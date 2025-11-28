import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production
    
    # Email configuration
    MAIL_SERVER = 'mail.privateemail.com'
    MAIL_PORT = 587
    # MAIL_SERVER = 'smtp.gmail.com'
    # MAIL_PORT = 587
    MAIL_USE_TLS = True
    # MAIL_USERNAME = 'info@iqbalai.com'  # Make sure this is the full email address
    # MAIL_PASSWORD = 'Iqbalai12@'  # Make sure this is the correct app-specific password
    # MAIL_DEFAULT_SENDER = 'info@iqbalai.com'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'info@iqbalai.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'Iqbalai12@')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME', 'info@iqbalai.com')
    MAIL_DEBUG = True  # Enable debug mode to see more detailed logs

    
    # Database configuration - supports SQLite, MySQL, and PostgreSQL
    # Examples:
    # SQLite: sqlite:///instance/chatbot.db or sqlite:////absolute/path/to/chatbot.db
    # MySQL: mysql+pymysql://user:password@localhost/dbname
    # PostgreSQL: postgresql://user:password@localhost/dbname or postgresql+psycopg2://user:password@localhost/dbname
    DATABASE_URL = os.getenv('DATABASE_URL','postgresql://myuser:mypassword@localhost:5432/mydatabase')
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 300,    # Recycle connections after 5 minutes
        'echo': False           # Set to True for SQL query logging
    }
    
    # Legacy DATABASE path for backward compatibility (used only if needed)
    if DATABASE_URL.startswith('sqlite'):
        # Extract path from SQLite URL
        db_path = DATABASE_URL.replace('sqlite:///', '').replace('sqlite:////', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        DATABASE = db_path
    else:
        DATABASE = None  # Not used for non-SQLite databases
    
    # Nomic API configuration
    NOMIC_API_KEY = os.getenv('NOMIC_API_KEY', 'nk-7Em9YdxJJI09E4vXTxJ9VOC2zygDGWD9eGBYxDLuG0E')  # Replace with your Nomic API key
    
    # Server URL for generating absolute URLs in production
    # Set this to your production domain (e.g., 'https://iqbalai.com')
    SERVER_URL = os.getenv('SERVER_URL', "https://iqbalai.com")
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size 
