from flask import session, redirect, url_for
from datetime import datetime, timedelta, timezone
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
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=364)  # 52 weeks * 7 days
    
    # Count all activities per date for the heatmap
    activity_counts = defaultdict(int)
    
    # Track dates with completed daily tasks (for streak calculation)
    daily_task_dates = set()
    
    for activity in activities:
        if activity.get('timestamp'):
            # Handle different timestamp formats safely
            try:
                # If timestamp is already a datetime object
                if isinstance(activity['timestamp'], datetime):
                    activity_date = activity['timestamp'].date()
                # If timestamp is a string with 'T' format (ISO format)
                elif 'T' in activity['timestamp']:
                    activity_date = datetime.strptime(activity['timestamp'].split('T')[0], '%Y-%m-%d').date()
                # If timestamp is just a date string
                else:
                    activity_date = datetime.strptime(activity['timestamp'], '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                # If any parsing error occurs, try a more generic approach
                try:
                    # Let Python figure out the format
                    activity_date = datetime.fromisoformat(activity['timestamp']).date()
                except:
                    # Skip this activity if we can't parse the date
                    continue
            
            if start_date <= activity_date <= end_date:
                activity_counts[activity_date] += 1
                
                # Add to daily task dates if it's a completed daily task
                if activity.get('action') == 'daily_task_completed':
                    daily_task_dates.add(activity_date)
    
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
    
    # Calculate streaks - ONLY using daily_task_completed dates
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    # Check if user completed a daily task today
    today_completed = end_date in daily_task_dates
    
    if today_completed:
        check_date = end_date
    else:
        check_date = end_date - timedelta(days=1)

    # Calculate current streak
    while check_date >= start_date and check_date in daily_task_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    # Calculate longest streak
    sorted_dates = sorted(list(daily_task_dates))
    
    if sorted_dates:
        # Initialize with the first date
        current_date = sorted_dates[0]
        temp_streak = 1
        longest_streak = 1
        
        # Check consecutive days
        for i in range(1, len(sorted_dates)):
            date = sorted_dates[i]
            expected_date = current_date + timedelta(days=1)
            
            if date == expected_date:
                # Consecutive day, extend streak
                temp_streak += 1
            else:
                # Streak broken, reset
                temp_streak = 1
                
            longest_streak = max(longest_streak, temp_streak)
            current_date = date

    print(weeks)
    print(months)

    return {
        'weeks': weeks,
        'months': months,
        'current_streak': current_streak,
        'longest_streak': longest_streak
    }