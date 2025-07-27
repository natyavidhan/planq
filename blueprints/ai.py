from flask import Blueprint, render_template, jsonify, session
from database import Database
from utils import auth_required

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return ai_bp


@ai_bp.route('/')
@auth_required
def ai_home():
    return render_template('ai.html')
