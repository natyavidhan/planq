from flask import Blueprint, render_template, request, jsonify, session
from database import Database
import json

question_bp = Blueprint('question', __name__, url_prefix='/question')

# Database instance will be stored here when registered
db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return question_bp

@question_bp.route('/<question_id>', methods=['GET'])
def question_page(question_id):
    """Frontend route for displaying a question page"""
    try:
        # Fetch the question by ID
        question = db.pyqs['questions'].find_one({'_id': question_id})
        
        if not question:
            return render_template('question.html', error="Question not found")
            
        # Convert ObjectId to string for JSON serialization
        question['_id'] = str(question['_id'])
        
        # Get related data (exam, subject, chapter, paper)
        if 'exam' in question:
            exam = db.pyqs['exams'].find_one({'_id': question['exam']}, {'name': 1})
            if exam:
                question['exam_name'] = exam['name']
                
        if 'subject' in question:
            subject = db.pyqs['subjects'].find_one({'_id': question['subject']}, {'name': 1})
            if subject:
                question['subject_name'] = subject['name']
                
        if 'chapter' in question:
            chapter = db.pyqs['chapters'].find_one({'_id': question['chapter']}, {'name': 1})
            if chapter:
                question['chapter_name'] = chapter['name']
                
        if 'paper_id' in question:
            paper = db.pyqs['papers'].find_one({'_id': question['paper_id']}, {'name': 1})
            if paper:
                question['paper_name'] = paper['name']
        
        # Create a version of the question without answers/explanation
        public_question = {
            '_id': question['_id'],
            'question': question['question'],
            'type': question.get('type', 'singleCorrect'),
            'options': question.get('options', []),
            'exam_name': question.get('exam_name'),
            'subject_name': question.get('subject_name'),
            'chapter_name': question.get('chapter_name'),
            'paper_name': question.get('paper_name'),
            'level': question.get('level')
        }
        
        # Pass only the public data to the template (no correct answers or explanation)
        return render_template('question.html', question=public_question)
        
    except Exception as e:
        print(f"Question Page Error: {str(e)}")
        return render_template('question.html', error=f"Failed to load question: {str(e)}")

@question_bp.route('/attempt/<question_id>', methods=['POST'])
def attempt_question(question_id):
    """API endpoint for submitting an answer attempt and receiving feedback"""
    try:
        # Get the user's answer from the request
        data = request.json
        if not data or 'answer' not in data:
            return jsonify({"error": "No answer provided"}), 400
            
        user_answer = data['answer']
        
        # Fetch the question with correct answer and explanation
        question = db.pyqs['questions'].find_one({'_id': question_id})
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
            
        # Determine if the answer is correct
        is_correct = False
        question_type = question.get('type', 'singleCorrect')
        
        if question_type == 'singleCorrect' or question_type == 'multipleCorrect':
            correct_options = question.get('correct_option', [])
            
            if question_type == 'singleCorrect':
                # For single correct, user_answer should be a single index
                is_correct = isinstance(user_answer, int) and user_answer in correct_options
            else:
                # For multiple correct, user_answer should be an array of indices
                is_correct = isinstance(user_answer, list) and set(user_answer) == set(correct_options)
        elif question_type == 'numerical':
            correct_value = question.get('correct_value')
            if correct_value is None:
                return jsonify({"error": "Question has no defined correct answer"}), 400
                
            # Try to convert inputs to proper numerical values
            try:
                user_num = float(user_answer)
                correct_num = float(correct_value)
                
                # Determine appropriate tolerance based on the magnitude of the correct answer
                # For very small numbers, use absolute tolerance; for larger numbers, use relative tolerance
                if abs(correct_num) < 1e-10:  # For answers very close to zero
                    tolerance = 1e-10
                    is_correct = abs(user_num - correct_num) <= tolerance
                else:
                    # Use relative tolerance for normal-sized numbers
                    relative_tolerance = 0.0001  # 0.01% tolerance
                    absolute_tolerance = 0.001   # Fixed minimal tolerance
                    
                    # Check if within either relative or absolute tolerance
                    relative_diff = abs((user_num - correct_num) / correct_num)
                    absolute_diff = abs(user_num - correct_num)
                    is_correct = (relative_diff <= relative_tolerance) or (absolute_diff <= absolute_tolerance)
            except (ValueError, TypeError):
                is_correct = False
              # Prepare response
        response = {
            'is_correct': is_correct,
            'explanation': question.get('explanation', ''),
            'correct_answer': None
        }
        
        # Include the correct answer based on question type
        if question_type == 'singleCorrect' or question_type == 'multipleCorrect':
            response['correct_answer'] = question.get('correct_option', [])
        elif question_type == 'numerical':
            response['correct_answer'] = question.get('correct_value', '')

        db.add_activity(
            user_id=session['user']['id'],
            action='attempt_question',
            details={
                'question_id': question_id,
                'is_correct': is_correct,
                'user_answer': user_answer,
                'correct_answer': response['correct_answer']
            }
        )
            
        return jsonify(response)
        
    except Exception as e:
        print(f"Question Attempt Error: {str(e)}")
        return jsonify({"error": "Failed to process question attempt", "details": str(e)}), 500