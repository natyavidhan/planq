from flask import Flask, render_template, redirect, request, session, url_for, abort, flash, jsonify
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
    
    # Get all exams for the extend streak modal
    exams = db.get_exams()
    
    return render_template("dashboard.html", tests=tests, activity=activity, heatmap_data=heatmap_data, exams=exams)

@auth_required
@app.route("/daily-task", methods=["GET", "POST"])
def daily_task():
    if 'user' not in session:
        return redirect(url_for("home"))
    

    if request.method == 'GET':
        # Get parameters from query string
        exam_id = request.args.get('exam')
        subject_id = request.args.get('subject')
        chapter_id = request.args.get('chapter')
        question_count = int(request.args.get('count', 5))
        time_limit = int(request.args.get('time', 30))
        
        # Generate questions but don't save as a test
        ques = db.generate_test(
            exam_id=exam_id,
            subjects={subject_id: [chapter_id] if chapter_id else ['all']},
            num=question_count,
            ratio=None
        )
        
        # Get exam, subject and chapter names for display
        exam_data = db.pyqs['exams'].get(exam_id)
        subject_data = db.get_subject(subject_id)
        
        # Prepare test data structure for the template
        all_question_ids = [qid for subj_questions in ques.values() for qid in subj_questions]
        
        # Get full question data
        question_data = {}
        for qid in all_question_ids:
            q = db.get_questions_by_ids([qid], full_data=True) 
            if q:
                question_data[qid] = q
        
        test_data = {
            '_id': 'daily-' + datetime.now().strftime('%Y%m%d'),
            'title': f"Daily Task - {subject_data.get('name', 'Subject')}",
            'duration': time_limit,
            'questions': ques,
            'question_data': question_data,
            'total_questions': len(all_question_ids)
        }

        session['daily_test'] = test_data
        
        # Add activity for starting daily task
        # db.add_activity(session['user']['id'], "daily_task_started", {
        #     "exam": exam_data.get('name', exam_id),
        #     "subject": subject_data.get('name', subject_id),
        #     "count": question_count
        # })
        
        # Calculate current streak
        activities = db.get_activities(session['user']['id'])
        heatmap_data = generate_heatmap_data(activities)
        streak_count = heatmap_data['current_streak']
        
        return render_template('daily_task.html', 
                            test=test_data, 
                            streak_count=streak_count,
                            exam=exam_data,
                            subject=subject_data)

    if 'user' not in session or 'daily_test' not in session:
        return jsonify({'error': 'No active daily task found'}), 400
    
    # Get the daily test data from session
    daily_test = session['daily_test']
    
    # Get the submitted answers
    data = request.json
    if not data or 'answers' not in data:
        return jsonify({'error': 'Missing answer data'}), 400
    
    submitted_answers = data['answers']
    time_spent = data.get('time_spent', 0)
    
    # Process each answer
    correct_count = 0
    total_questions = 0
    
    # Get flat list of all question IDs
    all_question_ids = [qid for subj_questions in daily_test['questions'].values() 
                        for qid in subj_questions]
    
    for question_id in all_question_ids:
        total_questions += 1
        
        # Get question data
        question_data = daily_test['question_data'].get(question_id, [])
        if not question_data:
            continue
            
        # Get the first question (your data structure)
        question = question_data[0] if question_data else None
        if not question:
            continue
        
        # Check if this question was answered
        user_answer = submitted_answers.get(question_id)
        if user_answer is None:
            continue
            
        # Check if answer is correct
        is_correct = False
        
        if question['type'] == 'singleCorrect' or question['type'] == 'mcq':
            correct_option = question['correct_option'][0] if question.get('correct_option') else None
            is_correct = user_answer == correct_option
        elif question['type'] == 'numerical':
            correct_value = question.get('correct_value')
            # Allow small margin of error for numerical
            is_correct = abs(float(user_answer) - float(correct_value)) < 0.01 if correct_value is not None else False
        
        # Record activity for this question attempt
        activity_type = "daily_correct_answer" if is_correct else "daily_incorrect_answer"
        
        # Add details to the activity
        details = {
            "question_id": question_id,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "exam": daily_test.get('exam'),
            "subject": question.get('subject')
        }
        
        # If the question has chapter info, include it
        if question.get('chapter'):
            details["chapter"] = question['chapter']
            
        db.add_activity(session['user']['id'], activity_type, details)
        
        if is_correct:
            correct_count += 1
    
    # Calculate score
    score_percent = (correct_count / total_questions * 100) if total_questions > 0 else 0
    score_percent = round(score_percent, 1)
    
    # Record daily task completion
    db.add_activity(session['user']['id'], "daily_task_completed", {
        "correct_count": correct_count,
        "total_questions": total_questions,
        "score": score_percent,
        "time_spent": time_spent,
        "title": daily_test.get('title', 'Daily Task')
    })
    
    # Clean up the session
    session.pop('daily_test', None)
    
    # Get updated streak info
    activities = db.get_activities(session['user']['id'])
    heatmap_data = generate_heatmap_data(activities)
    
    return jsonify({
        'success': True,
        'score': score_percent,
        'correct': correct_count,
        'total': total_questions,
        'current_streak': heatmap_data['current_streak'],
        'longest_streak': heatmap_data['longest_streak']
    })

@app.context_processor
def inject_user():
    """Make user available to all templates by default."""
    if 'user' in session:
        user = db.get_user("_id", session['user']['id'])
        return {'user': user, 'is_authenticated': True}
    return {'user': None, 'is_authenticated': False}




if __name__ == "__main__":
    app.run(debug=True)