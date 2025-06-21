from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

auth = Blueprint('auth', __name__, url_prefix='/auth')

# Dummy user data for demonstration
users = {
    'user@example.com': {
        'password': 'password123',
        'name': 'Test User'
    }
}

# User class for Flask-Login
class User:
    def __init__(self, email):
        self.email = email
        self.name = users[email]['name']
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return self.email


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in users and users[email]['password'] == password:
            user = User(email)
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('questions.list'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Registration logic would go here in a real application
        flash('Registration is not implemented in this demo', 'warning')
    
    return render_template('register.html')
