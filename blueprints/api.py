from flask import Blueprint, render_template, request, jsonify
from database import Database
from utils import auth_required
import json

api_bp = Blueprint('api', __name__, url_prefix='/api')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return api_bp


@api_bp.route('/exams', methods=['GET'])
def get_exams():
    exams = db.get_exams()
    return jsonify({"exams": exams}), 200

@api_bp.route('/exams/<exam_id>/subjects', methods=['GET'])
def get_exam_subjects(exam_id):
    full = request.args.get('full', 'false').lower() == 'true'
    subjects = db.get_subjects_by_exam(exam_id, full=full)
    return jsonify({"subjects": subjects}), 200
