from flask import Blueprint, render_template
from flask_login import current_user
from app.routes.questions import sample_questions

# Create a blueprint for the main routes
main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html', sample_questions=sample_questions)
