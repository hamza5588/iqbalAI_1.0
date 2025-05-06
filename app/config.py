import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production
    
    # Email configuration
    MAIL_SERVER = 'mail.privateemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'info@iqbalai.com'  # Make sure this is the full email address
    MAIL_PASSWORD = 'Iqbalai12@'  # Make sure this is the correct app-specific password
    MAIL_DEFAULT_SENDER = 'info@iqbalai.com'
    MAIL_DEBUG = True  # Enable debug mode to see more detailed logs
    
    # Database configuration
    DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'chatbot.db') 