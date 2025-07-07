from flask import Blueprint, render_template, request, jsonify
from flask import current_app
from database import Database

import re

search_bp = Blueprint('search', __name__, url_prefix='/search')

# Database instance will be stored here when registered
db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return search_bp

@search_bp.route('/', methods=['GET'])
def search_page():
    """Frontend route for the search page"""
    query = request.args.get('query', '')
    return render_template('search.html', query=query)

@search_bp.route('/filters', methods=['GET'])
def filters_api():
    """API endpoint for fetching filters from in-memory pyqs data"""
    try:
        # Parse query parameters
        exam_ids = request.args.get('examId', '').split(',')
        exam_ids = [eid for eid in exam_ids if eid]  # Remove empty IDs

        subject_ids = request.args.get('subjectId', '').split(',')
        subject_ids = [sid for sid in subject_ids if sid]  # Remove empty IDs

        if not exam_ids:
            return jsonify({"error": "Missing required parameters"}), 400

        if not subject_ids:
            # Return all papers for given exams
            papers = [
                {"_id": pid, "name": paper['name']}
                for pid, paper in db.pyqs['papers'].items()
                if paper.get('exam') in exam_ids
            ]
            return jsonify(papers)

        else:
            # Return all chapters for given exams and subjects
            chapters = [
                {"_id": cid, "name": chapter['name']}
                for cid, chapter in db.pyqs['chapters'].items()
                if chapter.get('exam') in exam_ids and chapter.get('subject') in subject_ids
            ]
            return jsonify(chapters)

    except Exception as e:
        print(f"API Filters Error: {str(e)}")
        return jsonify({"error": "Failed to fetch filters", "details": str(e)}), 500

@search_bp.route('/api', methods=['GET'])
def search_api():
    """API endpoint for searching questions from in-memory pyqs data"""
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