from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .routes.main import main as main_blueprint
    from .routes.auth import auth as auth_blueprint
    from .routes.questions import questions as questions_blueprint
    from .routes.tests import tests as tests_blueprint
    from .routes.profile import profile as profile_blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(questions_blueprint)
    app.register_blueprint(tests_blueprint)
    app.register_blueprint(profile_blueprint)
    
    # Sample user loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        # This would typically load a user from a database
        # For now, we'll return None as we're just using placeholders
        return None
    
    return app
