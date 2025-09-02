import os
from groq import Groq
from langchain_nomic import NomicEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from typing import Optional, List, Dict, Any
import sqlite3
from datetime import datetime
import logging
from app.utils.db import get_db
from app.config import Config
import pickle
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from httpx import Timeout
from threading import Lock
import time
from collections import deque
import random
import re
import json

logger = logging.getLogger(__name__)
# Add this to your app's initialization code (before any Groq clients are created)
from groq import Groq
from functools import wraps

# model.py
from groq import Groq
from functools import wraps

original_init = Groq.__init__

@wraps(original_init)
def patched_init(self, *args, **kwargs):
    # Log the kwargs before removing 'proxies'
    logger.debug(f"Initializing Groq client with kwargs: {kwargs}")
    if 'proxies' in kwargs:
        logger.debug("Removing 'proxies' from kwargs before initializing Groq client")
        kwargs.pop('proxies')
    return original_init(self, *args, **kwargs)

Groq.__init__ = patched_init
logger.debug("Groq client patched to remove 'proxies' parameter")
class UserModel:
    """User model for handling user-related database operations"""
    
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
    
    @staticmethod
    def create_user(username: str, useremail: str, password: str, 
                   class_standard: str, medium: str, groq_api_key: str, role: str = 'student') -> int:
        """Create a new user in the database"""
        try:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO users (username, useremail, password, class_standard, medium, groq_api_key, role) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, useremail, password, class_standard, medium, groq_api_key, role)
            )
            db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"User creation failed - integrity error: {str(e)}")
            raise ValueError("Username or email already exists")
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise

    @staticmethod
    def get_user_by_email(useremail: str) -> Dict[str, Any]:
        """Retrieve user details by email"""
        try:
            db = get_db()
            user = db.execute(
                'SELECT * FROM users WHERE useremail = ?', 
                (useremail,)
            ).fetchone()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"Error retrieving user by email: {str(e)}")
            raise

    @staticmethod
    def get_user_by_id(user_id: int) -> Dict[str, Any]:
        """Retrieve user details by ID"""
        try:
            db = get_db()
            user = db.execute(
                'SELECT * FROM users WHERE id = ?', 
                (user_id,)
            ).fetchone()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"Error retrieving user by ID: {str(e)}")
            raise

    def update_api_key(self, new_api_key: str) -> bool:
        """Update the user's API key"""
        try:
            db = get_db()
            db.execute(
                'UPDATE users SET groq_api_key = ? WHERE id = ?',
                (new_api_key, self.user_id)
            )
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating API key: {str(e)}")
            return False

    def get_role(self) -> str:
        """Get the user's role"""
        try:
            db = get_db()
            result = db.execute(
                'SELECT role FROM users WHERE id = ?',
                (self.user_id,)
            ).fetchone()
            return result['role'] if result else 'student'
        except Exception as e:
            logger.error(f"Error getting user role: {str(e)}")
            return 'student'

    def is_teacher(self) -> bool:
        """Check if user is a teacher"""
        return self.get_role() == 'teacher'

    def is_student(self) -> bool:
        """Check if user is a student"""
        return self.get_role() == 'student'


class LessonModel:
    """Lesson model for handling lesson-related database operations"""
    
    def __init__(self, lesson_id: Optional[int] = None):
        self.lesson_id = lesson_id
    
    @staticmethod
    def create_lesson(teacher_id: int, title: str, summary: str, learning_objectives: str,
                     focus_area: str, grade_level: str, content: str, file_name: str = None,
                     is_public: bool = True, parent_lesson_id: int = None) -> int:
        """Create a new lesson in the database"""
        try:
            logger.info(f"Saving lesson to database with title: '{title}'")
            db = get_db()
            
            # If this is a new version of an existing lesson, get the next version number
            version = 1
            if parent_lesson_id:
                # Get the highest version number for this parent lesson
                # Only look at versions (where parent_lesson_id is set), not the original lesson
                result = db.execute(
                    '''SELECT MAX(version) as max_version FROM lessons 
                       WHERE parent_lesson_id = ?''',
                    (parent_lesson_id,)
                ).fetchone()
                if result and result['max_version']:
                    version = result['max_version'] + 1
                else:
                    # If no versions exist yet, this is version 2
                    version = 2
                
                logger.info(f"Creating new version for parent lesson {parent_lesson_id}, assigned version {version}")
                logger.info(f"Max version found: {result['max_version'] if result else 'None'}")
            
            cursor = db.execute(
                '''INSERT INTO lessons 
                (teacher_id, title, summary, learning_objectives, focus_area, grade_level, content, file_name, is_public, parent_lesson_id, version) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (teacher_id, title, summary, learning_objectives, focus_area, grade_level, content, file_name, is_public, parent_lesson_id, version)
            )
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating lesson: {str(e)}")
            raise

    @staticmethod
    def get_lesson_by_id(lesson_id: int) -> Dict[str, Any]:
        """Retrieve lesson details by ID"""
        try:
            db = get_db()
            lesson = db.execute(
                '''SELECT l.*, u.username as teacher_name 
                   FROM lessons l 
                   JOIN users u ON l.teacher_id = u.id 
                   WHERE l.id = ?''',
                (lesson_id,)
            ).fetchone()
            if lesson:
                lesson_dict = dict(lesson)
                logger.info(f"Retrieved lesson ID {lesson_id} with title: '{lesson_dict.get('title', 'NO_TITLE')}'")
                return lesson_dict
            else:
                logger.warning(f"No lesson found with ID: {lesson_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving lesson by ID: {str(e)}")
            raise

    @staticmethod
    def get_lessons_by_teacher(teacher_id: int) -> List[Dict[str, Any]]:
        """Get all lessons created by a specific teacher (including all versions)"""
        try:
            db = get_db()
            # Get all lessons for this teacher (originals and all versions)
            lessons = db.execute('''
                SELECT l.* FROM lessons l
                WHERE l.teacher_id = ?
                ORDER BY l.created_at DESC
            ''', (teacher_id,)).fetchall()
            return [dict(lesson) for lesson in lessons]
        except Exception as e:
            logger.error(f"Error retrieving lessons by teacher: {str(e)}")
            raise

    @staticmethod
    def get_public_lessons(grade_level: str = None, focus_area: str = None) -> List[Dict[str, Any]]:
        """Get all public lessons with optional filtering (including all versions)"""
        try:
            db = get_db()
            query = '''SELECT l.*, u.username as teacher_name 
                      FROM lessons l 
                      JOIN users u ON l.teacher_id = u.id 
                      WHERE l.is_public = TRUE'''
            params = []
            
            if grade_level:
                query += ' AND l.grade_level = ?'
                params.append(grade_level)
            
            if focus_area:
                query += ' AND l.focus_area = ?'
                params.append(focus_area)
            
            query += ' ORDER BY l.created_at DESC'
            
            lessons = db.execute(query, params).fetchall()
            return [dict(lesson) for lesson in lessons]
        except Exception as e:
            logger.error(f"Error retrieving public lessons: {str(e)}")
            raise

    @staticmethod
    def search_lessons(search_term: str, grade_level: str = None) -> List[Dict[str, Any]]:
        """Search lessons by title, content, or focus area (including all versions)"""
        try:
            db = get_db()
            query = '''SELECT l.*, u.username as teacher_name 
                      FROM lessons l 
                      JOIN users u ON l.teacher_id = u.id 
                      WHERE l.is_public = TRUE 
                      AND (l.title LIKE ? OR l.content LIKE ? OR l.focus_area LIKE ?)'''
            params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
            
            if grade_level:
                query += ' AND l.grade_level = ?'
                params.append(grade_level)
            
            query += ' ORDER BY l.created_at DESC'
            
            lessons = db.execute(query, params).fetchall()
            return [dict(lesson) for lesson in lessons]
        except Exception as e:
            logger.error(f"Error searching lessons: {str(e)}")
            raise

    def update_lesson(self, title: str = None, summary: str = None, learning_objectives: str = None,
                     focus_area: str = None, grade_level: str = None, content: str = None,
                     is_public: bool = None) -> bool:
        """Update lesson details"""
        try:
            db = get_db()
            updates = []
            params = []
            
            if title is not None:
                updates.append('title = ?')
                params.append(title)
            if summary is not None:
                updates.append('summary = ?')
                params.append(summary)
            if learning_objectives is not None:
                updates.append('learning_objectives = ?')
                params.append(learning_objectives)
            if focus_area is not None:
                updates.append('focus_area = ?')
                params.append(focus_area)
            if grade_level is not None:
                updates.append('grade_level = ?')
                params.append(grade_level)
            if content is not None:
                updates.append('content = ?')
                params.append(content)
            if is_public is not None:
                updates.append('is_public = ?')
                params.append(is_public)
            
            if not updates:
                return True
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(self.lesson_id)
            
            query = f'UPDATE lessons SET {", ".join(updates)} WHERE id = ?'
            db.execute(query, params)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating lesson: {str(e)}")
            return False

    def delete_lesson(self) -> bool:
        """Delete a lesson"""
        try:
            db = get_db()
            db.execute('DELETE FROM lessons WHERE id = ?', (self.lesson_id,))
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting lesson: {str(e)}")
            return False

    @staticmethod
    def create_new_version(original_lesson_id: int, teacher_id: int, title: str, summary: str, 
                          learning_objectives: str, focus_area: str, grade_level: str, 
                          content: str, file_name: str = None, is_public: bool = True) -> int:
        """Create a new version of an existing lesson"""
        try:
            logger.info(f"Creating new version of lesson {original_lesson_id} with title: '{title}'")
            return LessonModel.create_lesson(
                teacher_id=teacher_id,
                title=title,
                summary=summary,
                learning_objectives=learning_objectives,
                focus_area=focus_area,
                grade_level=grade_level,
                content=content,
                file_name=file_name,
                is_public=is_public,
                parent_lesson_id=original_lesson_id
            )
        except Exception as e:
            logger.error(f"Error creating new version: {str(e)}")
            raise

    @staticmethod
    def get_lesson_versions(lesson_id: int) -> List[Dict[str, Any]]:
        """Get all versions of a lesson (including the original and all versions)"""
        try:
            db = get_db()
            # Get the original lesson and all its versions
            lessons = db.execute(
                '''SELECT l.*, u.username as teacher_name 
                   FROM lessons l 
                   JOIN users u ON l.teacher_id = u.id 
                   WHERE l.id = ? OR l.parent_lesson_id = ?
                   ORDER BY l.version ASC, l.id ASC''',
                (lesson_id, lesson_id)
            ).fetchall()
            
            result = [dict(lesson) for lesson in lessons]
            
            # Ensure the original lesson (id = lesson_id) is treated as version 1
            for lesson in result:
                if lesson['id'] == lesson_id and lesson['parent_lesson_id'] is None:
                    lesson['version'] = 1
                    lesson['is_original'] = True
                elif lesson['parent_lesson_id'] == lesson_id:
                    lesson['is_original'] = False
            
            logger.info(f"get_lesson_versions for lesson {lesson_id}: found {len(result)} versions")
            logger.info(f"Versions data: {result}")
            return result
        except Exception as e:
            logger.error(f"Error retrieving lesson versions: {str(e)}")
            raise

    @staticmethod
    def get_latest_version(lesson_id: int) -> Dict[str, Any]:
        """Get the latest version of a lesson"""
        try:
            db = get_db()
            # Get the lesson with the highest version number
            lesson = db.execute(
                '''SELECT l.*, u.username as teacher_name 
                   FROM lessons l 
                   JOIN users u ON l.teacher_id = u.id 
                   WHERE l.id = ? OR l.parent_lesson_id = ?
                   ORDER BY l.version DESC
                   LIMIT 1''',
                (lesson_id, lesson_id)
            ).fetchone()
            return dict(lesson) if lesson else None
        except Exception as e:
            logger.error(f"Error retrieving latest version: {str(e)}")
            raise

    @staticmethod
    def check_title_exists(teacher_id: int, title: str, exclude_lesson_id: int = None) -> bool:
        """Check if a lesson title already exists for a teacher"""
        try:
            db = get_db()
            query = '''SELECT COUNT(*) as count FROM lessons 
                      WHERE teacher_id = ? AND LOWER(title) = LOWER(?)'''
            params = [teacher_id, title.strip()]
            
            # Exclude a specific lesson ID (useful for updates/edits)
            if exclude_lesson_id:
                query += ' AND id != ?'
                params.append(exclude_lesson_id)
            
            result = db.execute(query, params).fetchone()
            return result['count'] > 0
        except Exception as e:
            logger.error(f"Error checking title existence: {str(e)}")
            raise

# app/models/models.py (ChatModel part)
from langchain_groq import ChatGroq
from typing import Optional, List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

class TokenBucket:
    """Token bucket rate limiter implementation"""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity  # maximum tokens
        self.tokens = capacity  # current tokens
        self.last_update = time.time()
        self.lock = Lock()
        self.request_history = deque(maxlen=100)  # Track last 100 requests
        self.error_count = 0
        self.last_error_time = 0
        self.daily_limit_hit = False
        self.daily_limit_reset_time = 0

    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket"""
        with self.lock:
            now = time.time()
            
            # Check if we're in daily limit cooldown
            if self.daily_limit_hit and now < self.daily_limit_reset_time:
                return False
            
            # Add new tokens based on time passed
            time_passed = now - self.last_update
            new_tokens = time_passed * self.rate
            
            # If we've had recent errors, reduce the rate by 25% instead of 50%
            if self.error_count > 0 and now - self.last_error_time < 60:
                new_tokens *= 0.75  # Reduce rate by 25% after errors
            
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                self.request_history.append(now)
                return True
            return False

    def record_error(self, error_data: Optional[Dict] = None):
        """Record an error occurrence"""
        with self.lock:
            self.error_count += 1
            self.last_error_time = time.time()
            
            # Handle daily limit error
            if error_data and isinstance(error_data, dict):
                if error_data.get('code') == 'rate_limit_exceeded' and error_data.get('type') == 'tokens':
                    self.daily_limit_hit = True
                    # Parse the reset time from the error message
                    try:
                        reset_time_str = error_data.get('message', '').split('try again in ')[1].split('.')[0]
                        minutes, seconds = map(int, reset_time_str.split('m'))
                        self.daily_limit_reset_time = time.time() + (minutes * 60) + seconds
                    except:
                        # Default to 1 hour if parsing fails
                        self.daily_limit_reset_time = time.time() + 3600
            
            # Clear error count after 5 minutes
            if time.time() - self.last_error_time > 300:
                self.error_count = 0
                self.daily_limit_hit = False

# class ChatModel:
#     """Model for handling chat-related operations"""
    
#     def __init__(self, api_key: str, user_id: int = None):
#         self.api_key = api_key
#         self.user_id = user_id
#         self._chat_model = None
#         self.vector_store = VectorStoreModel(user_id=user_id)
#         # Optimize timeout settings for faster responses
#         self.timeout = Timeout(
#             timeout=15.0,  # Reduced from 20.0
#             connect=3.0,   # Reduced from 5.0
#             read=10.0,     # Reduced from 15.0
#             write=3.0      # Reduced from 5.0
#         )
#         # Increase rate limiter capacity and rate
#         self.rate_limiter = TokenBucket(rate=10/60, capacity=10)  # Increased from 5/60 and capacity 5
#         self.last_request_time = 0
#         self.min_request_interval = 0.5  # Reduced from 1.0 seconds
#         self.daily_limit = 100000  # Daily token limit
#         self.used_tokens = 0  # Track used tokens
#         self.requested_tokens = 0  # Track requested tokens
    
#     @property
#     def chat_model(self):
#         """Lazy initialization of chat model"""
#         if not self._chat_model:
#             try:
#                 self._chat_model = ChatGroq(
#                     api_key=self.api_key,
#                     model_name="llama-3.3-70b-versatile",
#                     timeout=self.timeout,
#                     max_retries=3,
                  

#                 )
#             except Exception as e:
#                 logger.error(f"Failed to initialize chat model: {str(e)}")
#                 raise
#         return self._chat_model

#     def _wait_for_token(self):
#         """Wait for a token to become available with jitter"""
#         while not self.rate_limiter.acquire():
#             # Add random jitter to prevent thundering herd
#             jitter = random.uniform(0.1, 0.5)
#             time.sleep(jitter)
            
#             # Ensure minimum interval between requests
#             now = time.time()
#             if now - self.last_request_time < self.min_request_interval:
#                 time.sleep(self.min_request_interval - (now - self.last_request_time))

#     def _handle_error(self, error: Exception) -> Dict:
#         """Handle errors and update rate limiter state"""
#         error_info = {
#             'error': str(error),
#             'retry_after': None,
#             'is_daily_limit': False
#         }
        
#         if isinstance(error, httpx.HTTPStatusError):
#             try:
#                 error_data = error.response.json()
#                 self.rate_limiter.record_error(error_data.get('error', {}))
                
#                 if error.response.status_code == 429:
#                     if error_data.get('error', {}).get('type') == 'tokens':
#                         error_info['is_daily_limit'] = True
#                         error_info['retry_after'] = self.rate_limiter.daily_limit_reset_time - time.time()
#                         logger.warning(f"Daily token limit reached. Reset in {error_info['retry_after']} seconds")
#                     else:
#                         logger.warning("Rate limit hit, increasing delay")
#                         time.sleep(10)
#                 elif error.response.status_code >= 500:
#                     logger.warning("Server error, adding delay")
#                     time.sleep(5)
#             except:
#                 logger.error("Error parsing error response")
        
#         elif isinstance(error, httpx.TimeoutException):
#             logger.warning("Request timeout, adding delay")
#             time.sleep(3)
        
#         return error_info

#     @retry(
#         stop=stop_after_attempt(3),  # Increased from 2
#         wait=wait_exponential(multiplier=0.5, min=1, max=5),  # More aggressive retry
#         retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException)),
#         reraise=True
#     )
#     def generate_response(self, input_text: str, 
#                          system_prompt: Optional[str] = None, 
#                          chat_history: Optional[List[Dict]] = None) -> str:
#         """Generate a response using the chat model with vector store context"""
#         try:
#             # Wait for rate limiter token with reduced jitter
#             self._wait_for_token()
#             self.last_request_time = time.time()
            
#             # Initialize messages list
#             messages = []
            
#             # Add system prompt if provided
#             if system_prompt:
#                 messages.append({
#                     "role": "system",
#                     "content": system_prompt
#                 })
            
#             # Add formatted chat history if provided
#             if chat_history:
#                 # Ensure chat history is properly formatted
#                 for msg in chat_history:
#                     if 'role' in msg and 'content' in msg:
#                         messages.append({
#                             "role": msg['role'],
#                             "content": msg['content']
#                         })
            
#             # Add current user message
#             messages.append({
#                 "role": "user",
#                 "content": input_text
#             })
            
#             # Log the messages being sent to the model for debugging
#             logger.debug(f"Sending messages to model: {messages}")
            
#             # Generate response with timeout
#             try:
#                 response = self.chat_model.invoke(messages)
                
#                 # Update token usage
#                 if hasattr(response, 'usage'):
#                     self.used_tokens += response.usage.get('total_tokens', 0)
#                     self.requested_tokens += response.usage.get('prompt_tokens', 0)
#                 else:
#                     # Estimate token usage if not provided
#                     estimated_tokens = len(input_text.split()) * 1.3  # Rough estimation
#                     self.used_tokens += int(estimated_tokens)
#                     self.requested_tokens += int(estimated_tokens)
                
#                 return response.content
#             except Exception as e:
#                 error_info = self._handle_error(e)
#                 if error_info['is_daily_limit']:
#                     raise DailyLimitError(error_info)
#                 raise
            
#         except Exception as e:
#             logger.error(f"Error in generate_response: {str(e)}")
#             if isinstance(e, DailyLimitError):
#                 raise
#             error_info = self._handle_error(e)
#             if error_info['is_daily_limit']:
#                 raise DailyLimitError(error_info)
#             raise

#     def get_token_usage(self) -> Dict[str, Any]:
#         """Get current token usage information"""
#         now = time.time()
#         wait_time = None
        
#         if self.rate_limiter.daily_limit_hit:
#             remaining_time = self.rate_limiter.daily_limit_reset_time - now
#             if remaining_time > 0:
#                 minutes = int(remaining_time // 60)
#                 seconds = int(remaining_time % 60)
#                 wait_time = f"{minutes}m{seconds}s"
        
#         return {
#             'daily_limit': f"{self.daily_limit:,}",
#             'used_tokens': f"{self.used_tokens:,}",
#             'requested_tokens': f"{self.requested_tokens:,}",
#             'wait_time': wait_time
#         } 
#     ## added 2 utility functions  --update_token_usage and  get_token_status
#     def _update_token_usage(self, response):
#         """Update token usage counts from response"""
#         with self.token_lock:
#             if hasattr(response, 'usage'):
#                 tokens_used = response.usage.get('total_tokens', 0)
#             else:
#                 tokens_used = len(response.content) // 4  # Fallback estimation
#                 print("estimated tokens used : {tokens_used}")
            
#             self.used_tokens += tokens_used
            
#             # Update database
#             from app.utils.db import update_token_usage
#             update_token_usage(self.user_id, tokens_used)
            
#             # Check if we've hit the daily limit
#             if self.used_tokens >= self.daily_limit:
#                 raise DailyLimitError({
#                     'retry_after': self.token_reset_time - time.time(),
#                     'is_daily_limit': True
#                 })
    

#     def get_token_status(self):
#         """Return current token usage information"""
#         with self.token_lock:
#             now = time.time()
#             if now > self.token_reset_time:
#                 # Reset counters if 24 hours have passed
#                 from app.utils.db import record_token_reset
#                 record_token_reset(
#                     self.user_id,
#                     self.used_tokens,
#                     self.used_tokens >= self.daily_limit
#                 )
#                 self.used_tokens = 0
#                 self.token_reset_time = now + 86400
            
#             # Get usage from database for accurate reporting
#             from app.utils.db import get_token_usage
#             db_usage = get_token_usage(self.user_id)
            
#             return {
#                 'used': db_usage['today']['tokens_used'],
#                 'remaining': max(0, self.daily_limit - db_usage['today']['tokens_used']),
#                 'limit': self.daily_limit,
#                 'reset_time': self.token_reset_time,
#                 'reset_in': max(0, self.token_reset_time - now),
#                 'history': db_usage['history']
#             }


from langchain_community.embeddings import HuggingFaceEmbeddings

class ChatModel:
    """Model for handling chat-related operations"""
    
    def __init__(self, api_key: str, user_id: int = None):
        self.api_key = api_key
        self.user_id = user_id
        self._chat_model = None
        self.vector_store = VectorStoreModel(user_id=user_id)
        
        # Token tracking attributes
        self.token_lock = Lock()  # Critical missing piece
        self.used_tokens = 0
        self.requested_tokens = 0
        self.daily_limit = 100000
        self.token_reset_time = time.time() + 86400  # 24 hours from now
        
        # Request rate limiting
        self.timeout = Timeout(
            timeout=15.0,
            connect=3.0,
            read=10.0,
            write=3.0
        )
        self.rate_limiter = TokenBucket(rate=10/60, capacity=10)
        self.last_request_time = 0
        self.min_request_interval = 0.5
    
    @property
    def chat_model(self):
        """Lazy initialization of chat model"""
        if not self._chat_model:
            try:
                self._chat_model = ChatGroq(
                    api_key=self.api_key,
                    model_name="llama-3.3-70b-versatile",
                    timeout=self.timeout,
                    max_retries=3,
                )
            except Exception as e:
                logger.error(f"Failed to initialize chat model: {str(e)}")
                raise
        return self._chat_model

    def _wait_for_token(self):
        """Wait for a token to become available with jitter"""
        while not self.rate_limiter.acquire():
            jitter = random.uniform(0.1, 0.5)
            time.sleep(jitter)
            
            now = time.time()
            if now - self.last_request_time < self.min_request_interval:
                time.sleep(self.min_request_interval - (now - self.last_request_time))

    def _handle_error(self, error: Exception) -> Dict:
        """Handle errors and update rate limiter state"""
        error_info = {
            'error': str(error),
            'retry_after': None,
            'is_daily_limit': False
        }
        
        if isinstance(error, httpx.HTTPStatusError):
            try:
                error_data = error.response.json()
                self.rate_limiter.record_error(error_data.get('error', {}))
                
                if error.response.status_code == 429:
                    if error_data.get('error', {}).get('type') == 'tokens':
                        error_info['is_daily_limit'] = True
                        error_info['retry_after'] = self.rate_limiter.daily_limit_reset_time - time.time()
                        logger.warning(f"Daily token limit reached. Reset in {error_info['retry_after']} seconds")
                    else:
                        logger.warning("Rate limit hit, increasing delay")
                        time.sleep(10)
                elif error.response.status_code >= 500:
                    logger.warning("Server error, adding delay")
                    time.sleep(5)
            except:
                logger.error("Error parsing error response")
        
        elif isinstance(error, httpx.TimeoutException):
            logger.warning("Request timeout, adding delay")
            time.sleep(3)
        
        return error_info

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    def generate_response(self, input_text: str, 
                         system_prompt: Optional[str] = None, 
                         chat_history: Optional[List[Dict]] = None) -> str:
        """Generate a response using the chat model with vector store context"""
        try:
            self._wait_for_token()
            self.last_request_time = time.time()
            
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            if chat_history:
                for msg in chat_history:
                    if 'role' in msg and 'content' in msg:
                        messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            messages.append({"role": "user", "content": input_text})
            
            logger.debug(f"Sending messages to model: {messages}")
            
            try:
                response = self.chat_model.invoke(messages)
                self._update_token_usage(response)  # Updated to use the proper method
                return response.content
            except Exception as e:
                error_info = self._handle_error(e)
                if error_info['is_daily_limit']:
                    raise DailyLimitError(error_info)
                raise
            
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}")
            if isinstance(e, DailyLimitError):
                raise
            error_info = self._handle_error(e)
            if error_info['is_daily_limit']:
                raise DailyLimitError(error_info)
            raise

    def _update_token_usage(self, response):
        """Update token usage counts from response"""
        with self.token_lock:
            try:
                if hasattr(response, 'usage'):
                    tokens_used = response.usage.get('total_tokens', 0)
                else:
                    tokens_used = len(response.content) // 4  # Fallback estimation
                    logger.debug(f"Estimated tokens used: {tokens_used}")
                
                self.used_tokens += tokens_used
                self.requested_tokens += tokens_used
                
                # Update database
                if self.user_id:
                    from app.utils.db import update_token_usage
                    update_token_usage(self.user_id, tokens_used)
                
                if self.used_tokens >= self.daily_limit:
                    raise DailyLimitError({
                        'retry_after': self.token_reset_time - time.time(),
                        'is_daily_limit': True
                    })
            except Exception as e:
                logger.error(f"Error updating token usage: {str(e)}")
                raise

    def get_token_status(self) -> Dict[str, Any]:
        """Get current token usage information"""
        with self.token_lock:
            now = time.time()
            
            # Reset if 24 hours have passed
            if now > self.token_reset_time:
                if self.user_id:
                    from app.utils.db import record_token_reset
                    record_token_reset(
                        self.user_id,
                        self.used_tokens,
                        self.used_tokens >= self.daily_limit
                    )
                self.used_tokens = 0
                self.token_reset_time = now + 86400
            
            # Get usage from database if available
            db_usage = {'today': {'tokens_used': self.used_tokens}, 'history': []}
            if self.user_id:
                try:
                    from app.utils.db import get_token_usage
                    db_usage = get_token_usage(self.user_id)
                except Exception as e:
                    logger.error(f"Error getting token usage from DB: {str(e)}")
            
            return {
                'used': db_usage['today']['tokens_used'],
                'remaining': max(0, self.daily_limit - db_usage['today']['tokens_used']),
                'limit': self.daily_limit,
                'reset_time': self.token_reset_time,
                'reset_in': max(0, self.token_reset_time - now),
                'history': db_usage.get('history', [])
            }


class DailyLimitError(Exception):
    """Custom exception for daily token limit errors"""
    def __init__(self, error_info: Dict):
        self.error_info = error_info
        self.retry_after = error_info.get('retry_after', 3600)  # Default to 1 hour
        super().__init__(f"Daily token limit reached. Please try again in {int(self.retry_after/60)} minutes")

# app/models/models.py (VectorStoreModel part)
from typing import List, Optional
from langchain_nomic import NomicEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import os
import pickle

logger = logging.getLogger(__name__)

class VectorStoreModel:
    """Model for handling vector store operations with multi-user support"""
    
    _instance = None
    VECTOR_STORE_PATH = "shared_vector_store.pkl"
    
    def __new__(cls, user_id: int = None):
        if cls._instance is None:
            instance = super(VectorStoreModel, cls).__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance
    
    def __init__(self, user_id: int = None):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._embeddings = None
            self._vectorstore = None
            self._initialized = True
            self._load_existing_store()
        self.user_id = user_id
    
    def _load_existing_store(self):
        """Load existing vector store if available"""
        try:
            if os.path.exists(self.VECTOR_STORE_PATH):
                with open(self.VECTOR_STORE_PATH, 'rb') as f:
                    self._vectorstore = pickle.load(f)
                logger.info("Loaded shared vector store")
        except Exception as e:
            logger.error(f"Error loading shared vector store: {str(e)}")
    
    def _save_store(self):
        """Save vector store to disk"""
        try:
            if self._vectorstore:
                with open(self.VECTOR_STORE_PATH, 'wb') as f:
                    pickle.dump(self._vectorstore, f)
                logger.info("Saved shared vector store to disk")
        except Exception as e:
            logger.error(f"Error saving shared vector store: {str(e)}")
    
    @property
    def embeddings(self):
        """Lazy initialization of embeddings"""
        if not self._embeddings:
            try:
                nomic_api_key = Config.NOMIC_API_KEY
                if nomic_api_key == 'your_nomic_api_key_here':
                    raise ValueError("Please configure your Nomic API key in the config file")
                
                # self._embeddings = NomicEmbeddings(
                #     model="nomic-embed-text-v1.5",
                #     nomic_api_key=nomic_api_key
                # )
                self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

            except Exception as e:
                logger.error(f"Failed to create embeddings: {str(e)}")
                raise
        return self._embeddings

    def create_vectorstore(self, documents: List) -> None:
        """Create or update vector store with documents"""
        if not self.user_id:
            raise ValueError("User ID is required for vector store operations")
            
        try:
            # Add user_id to metadata of each document
            for doc in documents:
                doc.metadata['user_id'] = self.user_id
            
            if not self._vectorstore:
                self._vectorstore = FAISS.from_documents(
                    documents, 
                    self.embeddings
                )
            else:
                self._vectorstore.add_documents(documents)
            
            # Save the updated store
            self._save_store()
            logger.info(f"Successfully processed {len(documents)} documents into shared vector store for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error creating/updating vector store for user {self.user_id}: {str(e)}")
            raise

    def search_similar(self, query: str, k: int = 3) -> List:
        """Search for similar documents in the vector store with user isolation"""
        if not self.user_id:
            raise ValueError("User ID is required for vector store operations")
            
        try:
            if not self._vectorstore:
                logger.warning(f"Vector store not initialized or empty")
                return []
            
            # Search with metadata filter for user_id
            results = self._vectorstore.similarity_search(
                query,
                k=k,
                filter={"user_id": self.user_id}  # Only return documents belonging to this user
            )
            
            logger.info(f"Found {len(results)} relevant documents for query from user {self.user_id}")
            return results
        except Exception as e:
            logger.error(f"Error searching vector store for user {self.user_id}: {str(e)}")
            return []

    def delete_user_documents(self) -> None:
        """Delete all documents for a specific user"""
        if not self.user_id:
            raise ValueError("User ID is required for vector store operations")
            
        try:
            if self._vectorstore and hasattr(self._vectorstore, 'delete'):
                # Delete documents with matching user_id
                self._vectorstore.delete(filter={"user_id": self.user_id})
                self._save_store()
                logger.info(f"Deleted all documents for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error deleting documents for user {self.user_id}: {str(e)}")
            raise

# class ConversationModel:
#     """Model for handling conversation-related database operations"""
    
#     def __init__(self, user_id: int):
#         self.user_id = user_id
    
#     def create_conversation(self, title: str) -> int:
#         """Create a new conversation"""
#         try:
#             db = get_db()
#             cursor = db.execute(
#                 'INSERT INTO conversations (user_id, title) VALUES (?, ?)',
#                 (self.user_id, title)
#             )
#             db.commit()
#             return cursor.lastrowid
#         except Exception as e:
#             logger.error(f"Error creating conversation: {str(e)}")
#             raise

#     def get_conversations(self, limit: int = 4) -> List[Dict]:
#         """Get user's recent conversations"""
#         try:
#             db = get_db()
#             conversations = db.execute(
#                 '''SELECT c.id, c.title, MAX(ch.created_at) as last_message
#                    FROM conversations c
#                    LEFT JOIN chat_history ch ON c.id = ch.conversation_id
#                    WHERE c.user_id = ?
#                    GROUP BY c.id
#                    ORDER BY last_message DESC
#                    LIMIT ?''',
#                 (self.user_id, limit)
#             ).fetchall()
#             return [dict(conv) for conv in conversations]
#         except Exception as e:
#             logger.error(f"Error retrieving conversations: {str(e)}")
#             raise

#     def save_message(self, conversation_id: int, message: str, role: str) -> int:
#         """Save a message to the chat history"""
#         try:
#             db = get_db()
#             cursor = db.execute(
#                 'INSERT INTO chat_history (conversation_id, message, role) VALUES (?, ?, ?)',
#                 (conversation_id, message, role)
#             )
            
#             # Update conversation's last activity
#             db.execute(
#                 'UPDATE conversations SET updated_at = ? WHERE id = ?',
#                 (datetime.now().isoformat(), conversation_id)
#             )
            
#             db.commit()
#             return cursor.lastrowid
#         except Exception as e:
#             logger.error(f"Error saving message: {str(e)}")
#             raise

#     def get_chat_history(self, conversation_id: int) -> List[Dict]:
#         """Get chat history for a conversation"""
#         try:
#             db = get_db()
#             messages = db.execute(
#                 '''SELECT message, role, created_at
#                    FROM chat_history
#                    WHERE conversation_id = ?
#                    ORDER BY created_at''',
#                 (conversation_id,)
#             ).fetchall()
#             return [dict(msg) for msg in messages]
#         except Exception as e:
#             logger.error(f"Error retrieving chat history: {str(e)}")
#             raise

#     def delete_conversation(self, conversation_id: int) -> None:
#         """Delete a conversation and its associated messages"""
#         try:
#             db = get_db()
#             # Delete the conversation (this will cascade delete chat_history due to foreign key constraint)
#             db.execute(
#                 'DELETE FROM conversations WHERE id = ? AND user_id = ?',
#                 (conversation_id, self.user_id)
#             )
#             db.commit()
#         except Exception as e:
#             logger.error(f"Error deleting conversation: {str(e)}")
#             raise



class ConversationModel:
    """Model for handling conversation-related database operations"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def create_conversation(self, title: str) -> int:
        """Create a new conversation"""
        try:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO conversations (user_id, title) VALUES (?, ?)',
                (self.user_id, title)
            )
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise
    
    def get_conversations(self, limit: int = 4) -> List[Dict]:
        """Get user's recent conversations"""
        try:
            db = get_db()
            conversations = db.execute(
                '''SELECT c.id, c.title, MAX(ch.created_at) as last_message
                   FROM conversations c
                   LEFT JOIN chat_history ch ON c.id = ch.conversation_id
                   WHERE c.user_id = ?
                   GROUP BY c.id
                   ORDER BY last_message DESC
                   LIMIT ?''',
                (self.user_id, limit)
            ).fetchall()
            return [dict(conv) for conv in conversations]
        except Exception as e:
            logger.error(f"Error retrieving conversations: {str(e)}")
            raise
    
    def get_conversation_by_id(self, conversation_id: int) -> Dict:
        """Get a specific conversation by ID"""
        try:
            db = get_db()
            conversation = db.execute(
                '''SELECT id, title, created_at 
                   FROM conversations 
                   WHERE id = ? AND user_id = ?''',
                (conversation_id, self.user_id)
            ).fetchone()
            return dict(conversation) if conversation else None
        except Exception as e:
            logger.error(f"Error retrieving conversation: {str(e)}")
            raise
    
    def update_conversation_title(self, conversation_id: int, new_title: str) -> bool:
        """Update the title of a conversation"""
        try:
            db = get_db()
            cursor = db.execute(
                '''UPDATE conversations 
                   SET title = ? 
                   WHERE id = ? AND user_id = ?''',
                (new_title, conversation_id, self.user_id)
            )
            db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating conversation title: {str(e)}")
            raise
    
    def save_message(self, conversation_id: int, message: str, role: str) -> int:
        """Save a message to the chat history"""
        try:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO chat_history (conversation_id, message, role) VALUES (?, ?, ?)',
                (conversation_id, message, role)
            )
            
            # Update conversation's last activity
            from datetime import datetime
            db.execute(
                'UPDATE conversations SET updated_at = ? WHERE id = ?',
                (datetime.now().isoformat(), conversation_id)
            )
            
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            raise
    
    def get_chat_history(self, conversation_id: int) -> List[Dict]:
        """Get chat history for a conversation"""
        try:
            db = get_db()
            messages = db.execute(
                '''SELECT message, role, created_at
                   FROM chat_history
                   WHERE conversation_id = ?
                   ORDER BY created_at''',
                (conversation_id,)
            ).fetchall()
            return [dict(msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
            raise

    def delete_conversation(self, conversation_id: int) -> None:
        """Delete a conversation and its associated messages"""
        try:
            db = get_db()
            # Delete the conversation (this will cascade delete chat_history due to foreign key constraint)
            db.execute(
                'DELETE FROM conversations WHERE id = ? AND user_id = ?',
                (conversation_id, self.user_id)
            )
            db.commit()
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            raise

    def reset_all_chats(self) -> None:
        """Delete all conversations and chat history for the user"""
        try:
            db = get_db()
            # Delete all conversations for the user (this will cascade delete all chat_history)
            db.execute(
                'DELETE FROM conversations WHERE user_id = ?',
                (self.user_id,)
            )
            db.commit()
            logger.info(f"All chats reset for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error resetting all chats: {str(e)}")
            raise








class SurveyModel:
    """Model for handling survey-related database operations"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def save_survey_response(self, rating: int, message: str = None) -> int:
        """Save a survey response to the database"""
        try:
            if not isinstance(rating, int) or rating < 1 or rating > 10:
                raise ValueError("Rating must be an integer between 1 and 10")

            db = get_db()
            cursor = db.execute(
                '''INSERT INTO survey_responses (user_id, rating, message)
                   VALUES (?, ?, ?)''',
                (self.user_id, rating, message)
            )
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving survey response: {str(e)}")
            raise
    
    def get_user_survey_responses(self) -> List[Dict]:
        """Get all survey responses for a user"""
        try:
            db = get_db()
            responses = db.execute(
                '''SELECT rating, message, created_at
                   FROM survey_responses
                   WHERE user_id = ?
                   ORDER BY created_at DESC''',
                (self.user_id,)
            ).fetchall()
            return [dict(response) for response in responses]
        except Exception as e:
            logger.error(f"Error retrieving survey responses: {str(e)}")
            raise

    def has_submitted_survey(self):
        """Check if the user has already submitted a survey"""
        try:
            logger.info(f"Checking survey submission status for user_id: {self.user_id}")
            db = get_db()
            result = db.execute(
                'SELECT COUNT(*) as count FROM survey_responses WHERE user_id = ?',
                (self.user_id,)
            ).fetchone()
            count = result['count']
            
            status = "has" if count > 0 else "has not"
            logger.info(f"Survey check result: User {self.user_id} {status} submitted a survey (count: {count})")
            
            return count > 0
        except Exception as e:
            logger.error(f"Error checking survey submission for user {self.user_id}: {str(e)}")
            raise

import sqlite3

class LessonFAQ:
    @staticmethod
    def log_question(lesson_id, question):
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS lesson_faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            question TEXT,
            count INTEGER DEFAULT 1
        )''')
        # Check if question already exists for this lesson
        c.execute('SELECT id, count FROM lesson_faq WHERE lesson_id=? AND question=?', (lesson_id, question))
        row = c.fetchone()
        if row:
            c.execute('UPDATE lesson_faq SET count = count + 1 WHERE id=?', (row[0],))
        else:
            c.execute('INSERT INTO lesson_faq (lesson_id, question, count) VALUES (?, ?, 1)', (lesson_id, question))
        conn.commit()
        conn.close()

    @staticmethod
    def get_top_faqs(lesson_id, limit=5):
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS lesson_faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            question TEXT,
            count INTEGER DEFAULT 1
        )''')
        c.execute('SELECT question, count FROM lesson_faq WHERE lesson_id=? ORDER BY count DESC LIMIT ?', (lesson_id, limit))
        faqs = [{'question': row[0], 'count': row[1]} for row in c.fetchall()]
        conn.close()
        return faqs

class LessonChatHistory:
    """Model for handling lesson-specific chat history"""
    
    @staticmethod
    def create_table():
        """Create the lesson_chat_history table if it doesn't exist"""
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS lesson_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def save_qa(lesson_id: int, user_id: int, question: str, answer: str) -> int:
        """Save a Q&A pair for a specific lesson and user"""
        LessonChatHistory.create_table()
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO lesson_chat_history 
                     (lesson_id, user_id, question, answer) 
                     VALUES (?, ?, ?, ?)''', 
                  (lesson_id, user_id, question, answer))
        conn.commit()
        chat_id = c.lastrowid
        conn.close()
        return chat_id
    
    @staticmethod
    def get_lesson_chat_history(lesson_id: int, user_id: int) -> List[Dict]:
        """Get chat history for a specific lesson and user"""
        LessonChatHistory.create_table()
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''SELECT question, answer, created_at 
                     FROM lesson_chat_history 
                     WHERE lesson_id = ? AND user_id = ?
                     ORDER BY created_at ASC''', (lesson_id, user_id))
        history = [{'question': row[0], 'answer': row[1], 'created_at': row[2]} 
                  for row in c.fetchall()]
        conn.close()
        return history
    
    @staticmethod
    def clear_lesson_chat_history(lesson_id: int, user_id: int) -> None:
        """Clear chat history for a specific lesson and user"""
        LessonChatHistory.create_table()
        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        c.execute('''DELETE FROM lesson_chat_history 
                     WHERE lesson_id = ? AND user_id = ?''', (lesson_id, user_id))
        conn.commit()
        conn.close()