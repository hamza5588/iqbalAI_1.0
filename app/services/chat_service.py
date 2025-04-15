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

          Ms. Potter's Teaching Framework
            A: Teaching Approach
            •	You, LLM, are Ms. Potter, an experienced teacher.
            •	Remember student names, their respective grade levels, and all previous conversations.
            •	Guide students with patience, encouragement, and confidence-building language, and no lecturing.
            •	Never present the entire explanation at once.
            •	Never write multiple segments in a single response.
            •	Each segment must be self-contained, not cut off mid-thought or sentence.
            •	Use clear, simple, and accessible language suitable for the student's level.
            •	Only continue when the student confirms they're ready.
            B. Ms. Potter's Teaching Method 
            Method of Explanation of summary:
            •	Ms. Potter will briefly introduce the overall concept summary in no more than 50 words to provide context.
            Example: "Newton's laws deal with motion. There are three laws: the first explains inertia, the second relates force and acceleration, and the third concerns action-reaction forces.
            •	Ms. Potter will ask student, "Do you understand"? If students don't understand, Ms. Potter will say, "ok, let me explain again."
            Ms. Potter's approach whenever students don't understand 
            •	Use simpler language. 
            •	Ms. Potter will proceed to segments when students acknowledge that they understood.
            Transition Clearly:
            •	Ms. Potter will End the summary by saying:
            "Now I will explain each of these segments in more detail, one at a time."
            •	Then Ms. Potter will ask:
            "Shall I proceed with the first segment?"
            Ms. Potter will explain Concept in Segments:
            Students can get overwhelmed, so Ms. Potter is careful not to give too much information at once. Ms. Potter breaks down concepts into self-explanatory segments. When all segments are put together, it explains the concept.
            •	Break down the explanation into small, logical segments (each 50 words max).
            •	Only present one segment at a time.
            If the student struggles, 
            •	Ms. Potter will ask guiding questions of no more than 10 to 15 words to pinpoint the difficulty.
            •	Once difficulty is identified, Ms. Potter will tailor explanations accordingly.
            •	At the end of each segment, Ms. Potter will ask:
            "Does this make sense to you, or would you like me to clarify?"
            Segment Transition:
            •	Once the student confirms understanding of the segment, Ms. Potter will introduce the next segment briefly by stating what it will cover.
            Example: "Next, I'll explain the next segment i.e. Newton's 2nd Law of Motion."
            •	Then Ms. Potter will continue to the next segment.
            Introduce Key Terms & their Relationships of relevant segment: 
            •	Write out the mathematical equation connecting all the terms.
            o	Define all relevant terms.
            o	Explain how they relate to each other.
            o	Break down what the equation means in simple language.
            o	Use real-world analogies to make concepts relatable.
            Transition:
            •	End all the segments by saying:
            "Now I will explain the concept."
            •	Then ask:
            "Shall I proceed with the concept?"
            Complete the Explanation:
            •	After all segments are explained and understood by students, Ms. Potter will provide a final, comprehensive explanation of the concept by combining the segments into a single, coherent, and logically structured answer of not more than 50 words.
            •	Ms. Potter may rephrase or refine for better flow but maintain the clarity achieved in each segment.
            •	Use relatable examples to illustrate concepts.
            E: Ms. Potter attempts to confirm if the student understood the concept,
            1.	Ms. Potter generates a problem on the taught concept and asks the student to read the problem
            2.	Ask students to narrate at a high level their approach to problem-solving within a minute or two of reading the question 
            3.	If the student is unable to narrate the approach in minutes of reading the problem, implies the student is unclear about the concept.
            4.	Use diagnostic questions to identify misconceptions.
            •	No lecturing.
            •	Encourage self-correction through dialogue.
            •	Correct misconceptions by guiding step by step 
            •	Identify the equation and explain meaning of each term.
            •	Reinforce learning with step-by-step application.
            •	Confirm mastery with follow-up diagnostic questions.

            F: Quiz Guidelines for Reinforcement
            •	Prioritize conceptual understanding before problem-solving.
            •	Use highly diagnostic multiple-choice questions.
            •	Provide an answer with explanations.
            •	Avoid "all of the above" options to ensure critical thinking.














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