from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import Database
from utils import auth_required
import json

test_bp = Blueprint('test', __name__, url_prefix='/test')

# Database instance will be stored here when registered
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
        data = request.form
        
        exam_id = data.get('exam')
        if data.get('mode') == "generate":
            subjects_ = [subject.replace('subject-', '') for subject in data.keys() if subject.startswith('subject-')]
            subjects = {subject: data.get(f'subject-{subject}').split(",") for subject in subjects_}
            test = db.generate_test(
                exam_id=exam_id,
                subjects=subjects,
                num=int(data.get('question_count')),
                ratio=int(data.get('mcq_ratio')) / 100
            )
            
            if not test:
                return jsonify({"error": "Failed to generate test. Please check your inputs."}), 400
            
            test_id = db.add_test(
                user_id=session['user']['id'],
                metadata={
                    "title": data.get('test_name'),
                    "description": data.get('description'),
                    "exam": exam_id,
                    "duration": int(data.get('duration')),
                    "mode": data.get('mode'),
                    "subjects": subjects,
                },
                questions=test
            )
        else:
            test_id =  db.add_pyq_test(
                user_id=session['user']['id'],
                metadata={
                    "title": data.get('test_name'),
                    "exam": exam_id,
                    "duration": int(data.get('duration')),
                    "mode": data.get('mode'),
                },
                paper_id=data.get('paper_id')
            )
        return redirect(url_for('test.attempt_test', test_id=test_id))
    return render_template("generate_test.html", exams=db.get_exams())


