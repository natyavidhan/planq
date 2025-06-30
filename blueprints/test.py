from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify, abort
from database import Database
from utils import auth_required
import json
from datetime import datetime

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
    
    if not test_id or not answers:
        return jsonify({'error': 'Missing required data'}), 400
    
    # Get test from database
    test = db.get_test(test_id)
    if not test:
        return jsonify({'error': 'Test not found'}), 404
    
    # Check if user owns this test
    if test.get('created_by') != session['user']['id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Process answers and calculate score
    result = db.process_test_submission(test_id, session['user']['id'], answers, time_spent)
    
    # Add activity for completing test
    db.add_activity(session['user']['id'], "test_completed", {
        "test_id": test_id,
        "title": test['title'],
        "score": result['score']
    })
    
    return jsonify({'attemptId': result['attempt_id']}), 200