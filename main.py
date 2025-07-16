from flask import Flask, render_template, redirect, request, session, url_for, abort, flash, jsonify
from dotenv import load_dotenv
import requests

import os
import secrets
from urllib.parse import urlencode
from datetime import datetime

from config import CONFIG
from database import Database
from utils import auth_required, generate_heatmap_data

from blueprints.search import init_blueprint as init_search_blueprint
from blueprints.question import init_blueprint as init_question_blueprint
from blueprints.test import init_blueprint as init_test_blueprint
from blueprints.api import init_blueprint as init_api_blueprint
from blueprints.bookmarks import init_blueprint as init_bookmarks_blueprint
from blueprints.practice import init_blueprint as init_practice_blueprint
from blueprints.achievements import init_blueprint as init_achievements_blueprint

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['OAUTH2_PROVIDERS'] = CONFIG

db = Database()

# Register blueprints
app.register_blueprint(init_search_blueprint(db))
app.register_blueprint(init_question_blueprint(db))
app.register_blueprint(init_test_blueprint(db))
app.register_blueprint(init_api_blueprint(db))
app.register_blueprint(init_bookmarks_blueprint(db))
app.register_blueprint(init_practice_blueprint(db))
app.register_blueprint(init_achievements_blueprint(db))

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
    
    return render_template("dashboard.html", 
                          tests=tests, 
                          activity=all_activities[:6],
                          paginated_activity=paginated_activities,
                          heatmap_data=heatmap_data, 
                          exams=exams,
                          current_page=page,
                          total_activities=len(all_activities),
                          ac=db.achievements)


@app.context_processor
def inject_user():
    """Make user available to all templates by default."""
    if 'user' in session:
        user = db.get_user("_id", session['user']['id'])
        return {'user': user, 'is_authenticated': True}
    return {'user': None, 'is_authenticated': False}




if __name__ == "__main__":
    app.run(debug=True)