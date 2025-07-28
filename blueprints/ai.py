from flask import Blueprint, render_template, jsonify, session, request, redirect, url_for, abort
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
    user_id = session['user']['id']
    chat = db.create_chat(user_id)
    return redirect(url_for('ai.ai_chat', chat_id=chat['_id']))

@ai_bp.route('/<chat_id>')
@auth_required
def ai_chat(chat_id):
    user_id = session['user']['id']
    chat = db.ai[user_id].find_one({"_id": chat_id})
    if not chat:
        abort(404)
    chats = db.get_user_chats(user_id)
    return render_template('ai.html', chat=chat, chats=chats)

@ai_bp.route('/retrieve', methods=['POST'])
@auth_required
def ai_retrieve():
    data = request.json
    user_id = session['user']['id']
    
    query = data.get("query", "")
    exam_id = data.get("exam_id", "")
    subject_id = data.get("subject_id", "")
    chat_id = data.get("chat_id")
    messages = data.get("messages", [])
    top_k = data.get("top_k", 5)

    if not query or (not exam_id or not subject_id) or not chat_id:
        return jsonify({"error": "Invalid input"}), 400

    if not messages:
        db.update_chat_metadata(user_id, chat_id, {
            "exam_id": exam_id,
            "subject_id": subject_id
        })
    
    prompt, results = rag.planq_ai(query, exam_id, subject_id, top_k=top_k, messages=messages)
    
    db.add_chat_message(user_id, chat_id, "user", query)
    db.add_chat_message(user_id, chat_id, "model", results['answer'], context=results.get('context_used'))
    
    return jsonify(results)

@ai_bp.route('/delete/<chat_id>', methods=['POST'])
@auth_required
def ai_delete_chat(chat_id):
    user_id = session['user']['id']
    db.delete_chat(user_id, chat_id)
    return jsonify({"success": True})