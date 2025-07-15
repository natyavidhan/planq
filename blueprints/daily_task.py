from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from database import Database
from utils import auth_required, generate_heatmap_data, ist_now
from datetime import datetime, timezone

task_bp = Blueprint('daily_task', __name__, url_prefix='/daily-task')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return task_bp


def validate_answer(question, user_answer):
    question_type = question.get('type', 'singleCorrect')
    try:
        if question_type in ('singleCorrect', 'mcq'):
            correct_option = question.get('correct_option', [0])[0]
            return int(user_answer) == int(correct_option)

        elif question_type == 'numerical':
            correct_value = float(question.get('correct_value'))
            user_value = float(user_answer)
            # Allow tiny margin for floating point errors
            return abs(user_value - correct_value) < 0.01
        
        else:
            print(f"Unknown question type: {question_type}")
            return False

    except (ValueError, TypeError):
        return False
    
def apply_health_damage(test_data, question_level):
    total_questions = sum(len(v) for v in test_data.get('questions', {}).values())
    
    # Calculate damage using the new formula
    mul = {
        1: (-0.014 * 0.6),  # easy
        2: (-0.013 * 1.0),  # medium 
        3: (-0.012 * 1.4)   # hard
    }
    damage = int(mul[question_level] * total_questions**2 + 25)

    # Deduct health but never go below 0
    current_health = test_data.get('health', 100)
    new_health = max(0, current_health - damage)
    test_data['health'] = new_health

    # Update session
    session['daily_test'] = test_data
    return damage, round(new_health, 2)

@auth_required
@task_bp.route("/generate")
def generate_task():
        exam_id = request.args.get('exam')
        subject_id = request.args.get('subject')
        chapter_id = request.args.get('chapter')
        question_count = int(request.args.get('count', 10))
        time_limit = int(request.args.get('time', 30))
        
        ques = db.generate_test(
            exam_id=exam_id,
            subjects={subject_id: [chapter_id]},
            num=question_count,
            ratio=None
        )
        
        subject_data = db.get_subject(subject_id)
        chapter_data = db.get_chapter(chapter_id)
        
        all_question_ids = [qid for subj_questions in ques.values() for qid in subj_questions]
        print(all_question_ids)
        
        test_data = {
            '_id': 'daily-' + ist_now().strftime('%Y%m%d'),
            'title': f"Daily Task - {subject_data.get('name', 'Subject')} - {chapter_data.get('name', 'Chapter')}",
            'duration': time_limit,
            'questions': ques,
            'total_questions': len(all_question_ids),
            'exam': exam_id,
            'subject': subject_id,
        }

        
        exam_data = db.get_exam(exam_id)

        # Add activity for starting daily task
        db.add_activity(session['user']['id'], "daily_task_started", {
            "exam": exam_data.get('name', exam_id),
            "subject": subject_data.get('name', subject_id),
            "chapter": chapter_id,
            "count": question_count
        })

        test_data['health'] = 100
        test_data['start_time'] = ist_now().isoformat()
        test_data['q_meta'] = {q: {"status": None, "time": None} for q in all_question_ids}
        test_data['correct_count'] = 0
        test_data['incorrect_count'] = 0

        session['daily_test'] = test_data

        return redirect(url_for('daily_task.daily_task'))


@auth_required
@task_bp.route("/", methods=["GET", "POST"])
def daily_task():
    if 'user' not in session:
        return redirect(url_for("home"))
    
    user_id = session['user']['id']

    if request.method == 'POST':
        data = request.json or {}
        
        if 'question_id' in data:
            return process_question_attempt(data, user_id)
        elif 'correct_count' in data:
            return process_task_completion(data, user_id)
        else:
            return jsonify({'error': 'Invalid data format'}), 400

    # Handle GET request
    return render_daily_task_page()


def process_question_attempt(data, user_id):
    question_id = data.get('question_id')
    user_answer = data.get('user_answer')
    time_taken = data.get('time_taken', 0)

    question = db.get_question(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    is_correct = validate_answer(question, user_answer)
    db.add_activity(user_id, 'attempt_question', {
        'question_id': question_id,
        'is_correct': is_correct,
        'user_answer': user_answer,
        'time_taken': time_taken
    })

    test_data = session.get('daily_test', {})
    damage_done = 0
    if not is_correct:
        damage_done, health_remaining = apply_health_damage(test_data, question.get('level', 2))
        test_data['incorrect_count'] += 1
    else:
        health_remaining = test_data.get('health', 100)
        test_data['correct_count'] += 1
    
    test_data['q_meta'][question_id] = {
        'status': 'correct' if is_correct else 'incorrect',
        'time': time_taken
    }
    session['daily_test'] = test_data

    # Check for lucky guess achievement
    if is_correct and question.get('level', 1) == 3 and time_taken <= 5:
        db.check_lucky_guess(user_id, question.get('level', 1), time_taken)
        
    # Check for numerical precision achievement
    if is_correct and question.get('type') == 'numerical':
        db.check_performance_achievements(user_id, q_type='numerical')

    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'question_id': question_id,
        'damage_done': damage_done if not is_correct else 0,
        'health_remaining': health_remaining,
        'time_taken': time_taken,
    })


def process_task_completion(data, user_id):
    # correct_count = data.get('correct_count', 0)
    # incorrect_count = data.get('incorrect_count', 0)
    time_spent = data.get('time_spent', 0)
    question_timings = data.get('question_timings', {})
    health_remaining = data.get('health_remaining', 0)
    is_success = data.get('is_success', False)

    correct_count = session['daily_test'].get('correct_count', 0)
    incorrect_count = session['daily_test'].get('incorrect_count', 0)
    
    total_attempts = correct_count + incorrect_count
    total_questions = session['daily_test'].get('total_questions', 0)
    
    db.add_activity(user_id, "daily_task_completed", {
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "time_spent": time_spent,
        "question_timings": question_timings,
        "health_remaining": health_remaining,
        "is_success": is_success
    })

    activities = db.get_activities(user_id)
    heatmap_data = generate_heatmap_data(activities)
    
    # Check streak-related achievements
    db.check_streak_achievements(user_id)
    
    # Check performance-related achievements
    if total_attempts > 0:
        percent_correct = (correct_count / total_attempts) * 100
        avg_time_per_question = time_spent / total_questions if total_questions > 0 else 0
        
        db.check_performance_achievements(
            user_id,
            percent_correct=percent_correct,
            avg_time_per_question=avg_time_per_question,
            health_remaining=health_remaining
        )
    
    # Check time-based achievements
    db.check_time_based_achievements(user_id)
    
    # Check total achievements
    db.check_total_achievements(user_id)
    
    return jsonify({
        'success': True,
        'current_streak': heatmap_data['current_streak'],
        'longest_streak': heatmap_data['longest_streak']
    })


def render_daily_task_page():
    # GET request handling
    test_data = session.get('daily_test')
    if not test_data:
        return redirect(url_for('dashboard'))  # Redirect if no active daily test
    
    if test_data['health'] <= 0:
        flash("Your health is too low to continue the daily task. Please restart the test.")
        return redirect(url_for('dashboard'))

    # Fetch exam and subject metadata
    exam_data = db.get_exam(test_data['exam'])
    subject_data = db.get_subject(test_data['subject'])

    # Fetch all questions in bulk and sanitize
    all_question_ids = [qid for subj_questions in test_data['questions'].values() for qid in subj_questions]
    question_docs = db.get_questions_by_ids(all_question_ids, full_data=True)

    # print solution for debugging
    for q in question_docs:
        if q['type'] == 'numerical':
            print(q['correct_value'])
        else:
            print(q['correct_option'])

    # Sanitize question data to exclude answers
    sanitized_question_data = {}
    for q in question_docs:
        sanitized_question_data[q['_id']] = {
            '_id': q['_id'],
            'question': q['question'],
            'type': q.get('type', 'singleCorrect'),
            'options': q.get('options', []),
            'subject': q.get('subject'),
            'level': q.get('level', 2)
        }

    # Replace raw IDs in session with sanitized details for frontend
    test_data['question_data'] = sanitized_question_data

    # Fetch user activities for streak display
    activities = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(activities)
    streak_count = heatmap_data['current_streak']

    # Render the daily task template
    return render_template(
        'daily_task.html',
        test=test_data,
        streak_count=streak_count,
        exam=exam_data,
        subject=subject_data
    )