# app/__init__.py
from flask import Flask
from datetime import timedelta
import os
from app.utils.db import init_db
from flask_mail import Mail
from app.config import Config

mail = Mail()

def create_app():
    # Create Flask app with correct template folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'app', 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Ensure template folder exists
    if not os.path.exists(app.template_folder):
        os.makedirs(app.template_folder)
        print(f"Created template folder at: {app.template_folder}")
    else:
        print(f"Template folder exists at: {app.template_folder}")
    
    # Initialize database
    with app.app_context():
        init_db(app)
    
    # Register blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.files import bp as files_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(files_bp)
    
    # Create upload folder if it doesn't exist
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    
    # Debug print to show template folder location
    print(f"Flask app template folder: {app.template_folder}")
    print(f"Flask app static folder: {app.static_folder}")
    
    return app