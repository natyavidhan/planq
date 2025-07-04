from flask import Blueprint, render_template, request, jsonify, session
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

@api_bp.route('/exams/<exam_id>/pyqs', methods=['GET'])
def get_exam_pyqs(exam_id):
    pyqs = db.get_pyqs_by_exam(exam_id)
    return jsonify({"pyqs": pyqs}), 200

@api_bp.route('/bookmarks/check/<question_id>', methods=['GET'])
@auth_required
def check_bookmark(question_id):
    user_id = session.get('user').get('id')
    is_bookmarked = db.check_bookmark(user_id, question_id)
    return jsonify({"bookmarked": is_bookmarked[0], "bucket": is_bookmarked[1]}), 200

@api_bp.route('/bookmarks/bucket/create', methods=['POST'])
@auth_required
def create_bookmark_bucket():
    user_id = session.get('user').get('id')
    bucket_name = request.json.get('name')
    bucket_id = db.create_bookmark_bucket(user_id, bucket_name)
    return jsonify({"message": "Bucket created successfully", "bucket_id": bucket_id}), 201

@api_bp.route('/bookmarks/add/<question_id>', methods=['POST'])
@auth_required
def add_bookmark(question_id):
    user_id = session.get('user').get('id')
    bucket_id = request.json.get('bucket')
    db.add_bookmark(user_id, question_id, bucket_id)
    return jsonify({"message": "Question added to bookmarks"}), 201