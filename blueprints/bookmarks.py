from flask import Blueprint, render_template, request, jsonify, session
from utils.database import Database
from utils import auth_required

bookmarks_bp = Blueprint('bookmarks', __name__, url_prefix='/bookmarks')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return bookmarks_bp

@auth_required
@bookmarks_bp.route('/check/<question_id>', methods=['GET'])
def check_bookmark(question_id):
    user_id = session.get('user').get('id')
    is_bookmarked = db.check_bookmark(user_id, question_id)
    return jsonify({"bookmarked": is_bookmarked[0], "bucket": is_bookmarked[1]}), 200

@auth_required
@bookmarks_bp.route('/bucket/create', methods=['POST'])
def create_bookmark_bucket():
    user_id = session.get('user').get('id')
    bucket_name = request.json.get('name')
    bucket_id = db.create_bookmark_bucket(user_id, bucket_name)
    return jsonify({"message": "Bucket created successfully", "bucket_id": bucket_id}), 201

@auth_required
@bookmarks_bp.route('/add/<question_id>', methods=['POST'])
def add_bookmark(question_id):
    user_id = session.get('user').get('id')
    bucket_id = request.json.get('bucket')
    db.add_bookmark(user_id, question_id, bucket_id)
    return jsonify({"message": "Question added to bookmarks"}), 201

@auth_required
@bookmarks_bp.route('/remove/<question_id>', methods=['POST'])
def remove_bookmark(question_id):
    user_id = session.get('user').get('id')
    bucket_id = request.json.get('bucket', 'default')
    db.remove_bookmark(user_id, question_id, bucket_id)
    return jsonify({"message": "Question removed from bookmarks"}), 200

@auth_required
@bookmarks_bp.route('/', methods=['GET'])
def bookmarks_page():
    user_id = session.get('user').get('id')
    buckets = db.get_user_buckets(user_id)
    questions_ids = []
    for bucket_id, bucket in buckets.items():
        if 'questions' in bucket:
            questions_ids.extend(bucket['questions'])

    questions = {i['_id']: i for i in db.get_questions_by_ids(questions_ids, full_data=True)}
    return render_template('bookmarks.html', buckets=buckets, questions=questions)