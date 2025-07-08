from flask import Flask, render_template, redirect, request, session, url_for, abort, flash
from dotenv import load_dotenv
import requests

import os
import secrets
from urllib.parse import urlencode
from datetime import datetime, timedelta
from collections import defaultdict

from config import CONFIG
from database import Database
from utils import auth_required
from blueprints.search import init_blueprint as init_search_blueprint
from blueprints.question import init_blueprint as init_question_blueprint
from blueprints.test import init_blueprint as init_test_blueprint
from blueprints.api import init_blueprint as init_api_blueprint
from blueprints.bookmarks import init_blueprint as init_bookmarks_blueprint

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

def generate_heatmap_data(activities):
    """Generate heatmap data from user activities"""
    # Create a date range for the last year
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=364)  # 52 weeks * 7 days
    
    # Count activities per date
    activity_counts = defaultdict(int)
    for activity in activities:
        if activity.get('timestamp'):
            activity_date = activity['timestamp'].date()
            if start_date <= activity_date <= end_date:
                activity_counts[activity_date] += 1
    
    # Generate weeks data
    weeks = []
    current_date = start_date
    
    # Start from Monday of the first week
    while current_date.weekday() != 0:
        current_date -= timedelta(days=1)
    
    week_dates = []
    while current_date <= end_date + timedelta(days=6):  # Add extra days to complete last week
        week = []
        for day in range(7):
            date = current_date + timedelta(days=day)
            count = activity_counts.get(date, 0)
            
            # Determine activity level (0-4)
            if count == 0:
                level = 0
            elif count <= 2:
                level = 1
            elif count <= 5:
                level = 2
            elif count <= 10:
                level = 3
            else:
                level = 4
            
            week.append({
                'date': date.isoformat(),
                'count': count,
                'level': level
            })
        
        weeks.append(week)
        week_dates.append(current_date)
        current_date += timedelta(days=7)
    
    months = []
    if week_dates:
        first_week_start = week_dates[0]
        total_weeks = len(week_dates)
        
        month_week_map = defaultdict(list)
        for week_idx, week_start in enumerate(week_dates):
            month_key = week_start.strftime('%Y-%m')
            month_week_map[month_key].append(week_idx)
        
        for month_key in sorted(month_week_map.keys()):
            week_indices = month_week_map[month_key]
            month_date = datetime.strptime(month_key, '%Y-%m').date()
            
            months.append({
                'name': month_date.strftime('%b'),
                'span': len(week_indices)
            })
    
    # Calculate streaks
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=364)

    today_count = activity_counts.get(end_date, 0)
    if today_count > 0:
        check_date = end_date
    else:
        check_date = end_date - timedelta(days=1)

    while check_date >= start_date and activity_counts.get(check_date, 0) > 0:
        current_streak += 1
        check_date -= timedelta(days=1)

    sorted_dates = sorted(activity_counts.keys())
    for i, date in enumerate(sorted_dates):
        if activity_counts[date] > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 0

    return {
        'weeks': weeks,
        'months': months,
        'current_streak': current_streak,
        'longest_streak': longest_streak
    }

@auth_required
@app.route("/dashboard")
def dashboard():
    user = db.get_user("_id", session['user']['id'])
    if not user:
        flash("User not found.")
        return redirect(url_for("home"))
    
    tests = db.get_tests_by_user(session['user']['id'])
    activity = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(activity)
    
    return render_template("dashboard.html", tests=tests, activity=activity, heatmap_data=heatmap_data)

@app.context_processor
def inject_user():
    """Make user available to all templates by default."""
    if 'user' in session:
        user = db.get_user("_id", session['user']['id'])
        return {'user': user, 'is_authenticated': True}
    return {'user': None, 'is_authenticated': False}




if __name__ == "__main__":
    app.run(debug=True)