from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from database import Database
from utils import auth_required
import json
from datetime import datetime
from utils import generate_heatmap_data

task_bp = Blueprint('daily_task', __name__, url_prefix='/daily-task')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return task_bp

@auth_required
@task_bp.route("/generate")
def generate_task():
        exam_id = request.args.get('exam')
        subject_id = request.args.get('subject')
        chapter_id = request.args.get('chapter')
        question_count = int(request.args.get('count', 5))
        time_limit = int(request.args.get('time', 30))
        
        ques = db.generate_test(
            exam_id=exam_id,
            subjects={subject_id: [chapter_id] if chapter_id else ['all']},
            num=question_count,
            ratio=None
        )
        
        subject_data = db.get_subject(subject_id)
        
        all_question_ids = [qid for subj_questions in ques.values() for qid in subj_questions]
        
        
        test_data = {
            '_id': 'daily-' + datetime.now().strftime('%Y%m%d'),
            'title': f"Daily Task - {subject_data.get('name', 'Subject')}",
            'duration': time_limit,
            'questions': ques,
            'total_questions': len(all_question_ids),
            'exam': exam_id,
            'subject': subject_id,
        }

        session['daily_test'] = test_data
        
        # Add activity for starting daily task
        # db.add_activity(session['user']['id'], "daily_task_started", {
        #     "exam": exam_data.get('name', exam_id),
        #     "subject": subject_data.get('name', subject_id),
        #     "count": question_count
        # })

        return redirect(url_for('daily_task.daily_task'))


@auth_required
@task_bp.route("/", methods=["GET", "POST"])
def daily_task():
    if 'user' not in session:
        return redirect(url_for("home"))
    
    if request.method == 'POST':
        data = request.json
        user_id = session['user']['id']
        
        if not data:
            return jsonify({'error': 'Missing data'}), 400
        
        # If it's an individual question attempt
        if 'question_id' in data:
            question_id = data['question_id']
            user_answer = data.get('user_answer')
            time_taken = data.get('time_taken', 0)  # Get time taken in milliseconds

            # Get the question from the database
            question = db.pyqs['questions'].get(question_id, {})
            if not question:
                return jsonify({'error': 'Question not found'}), 404
                
            # Determine if the answer is correct - server-side validation
            is_correct = False
            question_type = question.get('type', 'singleCorrect')
            
            if question_type == 'singleCorrect' or question_type == 'mcq':
                correct_option = question.get('correct_option', [0])[0]
                # Ensure both are treated as integers for comparison
                try:
                    correct_option_int = int(correct_option)
                    user_answer_int = int(user_answer)
                    is_correct = user_answer_int == correct_option_int
                except (ValueError, TypeError):
                    # If conversion fails, compare directly
                    is_correct = user_answer == correct_option
            
            elif question_type == 'numerical':
                correct_value = question.get('correct_value')
                
                # Handle numerical comparison with proper type conversion
                try:
                    user_num = float(user_answer)
                    correct_num = float(correct_value)
                    
                    # Allow small margin of error for floating point comparison
                    is_correct = abs(user_num - correct_num) < 0.01
                except (ValueError, TypeError):
                    is_correct = False
            
            # Record activity for the question attempt
            db.add_activity(
                user_id=session['user']['id'],
                action='attempt_question',
                details={
                    'question_id': question_id,
                    'is_correct': is_correct,
                    'user_answer': user_answer,
                    'time_taken': time_taken
                }
            )
            
            # Return validation result to frontend
            return jsonify({
                'success': True,
                'is_correct': is_correct,
                'question_id': question_id
            })
        
        # If it's the task completion
        elif 'correct_count' in data:
            # Add a completion activity with timing data
            db.add_activity(user_id, "daily_task_completed", {
                "correct_count": data.get('correct_count', 0),
                "incorrect_count": data.get('incorrect_count', 0),
                "time_spent": data.get('time_spent', 0),
                "question_timings": data.get('question_timings', {}),
                "health_remaining": data.get('health_remaining', 0),
                "is_success": data.get('is_success', False)
            })
            
            # Get updated streak info
            activities = db.get_activities(user_id)
            heatmap_data = generate_heatmap_data(activities)
            
            return jsonify({
                'success': True,
                'current_streak': heatmap_data['current_streak'],
                'longest_streak': heatmap_data['longest_streak']
            })
        
        else:
            return jsonify({'error': 'Invalid data format'}), 400
            
    # GET request handling (existing code)
    test_data = session.get('daily_test')
    if not test_data:
        return redirect(url_for('dashboard'))
    
    exam_data = db.pyqs['exams'].get(test_data['exam'], {})
    subject_data = db.get_subject(test_data['subject'])
    
    # Sanitize questions to remove answers before sending to frontend
    question_data = {}
    for qid in test_data['questions'].get(test_data['subject'], []):
        q = db.get_questions_by_ids([qid], full_data=True)
        if q:
            # Create a sanitized version of each question without answers
            sanitized_questions = []
            for question in q:
                # print question and answer
                if question.get('type') == 'singleCorrect':
                    print(f"Answer: {question.get('correct_option', 'N/A')}")
                else:
                    print(f"Answer: {question.get('correct_value', 'N/A')}")
                sanitized_question = {
                    '_id': question['_id'],
                    'question': question['question'],
                    'type': question.get('type', 'singleCorrect'),
                    'options': question.get('options', []),
                    'subject': question.get('subject'),
                    'level': question.get('level', 2),
                    # Do NOT include correct_option, correct_value or explanation
                }
                sanitized_questions.append(sanitized_question)
            question_data[qid] = sanitized_questions

    test_data['question_data'] = question_data
    
    activities = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(activities)
    streak_count = heatmap_data['current_streak']
    
    return render_template('daily_task.html', 
                       test=test_data, 
                       streak_count=streak_count,
                       exam=exam_data,
                       subject=subject_data)