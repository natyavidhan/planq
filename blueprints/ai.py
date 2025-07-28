from flask import Blueprint, render_template, jsonify, session, request
from utils.rag import RAG
from utils.database import Database
from utils import auth_required

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

db:Database = None
rag:RAG = None

def init_blueprint(database, rag_instance):
    """Initialize the blueprint with the database instance"""
    global db, rag
    db = database
    rag = rag_instance
    return ai_bp


@ai_bp.route('/')
@auth_required
def ai_home():
    return render_template('ai.html')

@ai_bp.route('/retrieve', methods=['POST'])
@auth_required
def ai_retrieve():
    data = request.json
    query = data.get("query", "")
    exam_id = data.get("exam_id", "")
    subject_id = data.get("subject_id", "")
    top_k = data.get("top_k", 5)

    if not query or not exam_id:
        return jsonify({"error": "Invalid input"}), 400

    results = rag.planq_ai(query, exam_id, subject_id, top_k=top_k)
    return jsonify(results)