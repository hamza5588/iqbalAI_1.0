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

logger = logging.getLogger(__name__)

class ChatService:
    """Service class for handling chat-related business logic"""
    
    def __init__(self, user_id: int, api_key: str):
        self.user_id = user_id
        self.api_key = api_key
        self.chat_model = ChatModel(api_key=api_key, user_id=user_id)
        self.conversation_model = ConversationModel(user_id)
        self.vector_store = VectorStoreModel(user_id=user_id)
    
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
        
    def get_document_context(self, message: str) -> str:
        """Get relevant context from uploaded documents with page information"""
        try:
            if self.vector_store._vectorstore:
                # Check if the query is asking about a specific page
                page_match = re.search(r'page\s*(\d+)', message.lower())
                page_number = int(page_match.group(1)) if page_match else None
                
                relevant_docs = self.vector_store.search_similar(message, k=3)
                if relevant_docs:
                    context_parts = []
                    for doc in relevant_docs:


                        
                        # Get page number
                        page = doc.metadata.get('page', 1)
                        
                        # If user asked for specific page, only include that page's content
                        if page_number is not None and page != page_number:
                            continue
                            
                        context_parts.append(
                            f"Page {page}:\n{doc.page_content.strip()}"
                        )
                    
                    if context_parts:
                        return "Based on the uploaded documents:\n\n" + "\n\n".join(context_parts)
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
            # Create a new chat model instance for this interaction
            chat_model = self._create_new_chat_model()
            
            # Get document context
            document_context = self.get_document_context(message)
            
            # Base system prompt that enforces isolation and handling of document queries
            base_prompt = (
                """

            Mr. Potter's Teaching Philosophy and Methodology

            Section 1: Core Teaching Approach
            - Introduce yourself warmly as Mr. Potter, a patient and effective high school teacher
            - Build personal connections by remembering student names and their current understanding
            - Use supportive, encouraging language that inspires confidence
            - Structure responses clearly with bullet points for easy understanding
            - Guide students through concepts rather than lecturing
            - End interactions with summaries and open invitations for future questions

            Section 2: Understanding Student Difficulties
            Common challenges students face:
            - Not reading material thoroughly
            - Misunderstanding concepts
            - Lack of confidence
            - Reluctance to take initiative
            - Mistakes in concept application

            Mr. Potter's approach:
            - Identify the root cause through probing questions
            - Address misconceptions gradually
            - Guide students to self-realization
            - Remove doubts before introducing new concepts
            - Use questions to initiate dialogue and discover misunderstandings

            Section 3: Teaching Physics and STEM
            Key principles:
            - Emphasize precise terminology and definitions
            - Connect mathematical equations to real-world meaning
            - Break down complex concepts into elemental details
            - Use everyday examples to illustrate abstract concepts
            - Adapt explanations based on student grade level

            Teaching methodology:
            1. Identify key terminology
            2. Define terms mathematically
            3. Apply definitions to problems
            4. Interpret real-world meaning
            5. Address misconceptions
            6. Reinforce through examples

            Section 4: Problem-Solving Approach
            1. Ask students how they would approach the problem
            2. If they request direct solution:
            - Remind them that learning includes concept application
            - Encourage attempt even if uncertain
            - Guide through solution if needed

            3. If student attempts but struggles:
            - Identify misconceptions through probing questions
            - Analyze root cause of misunderstanding
            - Guide gradually to correct understanding
            - Confirm comprehension through targeted questions

            4. For complex problems:
            - Identify required equations
            - Break down elemental details
            - Connect to real-world phenomena
            - Adapt depth based on grade level

            Section 5: Building Student Confidence
            1. Analyze student's problem-solving approach
            2. Diagnose misconceptions using equations as reference
            3. Identify error types:
            - Mathematical principles
            - Variable manipulation
            - Rule application
            - Computational errors
            4. Guide self-correction through structured dialogue
            5. Reinforce learning with step-by-step application
            6. Confirm mastery through diagnostic quizzes

            Quiz Guidelines:
            - Create highly diagnostic multiple-choice questions
            - Include plausible, competitive alternate responses
            - Avoid "all of the above" options
            - Provide answer key with explanations
            - Match difficulty to grade level
            - Test conceptual understanding beyond facts 


	"""
            )
            
            if system_prompt:
                base_prompt = f"{base_prompt}\n\n{system_prompt}"
            
            if document_context:
                base_prompt = f"{base_prompt}\n\n{document_context}"
            
            # Handle new conversation
            if not conversation_id:
                conversation_id = self.conversation_model.create_conversation(
                    title=message[:50]
                )
                
                # Generate response with no history
                response = chat_model.generate_response(
                    input_text=message,
                    system_prompt=base_prompt,
                    chat_history=[]
                )
                
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
                
                response = chat_model.generate_response(
                    input_text=message,
                    system_prompt=base_prompt,
                    chat_history=formatted_history
                )
                
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
            raise

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
        """Create a new conversation"""
        try:
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