from flask import Blueprint, render_template
from flask_login import login_required

questions = Blueprint('questions', __name__, url_prefix='/questions')

# Sample question data for demonstration
sample_questions = [
    {
        'id': 1,
        'title': 'What is the capital of France?',
        'content': 'Please name the capital city of France.',
        'options': ['Paris', 'London', 'Berlin', 'Madrid'],
        'correct_answer': 'Paris',
        'tags': ['Geography', 'Europe', 'Capitals'],
        'difficulty': 'Easy'
    }
]

@questions.route('/')
@login_required
def list():
    return render_template('questions.html', questions=sample_questions)

@questions.route('/<int:question_id>')
@login_required
def view(question_id):
    question = next((q for q in sample_questions if q['id'] == question_id), None)
    if question:
        return render_template('question_detail.html', question=question)
    return render_template('404.html'), 404
