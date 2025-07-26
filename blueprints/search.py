from flask import Blueprint, render_template, request, jsonify
from database import Database

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
    
    # Get filter parameters from URL
    exam_id = request.args.get('exam', '')
    subject_id = request.args.get('subject', '')
    chapter_id = request.args.get('chapter', '')
    
    return render_template('search.html', 
                         query=query,
                         initial_exam=exam_id,
                         initial_subject=subject_id,
                         initial_chapter=chapter_id)

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
            papers_list = [
                paper for paper in db.pyqs['papers'].values()
                if paper.get('exam') in exam_ids
            ]
            
            # Sort papers by timestamp (newest first)
            sorted_papers = sorted(papers_list, key=lambda p: p.get('timestamp', 0), reverse=True)
            
            # Format for response
            papers = [{"_id": p['_id'], "name": p['name']} for p in sorted_papers]
            
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

