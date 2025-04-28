# # app/services/chat_service.py
# from typing import List, Dict, Optional, Any
# from app.models import ChatModel, ConversationModel, VectorStoreModel
# import logging
# from datetime import datetime

# logger = logging.getLogger(__name__)

# class ChatService:
#     """Service class for handling chat-related business logic"""
    
#     def __init__(self, user_id: int, api_key: str):
#         self.user_id = user_id
#         self.chat_model = ChatModel(api_key)
#         self.conversation_model = ConversationModel(user_id)
#         self.vector_store = VectorStoreModel()
        
#     def format_chat_history(self, history: List[Dict]) -> List[Dict]:
#         """Format chat history for the LLM"""
#         formatted_history = []
#         for msg in history:
#             # Map 'bot' role to 'assistant' and ensure we access the correct message field
#             role = 'assistant' if msg.get('role') == 'bot' else msg.get('role', 'user')
#             content = msg.get('message', '')  # Get message content with default empty string
            
#             if content and role:  # Only add if we have both content and role
#                 formatted_history.append({
#                     'role': role,
#                     'content': content
#                 })
#         return formatted_history
        
#     def process_message(self, message: str, 
#                        conversation_id: Optional[int] = None,
#                        system_prompt: Optional[str] = None) -> Dict[str, Any]:
#         """Process a user message and generate a response"""
#         try:
#             # Create new conversation if needed
#             if not conversation_id:
#                 conversation_id = self.conversation_model.create_conversation(
#                     title=message[:50]
#                 )
            
#             # Save user message
#             self.conversation_model.save_message(
#                 conversation_id=conversation_id,
#                 message=message,
#                 role='user'
#             )
            
#             # Get relevant context from vector store
#             context = ""
#             try:
#                 if self.vector_store._vectorstore:
#                     relevant_docs = self.vector_store.search_similar(message, k=3)
#                     if relevant_docs:
#                         context = "Using the provided documents, I found this relevant information:\n\n" + "\n".join(
#                             [f"• {doc.page_content.strip()}" for doc in relevant_docs]
#                         )
#                         logger.info("Found relevant context from documents")
#             except Exception as e:
#                 logger.warning(f"Error retrieving context: {str(e)}")
            
#             # Enhance system prompt with context
#             enhanced_prompt = "You are a helpful assistant. "
#             if system_prompt:
#                 enhanced_prompt += system_prompt
#             if context:
#                 enhanced_prompt += f"\n\n{context}\n\nPlease use this information to answer the question accurately."
            
#             # Get and format chat history
#             raw_history = self.conversation_model.get_chat_history(conversation_id)
#             formatted_history = self.format_chat_history(raw_history)
            
#             # For debugging
#             logger.debug(f"Formatted history: {formatted_history}")
            
#             # Generate response
#             response = self.chat_model.generate_response(
#                 input_text=message,
#                 system_prompt=enhanced_prompt,
#                 chat_history=formatted_history
#             )
            
#             # Save bot response
#             self.conversation_model.save_message(
#                 conversation_id=conversation_id,
#                 message=response,
#                 role='bot'
#             )
            
#             return {
#                 'response': response,
#                 'conversation_id': conversation_id
#             }
            
#         except Exception as e:
#             logger.error(f"Error processing message: {str(e)}")
#             raise

#     def get_recent_conversations(self, limit: int = 4) -> List[Dict[str, Any]]:
#         """Get user's recent conversations"""
#         try:
#             return self.conversation_model.get_conversations(limit=limit)
#         except Exception as e:
#             logger.error(f"Error retrieving conversations: {str(e)}")
#             raise

#     def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
#         """Get messages for a specific conversation"""
#         try:
#             raw_messages = self.conversation_model.get_chat_history(conversation_id)
#             return [
#                 {
#                     'role': msg.get('role', 'user'),
#                     'message': msg.get('message', ''),
#                     'created_at': msg.get('created_at', datetime.now().isoformat())
#                 }
#                 for msg in raw_messages
#             ]
#         except Exception as e:
#             logger.error(f"Error retrieving messages: {str(e)}")
#             raise

#     def create_conversation(self, title: str) -> int:
#         """Create a new conversation"""
#         try:
#             return self.conversation_model.create_conversation(title)
#         except Exception as e:
#             logger.error(f"Error creating conversation: {str(e)}")
#             raise

#     def delete_conversation(self, conversation_id: int) -> None:
#         """Delete a conversation"""
#         try:
#             self.conversation_model.delete_conversation(conversation_id)
#         except Exception as e:
#             logger.error(f"Error deleting conversation: {str(e)}")
#             raise

#     def clean_old_conversations(self, max_conversations: int = 50) -> None:
#         """Clean up old conversations beyond the maximum limit"""
#         try:
#             conversations = self.conversation_model.get_conversations()
#             if len(conversations) > max_conversations:
#                 for conv in conversations[max_conversations:]:
#                     self.delete_conversation(conv['id'])
#         except Exception as e:
#             logger.error(f"Error cleaning old conversations: {str(e)}")
#             raise



# app/services/chat_service.py
# app/services/chat_service.py
# app/services/chat_service.py
# app/services/chat_service.py
from typing import List, Dict, Optional, Any
from app.models import ChatModel, ConversationModel, VectorStoreModel
import logging
from datetime import datetime
import re
import httpx
import time

logger = logging.getLogger(__name__)

class ChatService:
    """Service class for handling chat-related business logic"""
    
    def __init__(self, user_id: int, api_key: str):
        self.user_id = user_id
        self.api_key = api_key
        self._chat_model = None  # Will be lazily initialized
        self.conversation_model = ConversationModel(user_id)
        self.vector_store = VectorStoreModel(user_id=user_id)
        self._document_context_cache = {}  # Cache for document contexts
        self._cache_ttl = 180  # Reduced from 300 (3 minutes instead of 5)
        self._cache_cleanup_interval = 60  # Clean up cache every minute
        self._last_cache_cleanup = time.time()
    
    @property
    def chat_model(self):
        """Lazy initialization of chat model with caching"""
        if not self._chat_model:
            self._chat_model = ChatModel(api_key=self.api_key, user_id=self.user_id)
        return self._chat_model

    def _create_new_chat_model(self):
        """Create a fresh chat model instance for each conversation"""
        return ChatModel(api_key=self.api_key, user_id=self.user_id)
        
    def format_chat_history(self, history: List[Dict]) -> List[Dict]:
        """Format chat history for the LLM"""
        formatted_history = []
        for msg in history:
            role = 'assistant' if msg.get('role') == 'bot' else msg.get('role', 'user')
            content = msg.get('message', '')
            
            if content and role:
                formatted_history.append({
                    'role': role,
                    'content': content
                })
        return formatted_history
        
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        if current_time - self._last_cache_cleanup >= self._cache_cleanup_interval:
            expired_keys = [
                key for key, value in self._document_context_cache.items()
                if current_time - value['timestamp'] >= self._cache_ttl
            ]
            for key in expired_keys:
                del self._document_context_cache[key]
            self._last_cache_cleanup = current_time

    def get_document_context(self, message: str) -> str:
        """Get relevant context from uploaded documents with optimized caching"""
        try:
            # Clean up cache periodically
            self._cleanup_cache()
            
            # Check cache first
            cache_key = f"{self.user_id}:{message}"
            cached_result = self._document_context_cache.get(cache_key)
            if cached_result and time.time() - cached_result['timestamp'] < self._cache_ttl:
                return cached_result['context']

            if self.vector_store._vectorstore:
                # Check if the query is asking about a specific page
                page_match = re.search(r'page\s*(\d+)', message.lower())
                page_number = int(page_match.group(1)) if page_match else None
                
                # Reduce k from 3 to 2 for faster search
                relevant_docs = self.vector_store.search_similar(message, k=2)
                if relevant_docs:
                    context_parts = []
                    for doc in relevant_docs:
                        page = doc.metadata.get('page', 1)
                        if page_number is not None and page != page_number:
                            continue
                        context_parts.append(
                            f"Page {page}:\n{doc.page_content.strip()}"
                        )
                    
                    if context_parts:
                        context = "Based on the uploaded documents:\n\n" + "\n\n".join(context_parts)
                        # Cache the result
                        self._document_context_cache[cache_key] = {
                            'context': context,
                            'timestamp': time.time()
                        }
                        return context
                    elif page_number is not None:
                        return f"I couldn't find any relevant information on page {page_number}."
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error retrieving document context: {str(e)}")
            return ""
            
    def process_message(self, message: str, 
                       conversation_id: Optional[int] = None,
                       system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Process a user message and generate a response"""
        try:
            # Get document context
            document_context = self.get_document_context(message)
            
            # Base system prompt
            base_prompt = """You are a helpful Mr. Potter Ai assistant that provides answers based on the provided documents.
            Your primary goal is to help users understand the content of their documents.
            
            Guidelines for document-based assistance:
            1. Always prioritize information from the provided documents
            2. If the answer is not in the documents, clearly state that
            3. When referencing document content:
               - Mention the page number if available
               - Quote relevant sections
               - Explain the context
            4. For multi-document queries:
               - Compare information across documents
               - Highlight any contradictions
               - Provide a comprehensive view
            5. If the user asks about something not in the documents:
               - Acknowledge the limitation
               - Suggest what information would be needed
               - Offer to help with other document-related questions
            
            Always maintain a helpful and professional tone while focusing on the document content."""

            if document_context:
                base_prompt = f"{base_prompt}\n\n{document_context}"

            if system_prompt:
                limit = "always answer in 50 words or less"
                base_prompt = f"{system_prompt} {limit}"

            # Handle new conversation
            if not conversation_id:
                conversation_id = self.conversation_model.create_conversation(
                    title=message[:50]
                )
                
                # Generate response with no history
                try:
                    response = self.chat_model.generate_response(
                        input_text=message,
                        system_prompt=base_prompt,
                        chat_history=[]
                    )
                except httpx.TimeoutException:
                    logger.warning("Request timed out during response generation")
                    return {
                        'error': 'The request is taking longer than expected. Please wait a moment and try again.',
                        'conversation_id': conversation_id
                    }
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning("Rate limit hit during response generation")
                        return {
                            'error': 'The system is currently experiencing high demand. Please wait a moment and try again.',
                            'conversation_id': conversation_id
                        }
                    elif e.response.status_code >= 500:
                        logger.warning(f"Server error during response generation: {str(e)}")
                        return {
                            'error': 'The AI service is temporarily unavailable. Please try again in a few moments.',
                            'conversation_id': conversation_id
                        }
                    raise
                
                # Save messages
                self.conversation_model.save_message(
                    conversation_id=conversation_id,
                    message=message,
                    role='user'
                )
                
                self.conversation_model.save_message(
                    conversation_id=conversation_id,
                    message=response,
                    role='bot'
                )
                
            # Handle existing conversation
            else:
                self.conversation_model.save_message(
                    conversation_id=conversation_id,
                    message=message,
                    role='user'
                )
                
                # Get history only for this conversation
                raw_history = self.conversation_model.get_chat_history(conversation_id)
                formatted_history = self.format_chat_history(raw_history)
                
                try:
                    response = self.chat_model.generate_response(
                        input_text=message,
                        system_prompt=base_prompt,
                        chat_history=formatted_history
                    )
                except httpx.TimeoutException:
                    logger.warning("Request timed out during response generation")
                    return {
                        'error': 'The request is taking longer than expected. Please wait a moment and try again.',
                        'conversation_id': conversation_id
                    }
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning("Rate limit hit during response generation")
                        return {
                            'error': 'The system is currently experiencing high demand. Please wait a moment and try again.',
                            'conversation_id': conversation_id
                        }
                    elif e.response.status_code >= 500:
                        logger.warning(f"Server error during response generation: {str(e)}")
                        return {
                            'error': 'The AI service is temporarily unavailable. Please try again in a few moments.',
                            'conversation_id': conversation_id
                        }
                    raise
                
                self.conversation_model.save_message(
                    conversation_id=conversation_id,
                    message=response,
                    role='bot'
                )
            
            return {
                'response': response,
                'conversation_id': conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            if isinstance(e, httpx.TimeoutException):
                return {
                    'error': 'The request is taking longer than expected. Please wait a moment and try again.',
                    'conversation_id': conversation_id
                }
            elif isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 429:
                    return {
                        'error': 'The system is currently experiencing high demand. Please wait a moment and try again.',
                        'conversation_id': conversation_id
                    }
                elif e.response.status_code >= 500:
                    return {
                        'error': 'The AI service is temporarily unavailable. Please try again in a few moments.',
                        'conversation_id': conversation_id
                    }
            return {
                'error': 'your daily token limit has been reached. please try again tomorrow or try with different api key.',
                'conversation_id': conversation_id
            }

    def get_recent_conversations(self, limit: int = 4) -> List[Dict[str, Any]]:
        """Get user's recent conversations"""
        try:
            return self.conversation_model.get_conversations(limit=limit)
        except Exception as e:
            logger.error(f"Error retrieving conversations: {str(e)}")
            raise

    def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Get messages for a specific conversation"""
        try:
            raw_messages = self.conversation_model.get_chat_history(conversation_id)
            return [
                {
                    'role': msg.get('role', 'user'),
                    'message': msg.get('message', ''),
                    'created_at': msg.get('created_at', datetime.now().isoformat())
                }
                for msg in raw_messages
            ]
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            raise

    def create_conversation(self, title: str) -> int:
        """Create a new conversation and clear user vector store context"""
        try:
            # Clear user vector store documents for a truly fresh chat
            self.vector_store.delete_user_documents()
            return self.conversation_model.create_conversation(title)
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise

    def delete_conversation(self, conversation_id: int) -> None:
        """Delete a conversation"""
        try:
            self.conversation_model.delete_conversation(conversation_id)
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            raise

    def clean_old_conversations(self, max_conversations: int = 50) -> None:
        """Clean up old conversations beyond the maximum limit"""
        try:
            conversations = self.conversation_model.get_conversations()
            if len(conversations) > max_conversations:
                for conv in conversations[max_conversations:]:
                    self.delete_conversation(conv['id'])
        except Exception as e:
            logger.error(f"Error cleaning old conversations: {str(e)}")
            raise

    def reset_all_conversations(self) -> None:
        """Delete all conversations for the current user"""
        try:
            conversations = self.conversation_model.get_conversations()
            for conv in conversations:
                self.delete_conversation(conv['id'])
        except Exception as e:
            logger.error(f"Error resetting conversations: {str(e)}")
            raise

    def get_token_usage(self) -> Dict[str, Any]:
        """Get current token usage information"""
        try:
            return self.chat_model.get_token_usage()
        except Exception as e:
            logger.error(f"Error getting token usage: {str(e)}")
            return {
                'daily_limit': '100,000',
                'used_tokens': '0',
                'requested_tokens': '0',
                'wait_time': None
            }