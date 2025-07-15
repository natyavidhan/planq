from flask import Blueprint, request, jsonify, session
from database import Database
from utils import auth_required
from datetime import datetime, timezone

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
    subjects = db.get_subjects(exam_id, full=full)
    return jsonify({"subjects": subjects}), 200

@api_bp.route('/exams/<exam_id>/pyqs', methods=['GET'])
def get_exam_pyqs(exam_id):
    pyqs = db.get_pyqs(exam_id)
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

@api_bp.route('/daily-task/status', methods=['GET'])
@auth_required
def daily_task_status():
    user_id = session['user']['id']
    
    today_date = datetime.now(timezone.utc).date().isoformat()
    
    activities = db.get_activities(user_id)
    
    completed_today = False
    for activity in activities:
        # Skip activities without a timestamp
        if not activity.get('timestamp'):
            continue
        
        try:
            # Handle different timestamp formats
            if isinstance(activity['timestamp'], datetime):
                activity_date = activity['timestamp'].date().isoformat()
            elif 'T' in activity['timestamp']:
                activity_date = activity['timestamp'].split('T')[0]
            else:
                activity_date = activity['timestamp']
                
            # If this is a daily task completion from today
            if activity_date == today_date and activity.get('action') == 'daily_task_completed':
                completed_today = True
                break
        except (ValueError, AttributeError):
            continue
    
    return jsonify({
        'completed_today': completed_today,
        'today_date': today_date
    }), 200


@api_bp.route('/search', methods=['GET'])
def search_api():
    try:
        # Extract query parameters
        query = request.args.get('query', '').strip()
        exam_ids = [eid for eid in request.args.get('examIds', '').split(',') if eid]
        subject_ids = [sid for sid in request.args.get('subjectIds', '').split(',') if sid]
        chapter_ids = [cid for cid in request.args.get('chapterIds', '').split(',') if cid]
        paper_ids = [pid for pid in request.args.get('paperIds', '').split(',') if pid]

        # Pagination
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 10)), 1), 100)
        skip = (page - 1) * limit

        # Filter in-memory questions
        filtered_questions = []
        for q in db.pyqs['questions'].values():
            if exam_ids and q.get('exam') not in exam_ids:
                continue
            if subject_ids and q.get('subject') not in subject_ids:
                continue
            if chapter_ids and q.get('chapter') not in chapter_ids:
                continue
            if paper_ids and q.get('paper_id') not in paper_ids:
                continue
            if query:
                q_text = (q.get('question', '') + ' ' +
                          q.get('explanation', '') + ' ' +
                          ' '.join(q.get('options', [])))
                if query.lower() not in q_text.lower():
                    continue
            filtered_questions.append(q)

        total_count = len(filtered_questions)
        total_pages = (total_count + limit - 1) // limit

        # Paginate results
        paginated_questions = filtered_questions[skip:skip + limit]

        # Attach related names from preloaded pyqs
        for q in paginated_questions:
            q['_id'] = str(q['_id'])
            q['exam_name'] = db.pyqs['exams'].get(q.get('exam'), {}).get('name')
            q['subject_name'] = db.pyqs['subjects'].get(q.get('subject'), {}).get('name')
            q['chapter_name'] = db.pyqs['chapters'].get(q.get('chapter'), {}).get('name')
            q['paper_name'] = db.pyqs['papers'].get(q.get('paper_id'), {}).get('name')

        # Prepare response
        response = {
            'results': [{
                '_id': q['_id'],
                'type': q.get('type', 'singleCorrect'),
                'question': q.get('question'),
                'exam': q.get('exam'),
                'exam_name': q.get('exam_name'),
                'subject': q.get('subject'),
                'subject_name': q.get('subject_name'),
                'chapter': q.get('chapter'),
                'chapter_name': q.get('chapter_name'),
                'paper_id': q.get('paper_id'),
                'paper_name': q.get('paper_name'),
                'level': q.get('level', 1)
            } for q in paginated_questions],
            'pagination': {
                'currentPage': page,
                'totalPages': total_pages,
                'totalResults': total_count,
                'limit': limit
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"API Search Error: {str(e)}")
        return jsonify({"error": "Failed to fetch search results", "details": str(e)}), 500
    

@api_bp.route('/activities')
@auth_required
def get_activities():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    paginated_activities = db.get_paginated_activities(session['user']['id'], page, per_page)
    
    return jsonify(paginated_activities)