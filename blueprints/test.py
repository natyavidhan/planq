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
        # Handle test generation logic here
        data = request.json
        # Validate and process the data
        return jsonify({"message": "Test generated successfully!"}), 201
    return render_template("generate_test.html", exams=db.get_exams())