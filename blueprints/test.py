from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, abort
from database import Database
from utils import auth_required

test_bp = Blueprint('test', __name__, url_prefix='/test')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return test_bp

@test_bp.route('/generate', methods=['GET', 'POST'])
@auth_required
def generate_test():
    if request.method == 'POST':
        exam_id = request.form.get('exam')
        mode = request.form.get('mode')
        
        if mode == 'generate':
            # Custom test generation
            subjects = {}
            for key, value in request.form.items():
                if key.startswith('subject-'):
                    subject_id = key.replace('subject-', '')
                    chapters = value.split(',') if value != 'all' else ['all']
                    subjects[subject_id] = chapters
            
            mcq_ratio = float(request.form.get('mcq_ratio', '70')) / 100
            question_count = int(request.form.get('question_count', '30'))
            
            # Generate test questions
            questions = db.generate_test(exam_id, subjects, question_count, mcq_ratio)
            
            # Create test metadata
            metadata = {
                'title': request.form.get('test_name'),
                'description': request.form.get('description', ''),
                'exam': exam_id,
                'duration': int(request.form.get('duration', 180)),
                'mode': mode,
                'subjects': subjects
            }
            
            # Save test to database
            test_id = db.add_test(session['user']['id'], metadata, questions)
            
            # Add activity
            db.add_activity(session['user']['id'], "test_created", {
                "test_id": test_id,
                "title": metadata['title'],
                "exam": exam_id
            })
            
            return redirect(url_for('test.attempt_test', test_id=test_id))
            
        elif mode == 'previous':
            # Previous year paper
            paper_id = request.form.get('paper_id')
            
            metadata = {
                'title': request.form.get('test_name'),
                'exam': exam_id,
                'duration': int(request.form.get('duration', 180)),
                'mode': mode
            }
            
            # Create test from previous year paper
            test_id = db.add_pyq_test(session['user']['id'], metadata, paper_id)
            
            return redirect(url_for('test.attempt_test', test_id=test_id))
    
    exams = db.get_exams()
    return render_template('generate_test.html', exams=exams)

@test_bp.route('/<test_id>', methods=['GET'])
@auth_required
def attempt_test(test_id):
    test = db.get_test_optimized(test_id)
    if not test:
        abort(404)
    
    
    return render_template('attempt_test.html', test=test)

@test_bp.route('/submit', methods=['POST'])
@auth_required
def submit_test():
    data = request.json
    test_id = data.get('testId')
    answers = data.get('answers')
    time_spent = data.get('timeSpent')
    question_timings = data.get('questionTimings', {})  # Get question timings
    
    if not test_id or not answers:
        return jsonify({'error': 'Missing required data'}), 400
    
    # Get test from database
    test = db.get_test(test_id)
    if not test:
        return jsonify({'error': 'Test not found'}), 404
    
    # Check if user owns this test
    if test.get('created_by') != session['user']['id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Process answers and calculate score, passing question timings
    result = db.process_test_submission(test_id, session['user']['id'], answers, time_spent, question_timings)
    
    # Add activity for completing test
    db.add_activity(session['user']['id'], "test_completed", {
        "test_id": test_id,
        "title": test['title'],
        "score": result['score'],
        "attempt_id": result['attempt_id']
    })
    
    return jsonify({'attemptId': result['attempt_id']}), 200

@test_bp.route('/<test_id>/analysis')
@auth_required
def test_analysis(test_id):
    """Show analysis of all attempts for a test"""
    test = db.get_test(test_id)
    if not test:
        abort(404)
        
    # Check if user owns this test
    if test['created_by'] != session['user']['id']:
        abort(403)
    
    # Get attempts and calculate stats for each attempt
    raw_attempts = db.get_test_attempts(test_id)
    attempts = []
    
    for attempt in raw_attempts:
        # Calculate statistics from feedback data
        total_questions = sum(len(questions) for questions in test['questions'].values())
        attempted = len(attempt['feedback'])
        correct = sum(1 for item in attempt['feedback'] if item['correct'])
        incorrect = attempted - correct
        
        # Add statistics to the attempt object
        attempt['stats'] = {
            'attempted': attempted,
            'correct': correct,
            'incorrect': incorrect,
            'accuracy': correct / attempted if attempted > 0 else 0,
            'unanswered': total_questions - attempted
        }
        attempts.append(attempt)

    # Get subject information and store in a format that can be used in the template
    subjects = {}
    for sub_id in test['subjects']:
        subject_info = db.get_subject(sub_id)
        if subject_info:
            subjects[sub_id] = subject_info

    # Get marking scheme from configuration
    marking_scheme = db.config[test['exam']]['marking_scheme']

    # Get all questions with chapter information
    questions = {}
    q_temp = {}
    all_question_ids = [q_id for subject_questions in test['questions'].values() 
                         for q_id in subject_questions]
    for q in db.get_questions_by_ids(all_question_ids):
        q_temp[q['_id']] = q

    q_no = 1
    for sub, ques in test['questions'].items():
        for q_id in ques:
            questions[q_id] = q_temp[q_id]
            questions[q_id]['question_number'] = q_no
            q_no += 1

    # Calculate max marks
    if isinstance(marking_scheme['correct'], dict):
        # For complex marking schemes, use the first value as default
        first_value = next(iter(marking_scheme['correct'].values()))
        max_marks = total_questions * first_value
    else:
        max_marks = total_questions * marking_scheme['correct']
    
    test['max_marks'] = max_marks
    test['questions'] = len(all_question_ids)  # Store the total question count
    test['subjects'] = subjects  # Replace subject IDs with full subject objects


    attempts.sort(key=lambda x: x['submitted_at'].timestamp(), reverse=False)

    return render_template('test_analysis.html', 
                          test=test, 
                          attempts=attempts, 
                          questions=questions)