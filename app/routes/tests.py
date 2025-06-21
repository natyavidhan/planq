from flask import Blueprint, render_template
from flask_login import login_required

tests = Blueprint('tests', __name__, url_prefix='/tests')

@tests.route('/')
@login_required
def list():
    return render_template('tests.html')

@tests.route('/generate')
@login_required
def generate():
    return render_template('test_generator.html')

@tests.route('/<int:test_id>')
@login_required
def view(test_id):
    # In a real app, we would fetch test data by ID
    return render_template('test_detail.html', test_id=test_id)
