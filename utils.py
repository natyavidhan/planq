from flask import session, redirect, url_for
from datetime import datetime, timedelta
from collections import defaultdict

def auth_required(f):
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


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