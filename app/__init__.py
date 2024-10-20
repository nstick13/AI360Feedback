from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from .config import Config
from .models import db, User  # Import User here
from .auth import auth_bp
from .command_center import command_center_bp
from .feedback import feedback_bp
from .dashboard import dashboard_bp
from .home import home_bp

mail = Mail()
login_manager = LoginManager()

def create_app():
    # Initialize the Flask app
    app = Flask(__name__)

    # Load the configurations
    app.config.from_object(Config)

    # Set up extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Set login view
    login_manager.login_view = 'auth.login'

    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))  # Ensure User is imported

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(command_center_bp, url_prefix='/command_center')
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(home_bp)

    return app
