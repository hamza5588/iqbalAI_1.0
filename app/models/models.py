import os
from groq import Groq
from langchain_nomic import NomicEmbeddings
from langchain_community.vectorstores import FAISS
from typing import Optional, List, Dict, Any
import sqlite3
from datetime import datetime
import logging
from app.utils.db import get_db
import pickle

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
                   class_standard: str, medium: str, groq_api_key: str) -> int:
        """Create a new user in the database"""
        try:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO users (username, useremail, password, class_standard, medium, groq_api_key) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (username, useremail, password, class_standard, medium, groq_api_key)
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

    def update_api_key(self, new_api_key: str) -> bool:
        """Update user's Groq API key"""
        try:
            if not self.user_id:
                raise ValueError("User ID is required")
            
            db = get_db()
            db.execute(
                'UPDATE users SET groq_api_key = ? WHERE id = ?',
                (new_api_key, self.user_id)
            )
            db.commit()
            return True
        except Exception as e:
            logger.error(f"API key update failed: {str(e)}")
            raise

# app/models/models.py (ChatModel part)
from langchain_groq import ChatGroq
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# app/models/models.py (ChatModel part)
from langchain_groq import ChatGroq
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

from langchain_groq import ChatGroq
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChatModel:
    """Model for handling chat-related operations"""
    
    def __init__(self, api_key: str, user_id: int = None):
        self.api_key = api_key
        self.user_id = user_id
        self._chat_model = None
        self.vector_store = VectorStoreModel(user_id=user_id)
    
    @property
    def chat_model(self):
        """Lazy initialization of chat model"""
        if not self._chat_model:
            try:
                self._chat_model = ChatGroq(
                    api_key=self.api_key,
                    model_name="llama-3.3-70b-versatile"
                )
            except Exception as e:
                logger.error(f"Failed to initialize chat model: {str(e)}")
                raise
        return self._chat_model

    def generate_response(self, input_text: str, 
                         system_prompt: Optional[str] = None, 
                         chat_history: Optional[List[Dict]] = None) -> str:
        """Generate a response using the chat model with vector store context"""
        try:
            # Initialize messages list
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add formatted chat history if provided
            if chat_history:
                # Ensure chat history is properly formatted
                for msg in chat_history:
                    if 'role' in msg and 'content' in msg:
                        messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": input_text
            })
            
            # Log the messages being sent to the model for debugging
            logger.debug(f"Sending messages to model: {messages}")
            
            # Generate response
            response = self.chat_model.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

# app/models/models.py (VectorStoreModel part)
from typing import List, Optional
from langchain_nomic import NomicEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import os
import pickle
from dotenv import load_dotenv
load_dotenv()

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
                self._embeddings = NomicEmbeddings(
                    model="nomic-embed-text-v1.5"
                )
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

    def save_message(self, conversation_id: int, message: str, role: str) -> int:
        """Save a message to the chat history"""
        try:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO chat_history (conversation_id, message, role) VALUES (?, ?, ?)',
                (conversation_id, message, role)
            )
            
            # Update conversation's last activity
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

class SurveyModel:
    """Model for handling survey-related database operations"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def save_survey_response(self, rating: int) -> int:
        """Save a survey response to the database"""
        try:
            if not isinstance(rating, int) or rating < 1 or rating > 10:
                raise ValueError("Rating must be an integer between 1 and 10")

            db = get_db()
            cursor = db.execute(
                '''INSERT INTO survey_responses (user_id, rating)
                   VALUES (?, ?)''',
                (self.user_id, rating)
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
                '''SELECT rating, created_at
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