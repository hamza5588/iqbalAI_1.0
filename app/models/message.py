from typing import Dict
import logging
from app.utils.db import get_db

logger = logging.getLogger(__name__)

class Message:
    """Model for handling message-related database operations"""
    
    def __init__(self, conversation_id: int):
        self.conversation_id = conversation_id
    
    def save(self, content: str, role: str) -> int:
        """Save a message to the database"""
        try:
            db = get_db()
            cursor = db.execute(
                '''INSERT INTO messages (conversation_id, content, role)
                   VALUES (?, ?, ?)''',
                (self.conversation_id, content, role)
            )
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            raise
    
    @staticmethod
    def get_messages(conversation_id: int) -> list[Dict]:
        """Get all messages for a conversation"""
        try:
            db = get_db()
            messages = db.execute(
                '''SELECT id, content, role, created_at
                   FROM messages
                   WHERE conversation_id = ?
                   ORDER BY created_at ASC''',
                (conversation_id,)
            ).fetchall()
            return [dict(msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            raise 