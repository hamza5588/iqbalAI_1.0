import sqlite3
import logging
from flask import current_app, g

logger = logging.getLogger(__name__)

def get_db():
    """Get database connection."""
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(
                'chat.db',
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            # Enable foreign key support
            g.db.execute('PRAGMA foreign_keys = ON')
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database: {str(e)}")

def init_db(app):
    """Initialize the database schema."""
    try:
        with app.app_context():
            db = get_db()
            
            # Create users table
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    useremail TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    class_standard TEXT NOT NULL,
                    medium TEXT NOT NULL,
                    groq_api_key TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME
                )
            ''')
            
            # Create conversations table
            db.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create chat_history table
            db.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            ''')
            
            # Create survey_responses table
            db.execute('''
                CREATE TABLE IF NOT EXISTS survey_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    helpful TEXT NOT NULL CHECK(helpful IN ('yes', 'no')),
                    experience TEXT NOT NULL CHECK(experience IN ('excellent', 'good', 'poor')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create user_prompts table
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            db.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_conversation_id ON chat_history(conversation_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_prompts_user_id ON user_prompts(user_id)')
            
            db.commit()
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise