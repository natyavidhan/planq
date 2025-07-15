from flask import Blueprint, render_template, jsonify, session
from database import Database
from utils import auth_required

achievements_bp = Blueprint('achievements', __name__, url_prefix='/achievements')

db:Database = None

def init_blueprint(database):
    """Initialize the blueprint with the database instance"""
    global db
    db = database
    return achievements_bp

@achievements_bp.route('/', methods=['GET'])
@auth_required
def achievements_page():
    """Display user achievements"""
    user_id = session['user']['id']
    
    # Get all achievements from database
    unlocked_achievements = db.get_achievements(user_id)
    
    # Get all available achievements
    all_achievements = list(db.achievements.values())
    
    # Separate achievements by type
    streak_achievements = [a for a in all_achievements if a.get('type') == 'streak']
    total_achievements = [a for a in all_achievements if a.get('type') == 'total']
    performance_achievements = [a for a in all_achievements if a.get('type') == 'performance']
    time_achievements = [a for a in all_achievements if a.get('type') == 'time']
    
    # Mark unlocked achievements
    unlocked_ids = {a['_id'] for a in unlocked_achievements}
    for achievement in all_achievements:
        achievement['unlocked'] = achievement['_id'] in unlocked_ids
    
    return render_template(
        'achievements.html',
        streak_achievements=streak_achievements,
        total_achievements=total_achievements,
        performance_achievements=performance_achievements,
        time_achievements=time_achievements,
        unlocked_count=len(unlocked_ids),
        total_count=len(all_achievements)
    )

@achievements_bp.route('/check', methods=['POST'])
@auth_required
def check_achievements():
    """Manually check for new achievements"""
    user_id = session['user']['id']
    
    # Check all possible achievements
    db.check_streak_achievements(user_id)
    db.check_total_achievements(user_id)
    db.check_time_based_achievements(user_id)
    
    return jsonify({'success': True, 'message': 'Achievements checked'})
