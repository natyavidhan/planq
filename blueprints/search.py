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
    """API endpoint for fetching filters"""
    try:
        exam_ids = request.args.get('examId', '').split(',')
        exam_ids = [id for id in exam_ids if id]  # Filter out empty strings
        
        subject_ids = request.args.get('subjectId', '').split(',')
        subject_ids = [id for id in subject_ids if id]  # Filter out empty strings
        
        if not exam_ids:
            return jsonify({"error": "Missing required parameters"}), 400
        
        # If no subject IDs provided, return available papers
        if not subject_ids:
            papers = list(db.pyqs['papers'].find(
                {"exam": {"$in": exam_ids}},
                {"_id": 1, "name": 1}
            ))
            
            # Convert ObjectId to string
            for paper in papers:
                paper['_id'] = str(paper['_id'])
                
            return jsonify(papers)
        
        # If subject IDs provided, return available chapters
        chapters = list(db.pyqs['chapters'].find(
            {"exam": {"$in": exam_ids}, "subject": {"$in": subject_ids}},
            {"_id": 1, "name": 1}
        ))
        
        # Convert ObjectId to string
        for chapter in chapters:
            chapter['_id'] = str(chapter['_id'])
            
        return jsonify(chapters)
        
    except Exception as e:
        print(f"API Filters Error: {str(e)}")
        return jsonify({"error": "Failed to fetch filters", "details": str(e)}), 500

@search_bp.route('/api', methods=['GET'])
def search_api():
    """API endpoint for searching questions"""
    try:
        # Extract all parameters
        query = request.args.get('query', '')
        exam_ids = request.args.get('examIds', '').split(',')
        exam_ids = [id for id in exam_ids if id]
        
        subject_ids = request.args.get('subjectIds', '').split(',')
        subject_ids = [id for id in subject_ids if id]
        
        chapter_ids = request.args.get('chapterIds', '').split(',')
        chapter_ids = [id for id in chapter_ids if id]
        
        paper_ids = request.args.get('paperIds', '').split(',')
        paper_ids = [id for id in paper_ids if id]
        
        # Pagination parameters
        page = int(request.args.get('page', '1'))
        limit = int(request.args.get('limit', '10'))
        
        # Validate pagination parameters
        if limit > 100:
            return jsonify({"error": "Limit exceeds maximum value of 100"}), 400
            
        if page < 1 or limit < 1:
            return jsonify({"error": "Page and limit must be greater than 0"}), 400
            
        skip = (page - 1) * limit
        
        # Build query filter
        query_filter = {}
        
        if query:
            query_filter['$or'] = [
                {'question': {'$regex': query, '$options': 'i'}},
                {'answer': {'$regex': query, '$options': 'i'}},
                {'options': {'$regex': query, '$options': 'i'}}
            ]
        
        # Add other filters
        if exam_ids:
            query_filter['exam'] = {'$in': exam_ids}
            
        if subject_ids:
            query_filter['subject'] = {'$in': subject_ids}
            
        if chapter_ids:
            query_filter['chapter'] = {'$in': chapter_ids}
            
        if paper_ids:
            query_filter['paper_id'] = {'$in': paper_ids}
        
        # Count total documents for pagination
        total_count = db.pyqs['questions'].count_documents(query_filter)
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        # Fetch questions
        questions = list(db.pyqs['questions'].find(
            query_filter,
            {
                '_id': 1,
                'type': 1,
                'question': 1,
                'exam': 1,
                'subject': 1,
                'chapter': 1,
                'paper_id': 1,
                'level': 1
            }
        ).skip(skip).limit(limit))
        
        # Extract unique IDs for related collections
        exam_ids_to_fetch = list(set(q['exam'] for q in questions if 'exam' in q))
        subject_ids_to_fetch = list(set(q['subject'] for q in questions if 'subject' in q))
        chapter_ids_to_fetch = list(set(q['chapter'] for q in questions if 'chapter' in q))
        paper_ids_to_fetch = list(set(q['paper_id'] for q in questions if 'paper_id' in q))
        
        # Fetch related data
        exams = {}
        if exam_ids_to_fetch:
            for exam in db.pyqs['exams'].find({'_id': {'$in': exam_ids_to_fetch}}, {'_id': 1, 'name': 1}):
                exams[exam['_id']] = exam['name']
        
        subjects = {}
        if subject_ids_to_fetch:
            for subject in db.pyqs['subjects'].find({'_id': {'$in': subject_ids_to_fetch}}, {'_id': 1, 'name': 1}):
                subjects[subject['_id']] = subject['name']
        
        chapters = {}
        if chapter_ids_to_fetch:
            for chapter in db.pyqs['chapters'].find({'_id': {'$in': chapter_ids_to_fetch}}, {'_id': 1, 'name': 1}):
                chapters[chapter['_id']] = chapter['name']
        
        papers = {}
        if paper_ids_to_fetch:
            for paper in db.pyqs['papers'].find({'_id': {'$in': paper_ids_to_fetch}}, {'_id': 1, 'name': 1}):
                papers[paper['_id']] = paper['name']
        
        # Add related data to questions
        for q in questions:
            q['_id'] = str(q['_id'])
            q['exam_name'] = exams.get(q.get('exam'))
            q['subject_name'] = subjects.get(q.get('subject'))
            q['chapter_name'] = chapters.get(q.get('chapter'))
            q['paper_name'] = papers.get(q.get('paper_id'))
        
        # Prepare response
        response = {
            'results': questions,
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