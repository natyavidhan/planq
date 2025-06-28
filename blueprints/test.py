from flask import Blueprint, render_template, request, jsonify
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
        print(data)
        exam_id = data.get('exam')
        subjects_ = [subject.replace('subject-', '') for subject in data.keys() if subject.startswith('subject-')]
        subjects = {subject: data.get(f'subject-{subject}').split(",") for subject in subjects_}
        test = db.generate_test(
            exam_id=exam_id,
            subjects=subjects,
            num=int(data.get('question_count')),
            ratio=int(data.get('mcq_ratio')) / 100
        )
        print(json.dumps(test, indent=2))
        return jsonify({"message": "Test generated successfully!"}), 201
    return render_template("generate_test.html", exams=db.get_exams())