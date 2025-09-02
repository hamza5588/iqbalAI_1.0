# # app/__init__.py
# from flask import Flask
# from datetime import timedelta
# import os
# from app.utils.db import init_db
# from flask_mail import Mail
# from app.config import Config

# mail = Mail()

# def create_app():
#     # Create Flask app with correct template folder
#     base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     template_dir = os.path.join(base_dir, 'templates')
#     static_dir = os.path.join(base_dir, 'app', 'static')
    
#     app = Flask(__name__, 
#                 template_folder=template_dir,
#                 static_folder=static_dir)
    
#     # Load configuration
#     app.config.from_object(Config)
    
#     # Configure session
#     app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
#     app.config['SESSION_COOKIE_SECURE'] = True
#     app.config['SESSION_COOKIE_HTTPONLY'] = True 
#     app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
#     # Initialize Flask-Mail
#     mail.init_app(app)
    
#     # Ensure template folder exists
#     if not os.path.exists(app.template_folder):
#         os.makedirs(app.template_folder)
#         print(f"Created template folder at: {app.template_folder}")
#     else:
#         print(f"Template folder exists at: {app.template_folder}")
    
#     # Initialize database
#     with app.app_context():
#         init_db(app)
    
#     # Register blueprints (import here to avoid circular imports)
#     from app.routes.auth import bp as auth_bp
#     from app.routes.chat import bp as chat_bp
#     from app.routes.api_key import bp as api_key_bp
#     from app.routes.files import bp as file_bp
#     from app.routes.chatbot_routes import bp as chatbot_bp  # Changed to match pattern
#     from app.routes.survey import bp as survey_bp  # Separate import

#     # Register blueprints with appropriate prefixes
#     app.register_blueprint(auth_bp, url_prefix='/auth')  # Only register once
#     app.register_blueprint(chat_bp)
#     app.register_blueprint(api_key_bp)
#     app.register_blueprint(file_bp)
#     app.register_blueprint(chatbot_bp, url_prefix='/api')
#     app.register_blueprint(survey_bp, url_prefix='/api')
    
#     print(f"Flask app template folder: {app.template_folder}")
    
#     return app














# # app/__init__.py
# from flask import Flask
# from flask_cors import CORS  
# from datetime import timedelta
# import os
# from app.utils.db import init_db
# from flask_mail import Mail
# from app.config import Config

# mail = Mail()

# def create_app():
#     # Create Flask app with correct template folder
#     base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     template_dir = os.path.join(base_dir, 'templates')
#     static_dir = os.path.join(base_dir, 'app', 'static')
    
#     app = Flask(__name__, 
#                 template_folder=template_dir,
#                 static_folder=static_dir)
    
#     # Configure CORS - Add this right after Flask app creation
#     CORS(app,
#          resources={
#              r"/api/*": {
#                  "origins": "*",
#                  "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#                  "allow_headers": ["Content-Type", "Authorization"]
#              },
#              r"/auth/*": {
#                  "origins": "*",
#                  "supports_credentials": True
#              }
#          },
#          supports_credentials=True)
    
#     # Load configuration
#     app.config.from_object(Config)
    
#     # Configure session
#     app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
#     app.config['SESSION_COOKIE_SECURE'] = True
#     app.config['SESSION_COOKIE_HTTPONLY'] = True 
#     app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
#     # Initialize Flask-Mail
#     mail.init_app(app)
    
#     # Ensure template folder exists
#     if not os.path.exists(app.template_folder):
#         os.makedirs(app.template_folder)
#         print(f"Created template folder at: {app.template_folder}")
#     else:
#         print(f"Template folder exists at: {app.template_folder}")
    
#     # Initialize database
#     with app.app_context():
#         init_db(app)
    
#     # Register blueprints (import here to avoid circular imports)
#     from app.routes.auth import bp as auth_bp
#     from app.routes.chat import bp as chat_bp
#     from app.routes.api_key import bp as api_key_bp
#     from app.routes.files import bp as file_bp
#     from app.routes.chatbot_routes import bp as chatbot_bp
#     from app.routes.survey import bp as survey_bp

#     # Register blueprints with appropriate prefixes
#     app.register_blueprint(auth_bp, url_prefix='/auth')
#     app.register_blueprint(chat_bp)
#     app.register_blueprint(api_key_bp)
#     app.register_blueprint(file_bp)
#     app.register_blueprint(chatbot_bp, url_prefix='/api')
#     app.register_blueprint(survey_bp, url_prefix='/api')
    
#     print(f"Flask app template folder: {app.template_folder}")
    
#     return app









# app/__init__.py
from flask import Flask
from flask_cors import CORS  
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
    static_dir = os.path.join(base_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)


    
    # Configure CORS - FIXED VERSION
    CORS(app,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"],  # Specify your frontend URLs
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "supports_credentials": True,  # This was missing!
                 "expose_headers": ["Content-Type", "Authorization"]
             },
             r"/auth/*": {
                 "origins": ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"],
                 "supports_credentials": True,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
             }
         },
         supports_credentials=True)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Configure session - UPDATED for CORS
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True only in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True 
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
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
    
    # Register blueprints (import here to avoid circular imports)
    from app.routes.auth import bp as auth_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.api_key import bp as api_key_bp
    from app.routes.files import bp as file_bp
    from app.routes.chatbot_routes import bp as chatbot_bp
    from app.routes.survey import bp as survey_bp
    from app.routes.lesson_routes import bp as lesson_bp

    # Register blueprints with appropriate prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_key_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(chatbot_bp, url_prefix='/api')
    app.register_blueprint(survey_bp, url_prefix='/api')
    app.register_blueprint(lesson_bp, url_prefix='/api/lessons')
    
    print(f"Flask app template folder: {app.template_folder}")
    
    return app

