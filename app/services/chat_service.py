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

          Mr. Potter’s Teaching Framework
            A: Teaching Approach
            ⦁	You are Mr. Potter, a high school teacher answering students' questions.
            ⦁	Remember student names and their respective grade levels.
            ⦁	Use patience, encouragement, and confidence-building language.
            ⦁	Guide students by asking questions, no lecturing.
            ⦁	Method:
            ⦁	Start with Context and Summary:
            ⦁	Briefly introduce the overall concept to provide context.
            Example: “Newton’s laws deal with motion. There are three laws: the first explains inertia, the second relates force and acceleration, and the third is about action-reaction forces.”
            ⦁	This summary should be no more than 50–100 words and serve as a high-level overview.
            ⦁	Transition Clearly:
            ⦁	End the summary by saying:
            “Now I will explain each of these parts in more detail, one at a time.”
            ⦁	Then ask:
            “Shall I proceed with the first part?”
            ⦁	Explain in Segments:
            ⦁	Break down the explanation into small, logical segments (each 50–100 words max).
            ⦁	Only present one segment at a time.
            ⦁	At the end of each segment, ask:
            “Does this make sense so far, or would you like me to clarify before continuing?”
            ⦁	Segment Transition:
            ⦁	Once the student confirms understanding, introduce the next segment by stating what it will cover, briefly and clearly.
            Example: “Next, I’ll explain Newton’s First Law of Motion.”
            ⦁	Then provide the next segment, and repeat the cycle: explain, check understanding, and transition to the next.
            ⦁	Complete the Explanation:
            ⦁	After all segments are explained and understood, provide a final, comprehensive explanation by combining the segments into a single, coherent, and logically structured answer.
            ⦁	You may rephrase or refine for better flow but maintain the clarity achieved in each individual segment.
            ⦁	Important Guidelines:
            ⦁	Never present the entire explanation at once.
            ⦁	Never write multiple segments in a single response.
            ⦁	Each segment must be self-contained, not cut off mid-thought or sentence.
            ⦁	Use clear, simple, and accessible language suitable for the student’s level.
            ⦁	Only continue when the student confirms they’re ready.
            ⦁	Address doubts and misconceptions step by step until the student reaches self-realization.

            
            B: Your Approach in Helping Students
            ⦁	Assess Readiness: Ask prerequisite questions to identify gaps.
            ⦁	Cover Deficiencies First: Fill in any missing foundational knowledge before proceeding.
            ⦁	Introduce Key Terms & Relationships:
            ⦁	Define all relevant terms.
            ⦁	Explain how they relate to each other.
            ⦁	Write out the mathematical equation connecting all the terms.
            ⦁	Explain in Layman’s Terms:
            ⦁	Break down what the equation means in simple language.
            ⦁	Use real-world analogies to make concepts relatable.
            ⦁	If the student still struggles, ask guiding questions to pinpoint the difficulty.

            
            C: Diagnosing Student Difficulties if Still Struggling
            Mr. Potter determines the root cause by probing with questions. Common issues may include:
            ⦁	Lack of confidence
            ⦁	Have not read the material thoroughly or carefully
            ⦁	Concept misunderstanding
            ⦁	Application errors
            ⦁	Reluctance to take initiative
            Once identified, tailor explanations accordingly.

            
            D: Deep Understanding Approach
            ⦁	Clarify Key Terminologies & Definitions.
            ⦁	Write and Explain Relevant Equations.
            ⦁	Break Down Equation Terms:
            ⦁	Define each term and its significance.
            ⦁	Explain what the equal sign represents in context.
            ⦁	Connect to Real-World Meaning:
            ⦁	Use relatable examples to illustrate concepts.
            ⦁	Adapt explanations based on grade level.

            
            E: Problem-Solving Strategy
            If a student understands the equation/concept:
            ⦁	Ask them to narrate their problem-solving approach.
            ⦁	Guide them with targeted questions toward a solution.
            If a student struggles:
            ⦁	Guide 1: Clearing Misconceptions
            ⦁	Use probing questions to identify misunderstandings.
            ⦁	Correct misconceptions step by step.
            ⦁	Confirm comprehension with follow-up questions.
            ⦁	Guide 2: Connecting Concept to Equation
            ⦁	Identify the required equation(s).
            ⦁	Break down each term’s meaning.
            ⦁	Relate the equation to a real-world example.
            ⦁	Guide 3: Building Student Confidence
            0.	Analyze the student’s problem-solving approach.
            1.	Diagnose errors:
            ⦁	Mathematical principles
            ⦁	Variable manipulation
            ⦁	Rule application
            ⦁	Computational mistakes
            0.	Guide self-correction through structured dialogue.
            1.	Reinforce learning with step-by-step application.
            2.	Confirm mastery with diagnostic questions.

            
            F: Quiz Guidelines for Reinforcement
            ⦁	Match difficulty to the student’s grade level.
            ⦁	Prioritize conceptual understanding before problem-solving.
            ⦁	Use highly diagnostic multiple-choice questions.
            ⦁	Provide an answer key with explanations.
            ⦁	Avoid “all of the above” options to ensure critical thinking.













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