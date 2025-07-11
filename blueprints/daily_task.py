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
    
    if request.method == 'GET':
        test_data = session.get('daily_test')
        if not test_data:
            return redirect(url_for('dashboard'))
        
        exam_data = db.pyqs['exams'].get(test_data['exam'], {})
        subject_data = db.get_subject(test_data['subject'])
        
        question_data = {}
        for qid in test_data['questions'].get(test_data['subject'], []):
            q = db.get_questions_by_ids([qid], full_data=True) 
            if q:
                question_data[qid] = q
    
        test_data['question_data'] = question_data
        
        activities = db.get_activities(session['user']['id'])
        heatmap_data = generate_heatmap_data(activities)
        streak_count = heatmap_data['current_streak']
        
        return render_template('daily_task.html', 
                           test=test_data, 
                           streak_count=streak_count,
                           exam=exam_data,
                           subject=subject_data)

    if 'user' not in session or 'daily_test' not in session:
        return jsonify({'error': 'No active daily task found'}), 400
    
    # Get the daily test data from session
    daily_test = session['daily_test']
    
    # Get the submitted answers
    data = request.json
    if not data or 'answers' not in data:
        return jsonify({'error': 'Missing answer data'}), 400
    
    submitted_answers = data['answers']
    time_spent = data.get('time_spent', 0)
    
    # Process each answer
    correct_count = 0
    total_questions = 0
    
    # Get flat list of all question IDs
    all_question_ids = [qid for subj_questions in daily_test['questions'].values() 
                        for qid in subj_questions]
    
    for question_id in all_question_ids:
        total_questions += 1
        
        # Get question data
        question_data = daily_test['question_data'].get(question_id, [])
        if not question_data:
            continue
            
        # Get the first question (your data structure)
        question = question_data[0] if question_data else None
        if not question:
            continue
        
        # Check if this question was answered
        user_answer = submitted_answers.get(question_id)
        if user_answer is None:
            continue
            
        # Check if answer is correct
        is_correct = False
        
        if question['type'] == 'singleCorrect' or question['type'] == 'mcq':
            correct_option = question['correct_option'][0] if question.get('correct_option') else None
            is_correct = user_answer == correct_option
        elif question['type'] == 'numerical':
            correct_value = question.get('correct_value')
            # Allow small margin of error for numerical
            is_correct = abs(float(user_answer) - float(correct_value)) < 0.01 if correct_value is not None else False
        
        # Record activity for this question attempt
        activity_type = "daily_correct_answer" if is_correct else "daily_incorrect_answer"
        
        # Add details to the activity
        details = {
            "question_id": question_id,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "exam": daily_test.get('exam'),
            "subject": question.get('subject')
        }
        
        # If the question has chapter info, include it
        if question.get('chapter'):
            details["chapter"] = question['chapter']
            
        db.add_activity(session['user']['id'], activity_type, details)
        
        if is_correct:
            correct_count += 1
    
    # Calculate score
    score_percent = (correct_count / total_questions * 100) if total_questions > 0 else 0
    score_percent = round(score_percent, 1)
    
    # Record daily task completion
    db.add_activity(session['user']['id'], "daily_task_completed", {
        "correct_count": correct_count,
        "total_questions": total_questions,
        "score": score_percent,
        "time_spent": time_spent,
        "title": daily_test.get('title', 'Daily Task')
    })
    
    # Clean up the session
    session.pop('daily_test', None)
    
    # Get updated streak info
    activities = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(activities)
    
    return jsonify({
        'success': True,
        'score': score_percent,
        'correct': correct_count,
        'total': total_questions,
        'current_streak': heatmap_data['current_streak'],
        'longest_streak': heatmap_data['longest_streak']
    })