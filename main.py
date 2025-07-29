from flask import Flask, render_template, redirect, request, session, url_for, abort, flash, jsonify
from dotenv import load_dotenv
import requests

import os
import secrets
from urllib.parse import urlencode
from datetime import datetime

from utils.sr import SR
from config import CONFIG
from utils.database import Database
from utils import auth_required, generate_heatmap_data, ist_now

from blueprints.search import init_blueprint as init_search_blueprint
from blueprints.question import init_blueprint as init_question_blueprint
from blueprints.test import init_blueprint as init_test_blueprint
from blueprints.api import init_blueprint as init_api_blueprint
from blueprints.bookmarks import init_blueprint as init_bookmarks_blueprint
from blueprints.practice import init_blueprint as init_practice_blueprint
from blueprints.achievements import init_blueprint as init_achievements_blueprint
from blueprints.track import init_blueprint as init_track_blueprint
from blueprints.ai import init_blueprint as init_ai_blueprint

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['OAUTH2_PROVIDERS'] = CONFIG

db = Database()
sr = SR(db)

# Register blueprints
app.register_blueprint(init_search_blueprint(db))
app.register_blueprint(init_question_blueprint(db))
app.register_blueprint(init_test_blueprint(db))
app.register_blueprint(init_api_blueprint(db, sr))
app.register_blueprint(init_bookmarks_blueprint(db))
app.register_blueprint(init_practice_blueprint(db, sr))
app.register_blueprint(init_achievements_blueprint(db))
app.register_blueprint(init_track_blueprint(db, sr))
app.register_blueprint(init_ai_blueprint(db))

# Custom filters for templates
@app.template_filter('formatdate')
def format_date(value):
    if isinstance(value, datetime):
        return value.strftime('%b %d, %Y')
    return value

@app.template_filter('formatdatetime')
def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime('%b %d, %Y at %I:%M %p')
    return value

@app.route("/")
def home():
    if 'user' not in session:
        return render_template("home.html")
    return redirect(url_for("dashboard"))


@app.route('/authorize/<provider>')
def oauth2_authorize(provider):
    if 'user' in session:
        return redirect(url_for('home'))

    provider_data = app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    session['oauth2_state'] = secrets.token_urlsafe(16)

    qs = urlencode({
        'client_id': provider_data['client_id'],
        'redirect_uri': url_for('oauth2_callback', provider=provider,
                                _external=True),
        'response_type': 'code',
        'scope': ' '.join(provider_data['scopes']),
        'state': session['oauth2_state'],
    })

    return redirect(provider_data['authorize_url'] + '?' + qs)


@app.route('/callback/<provider>')
def oauth2_callback(provider):
    if 'user' in session:
        return redirect(url_for('home'))

    provider_data = app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    if 'error' in request.args:
        for k, v in request.args.items():
            if k.startswith('error'):
                flash(f'{k}: {v}')
        return redirect(url_for('index'))

    if request.args['state'] != session.get('oauth2_state'):
        abort(401)

    if 'code' not in request.args:
        abort(401)

    response = requests.post(provider_data['token_url'], data={
        'client_id': provider_data['client_id'],
        'client_secret': provider_data['client_secret'],
        'code': request.args['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('oauth2_callback', provider=provider,
                                _external=True),
    }, headers={'Accept': 'application/json'})
    if response.status_code != 200:
        abort(401)
    oauth2_token = response.json().get('access_token')
    if not oauth2_token:
        abort(401)

    # use the access token to get the user's email address
    response = requests.get(provider_data['userinfo']['url'], headers={
        'Authorization': 'Bearer ' + oauth2_token,
        'Accept': 'application/json',
    })
    if response.status_code != 200:
        abort(401)
    email = provider_data['userinfo']['email'](response.json())

    if not email:
        flash('No email address found in the user info response.')
        return redirect(url_for('home'))
    
    user = db.get_user("email", email)
    if not user:
        user = db.add_user(email)

    session['user'] = {
        'id': str(user['_id']),
        'email': user['email'],
        'username': user['username']
    }

    return redirect(url_for('home'))

@app.route("/logout")
def logout():
    session.pop("user")
    return redirect(url_for("home"))


@app.route("/profile/<username>")
def profile(username):
    user = db.get_user("username", username)
    if not user:
        abort(404)

    user_id = str(user['_id'])

    # Calculate XP info for the profile user
    total_xp = user.get('points', 0)
    level = int((total_xp / 100) ** (1 / 1.5)) + 1
    xp_for_current_level = int(100 * ((level - 1) ** 1.5))
    xp_for_next_level = int(100 * (level ** 1.5))
    xp_in_current_level = total_xp - xp_for_current_level
    xp_needed_for_next_level = xp_for_next_level - xp_for_current_level
    progress_percentage = (xp_in_current_level / xp_needed_for_next_level) * 100 if xp_needed_for_next_level > 0 else 0

    user['xp_info'] = {
        'level': level,
        'total_xp': total_xp,
        'progress': progress_percentage,
        'xp_current': xp_in_current_level,
        'xp_needed': xp_needed_for_next_level
    }

    # Fetch activities and filter out sensitive ones
    all_activities = db.get_activities(user_id)
    public_activities = [
        activity for activity in all_activities 
        if activity.get("action") not in ["attempt_question", "practice_started"]
    ]

    # Generate heatmap from all activities
    heatmap_data = generate_heatmap_data(all_activities)

    # Get unlocked achievements
    unlocked_achievements = db.get_achievements(user_id)

    # Get total unique questions solved
    unique_question_ids = db.activities[user_id].distinct(
        "details.question_id", 
        {"action": "attempt_question"}
    )
    total_unique_questions = len(unique_question_ids)
    
    # Calculate progress by exam
    solved_questions = db.get_questions_by_ids(unique_question_ids, full_data=True)
    progress_by_exam = {}
    
    # Pre-calculate total questions per subject for efficiency
    total_questions_per_subject = {}
    for q_id, q_data in db.pyqs['questions'].items():
        subject_id = q_data.get('subject')
        if subject_id:
            total_questions_per_subject[subject_id] = total_questions_per_subject.get(subject_id, 0) + 1

    for q in solved_questions:
        exam_id = q.get('exam')
        subject_id = q.get('subject')
        
        if not exam_id or not subject_id:
            continue

        if exam_id not in progress_by_exam:
            progress_by_exam[exam_id] = {
                'name': db.get_exam(exam_id)['name'],
                'subjects': {}
            }
        
        if subject_id not in progress_by_exam[exam_id]['subjects']:
            progress_by_exam[exam_id]['subjects'][subject_id] = {
                'name': db.get_subject(subject_id)['name'],
                'solved': 0,
                'total': total_questions_per_subject.get(subject_id, 0)
            }
        
        progress_by_exam[exam_id]['subjects'][subject_id]['solved'] += 1
    print(progress_by_exam)
    return render_template("profile.html",
                           profile_user=user,
                           activities=public_activities[:10],
                           heatmap_data=heatmap_data,
                           unlocked_achievements=unlocked_achievements,
                           total_unique_questions=total_unique_questions,
                           ac=db.achievements,
                           progress_by_exam=progress_by_exam)


@app.route("/dashboard")
@auth_required
def dashboard():
    user = db.get_user("_id", session['user']['id'])
    if not user:
        flash("User not found.")
        return redirect(url_for("home"))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    tests = db.get_tests_by_user(session['user']['id'])
    
    all_activities = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(all_activities)
    
    paginated_activities = db.get_paginated_activities(session['user']['id'], page, per_page)
    
    exams = db.get_exams()
    
    sr_chapters = sr.get_chapters(session['user']['id'])
    new_sr_chapters = []
    for chapter in sr_chapters:
        new_sr_chapters.append({
            'chapter_id': chapter['_id'],
            'ef': chapter['ef'],
            'last_revision': chapter['last_revision'],
            'interval': chapter['interval'],
            'delta': chapter['delta'],
            'next': chapter['interval'] - (ist_now() - chapter['last_revision']).days,
            'days_since': (ist_now() - chapter['last_revision']).days,
        })
        
    new_sr_chapters.sort(key=lambda x: x['next'])
    new_sr_chapters = new_sr_chapters[:4]
    
    for chapter in new_sr_chapters:
        chapter['next'] = max(0, chapter['next'])
        
        ch = db.get_chapter(chapter['chapter_id'])
        exam = db.get_exam(ch['exam'])['name']
        sub = db.get_subject(ch['subject'])['name']
        
        ques = sr.unique_questions_solved(session['user']['id'], chapter['chapter_id'])
        chapter['exam'] = exam
        chapter['subject'] = sub
        chapter['title'] = ch['name']
        chapter['questions'] = len(ques)
        
    
    return render_template("dashboard.html", 
                          tests=tests, 
                          activity=all_activities[:6],
                          paginated_activity=paginated_activities,
                          heatmap_data=heatmap_data, 
                          exams=exams,
                          current_page=page,
                          total_activities=len(all_activities),
                          ac=db.achievements,
                          sr_chapters=new_sr_chapters)


@app.context_processor
def inject_user():
    """Make user available to all templates by default."""
    if 'user' in session:
        user = db.get_user("_id", session['user']['id'])
        if user:
            total_xp = user.get('points', 0)
            
            # Leveling logic for progress bar
            level = int((total_xp / 100) ** (1 / 1.5)) + 1
            xp_for_current_level = int(100 * ((level - 1) ** 1.5))
            xp_for_next_level = int(100 * (level ** 1.5))
            
            xp_in_current_level = total_xp - xp_for_current_level
            xp_needed_for_next_level = xp_for_next_level - xp_for_current_level
            
            progress_percentage = (xp_in_current_level / xp_needed_for_next_level) * 100 if xp_needed_for_next_level > 0 else 0

            user['xp_info'] = {
                'level': level,
                'total_xp': total_xp,
                'progress': progress_percentage,
                'xp_current': xp_in_current_level,
                'xp_needed': xp_needed_for_next_level
            }
            return {'user': user, 'is_authenticated': True}
    return {'user': None, 'is_authenticated': False}




if __name__ == "__main__":
    app.run(debug=True)