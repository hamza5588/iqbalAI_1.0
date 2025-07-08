import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production
    
    # Email configuration
    # MAIL_SERVER = 'mail.privateemail.com'
    # MAIL_PORT = 587
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    # MAIL_USERNAME = 'info@iqbalai.com'  # Make sure this is the full email address
    # MAIL_PASSWORD = 'Iqbalai12@'  # Make sure this is the correct app-specific password
    # MAIL_DEFAULT_SENDER = 'info@iqbalai.com'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'y7hamzakhanswati@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'oyte uhxj ytrz vsms')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME', 'y7hamzakhanswati@gmail.com')
    MAIL_DEBUG = True  # Enable debug mode to see more detailed logs

    
    # Database configuration
    DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'chatbot.db')
    
    # Nomic API configuration
    NOMIC_API_KEY = os.getenv('NOMIC_API_KEY', 'nk-7Em9YdxJJI09E4vXTxJ9VOC2zygDGWD9eGBYxDLuG0E')  # Replace with your Nomic API key 