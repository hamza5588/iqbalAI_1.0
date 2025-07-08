import sqlite3
import logging
from flask import current_app, g 
from typing import Dict, Any, Optional, List
logger = logging.getLogger(__name__)

def get_db():
    """Get database connection."""
    if 'db' not in g:
        try:
            print(current_app.config['DATABASE'])
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
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


def update_token_usage(user_id: int, tokens_used: int) -> None:
    """Update the token usage for a user."""
    try:
        db = get_db()
        # Try to update existing record for today
        cursor = db.execute(
            '''UPDATE user_token_usage 
               SET tokens_used = tokens_used + ?, last_updated = CURRENT_TIMESTAMP
               WHERE user_id = ? AND date = CURRENT_DATE''',
            (tokens_used, user_id)
        )
        
        # If no rows were updated, insert a new record
        if cursor.rowcount == 0:
            db.execute(
                '''INSERT INTO user_token_usage (user_id, tokens_used)
                   VALUES (?, ?)''',
                (user_id, tokens_used)
            )
        
        db.commit()
    except Exception as e:
        logger.error(f"Error updating token usage: {str(e)}")
        raise


# token usage functions 
def get_token_usage(user_id: int) -> Dict[str, Any]:
    """Get current token usage for a user."""
    try:
        db = get_db()
        # Get today's usage
        today = db.execute(
            '''SELECT tokens_used, last_updated 
               FROM user_token_usage 
               WHERE user_id = ? AND date = CURRENT_DATE''',
            (user_id,)
        ).fetchone()
        
        # Get historical usage (last 7 days)
        history = db.execute(
            '''SELECT date, tokens_used 
               FROM user_token_usage 
               WHERE user_id = ? AND date >= date('now', '-7 days')
               ORDER BY date DESC''',
            (user_id,)
        ).fetchall()
        
        return {
            'today': dict(today) if today else {'tokens_used': 0, 'last_updated': None},
            'history': [dict(record) for record in history]
        }
    except Exception as e:
        logger.error(f"Error getting token usage: {str(e)}")
        raise

def record_token_reset(user_id: int, tokens_used: int, limit_reached: bool = False) -> None:
    """Record when a user's token counter is reset."""
    try:
        db = get_db()
        db.execute(
            '''INSERT INTO token_reset_history 
               (user_id, tokens_used, was_limit_reached)
               VALUES (?, ?, ?)''',
            (user_id, tokens_used, limit_reached)
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error recording token reset: {str(e)}")
        raise
# ----- >


def init_db(app):
    """Initialize the database schema."""
    try:
        with app.app_context():
            db = get_db()
            
            # Create users table with role column
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    useremail TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('student', 'teacher')),
                    class_standard TEXT NOT NULL,
                    medium TEXT NOT NULL,
                    groq_api_key TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME
                )
            ''')
            
            # Create lessons table to store lessons created by teachers
            db.execute('''
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    learning_objectives TEXT,
                    focus_area TEXT,
                    grade_level TEXT,
                    content TEXT NOT NULL,
                    file_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_public BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
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
            
            # create survey table
            db.execute('''
                CREATE TABLE IF NOT EXISTS survey_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 10),
                    message TEXT,
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

             # Create user_documents table
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    vector_db_ids TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
             # Create user_token_usage table
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL DEFAULT CURRENT_DATE,
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')

            # Create token_reset_history table
            db.execute('''
                CREATE TABLE IF NOT EXISTS token_reset_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reset_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    tokens_used INTEGER NOT NULL,
                    was_limit_reached BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')

            # Create index for token usage tracking
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_token_usage_user_id ON user_token_usage(user_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_token_usage_date ON user_token_usage(date)')

            # Create indexes for lessons table
            db.execute('CREATE INDEX IF NOT EXISTS idx_lessons_teacher_id ON lessons(teacher_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_lessons_grade_level ON lessons(grade_level)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_lessons_focus_area ON lessons(focus_area)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_lessons_is_public ON lessons(is_public)')

            db.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_conversation_id ON chat_history(conversation_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_prompts_user_id ON user_prompts(user_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_user_documents_file_type ON user_documents(file_type)')
            
            db.commit()
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

