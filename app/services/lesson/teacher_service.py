"""
Teacher-focused lesson service for creating and managing lessons
"""
import os
import logging
import tempfile
from typing import Any, Dict, List, Optional

# Disable tqdm threading to prevent "cannot start new thread" errors
os.environ['TQDM_DISABLE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from docx import Document as DocxDocument
from docx.shared import Inches
from io import BytesIO
from datetime import datetime
import json

from .base_service import BaseLessonService
from .models import LessonResponse, LessonPlan
from .rag_service import RAGService

from app.models.models import LessonModel

logger = logging.getLogger(__name__)

# Set up detailed teacher service logging
teacher_logger = logging.getLogger('teacher_service')
teacher_logger.setLevel(logging.INFO)

# Create teacher.log file handler
if not os.path.exists('logs'):
    os.makedirs('logs')

teacher_handler = logging.FileHandler('logs/lesson.log')
teacher_handler.setLevel(logging.INFO)

# Create formatter for teacher logs
teacher_formatter = logging.Formatter(
    '%(asctime)s - TEACHER_SERVICE - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
teacher_handler.setFormatter(teacher_formatter)
teacher_logger.addHandler(teacher_handler)

from typing import Literal
from pydantic import BaseModel

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
# from langchain.memory import ConversationBufferMemory

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
import re
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from langchain_groq import ChatGroq

class lesson_response(BaseModel):
    complete_lesson: Literal["yes", "no"] = Field(
        ...,
        description="check if the lesson is generated or not if generated ('yes') or not ('no')."
    )

class InteractiveChatResponse(BaseModel):
    """Structured response for interactive chat"""
    ai_response: str = Field(..., description="The AI's response text")
    complete_lesson: Literal["yes", "no"] = Field(..., description="Whether the complete lesson has been generated ('yes') or still in draft/outline stage ('no')")

def check_lesson_response(text: str, groq_api_key: str):
    """Check if the AI response indicates a complete lesson has been generated"""
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.1
    )
    
    # Create a prompt to analyze if the response is a complete lesson or just an outline/draft
    analysis_prompt = f"""Analyze the following AI response and determine if it contains a COMPLETE LESSON or just an OUTLINE/DRAFT.

Complete Lesson indicators:
- Contains full lesson content with detailed explanations
- Includes actual lesson sections with comprehensive content
- Has detailed examples, code snippets, or explanations
- Ready to use for teaching (not just a structure/outline)

Outline/Draft indicators:
- Only shows structure (Learning Objectives, Main Topics list, etc.)
- Asks for confirmation before generating full lesson
- Contains phrases like "Does this outline work", "Should I generate", "Is this perfect now"
- Only shows headings/sections without full content

AI Response:
{text}

Determine if this is a complete lesson (yes) or still a draft/outline (no)."""

    llm_with_structured_output = llm.with_structured_output(lesson_response)
    return llm_with_structured_output.invoke(analysis_prompt)

class TeacherLessonService(BaseLessonService):
    """
    Teacher-focused lesson generation workflow:
    1. Teacher selects 'Generate Lesson' from the sidebar.
    2. Uploads a PDF file (e.g., textbook, handout).
    3. Teacher enters details about the lesson plan to be generated (title, objectives, focus areas, etc.).
    4. iqbalAI processes the file and user inputs, generates a structured lesson plan.
    5. Teacher can review, ask follow-up questions, edit/refine lesson parts.
    6. After final screening and edits, the final document is ready.
    7. User/teacher can download the final version.
    """
    
    # Class-level dictionary to persist chat histories across service instances
    # This ensures conversation history persists across HTTP requests
    _chat_histories = {}
    
    def __init__(self, groq_api_key: str):
        super().__init__(groq_api_key)
        self.rag_service = RAGService()
        self.lesson_vector_stores = {}  # Store vector DBs for each lesson
        teacher_logger.info("RAG service initialized")
        # Use class-level chat_histories to persist across instances
        teacher_logger.info("RAG service initialized with persistent memory")

    def process_file(self, file: FileStorage, lesson_details: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process an uploaded file and return structured lesson content with DOCX bytes.
        Accepts additional lesson details (title, prompt, focus areas, etc.) for teacher-focused workflow.
        """
        teacher_logger.info(f"=== TEACHER FILE PROCESSING STARTED ===")
        teacher_logger.info(f"File: {file.filename if file else 'None'}")
        teacher_logger.info(f"Lesson details: {json.dumps(lesson_details, indent=2) if lesson_details else 'None'}")
        
        temp_path = None
        try:
            if not file or not file.filename:
                teacher_logger.warning("No file provided")
                return {"error": "No file provided"}
            if not self.allowed_file(file.filename):
                teacher_logger.warning(f"Unsupported file type: {file.filename}")
                return {"error": "File type not supported. Please upload PDF, DOC, DOCX, or TXT files."}
            
            teacher_logger.info(f"File validation passed: {file.filename}")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}") as temp_file:
                temp_path = temp_file.name
                file.save(temp_path)
            
            teacher_logger.info(f"File saved to temporary path: {temp_path}")
            
            documents = self._load_document(temp_path, file.filename)
            if not documents:
                teacher_logger.error("Could not extract content from the file")
                return {"error": "Could not extract content from the file"}
            
            teacher_logger.info(f"Document loaded successfully: {len(documents)} pages/sections")
            
            full_text = "\n".join([doc.page_content for doc in documents])
            if not full_text.strip():
                teacher_logger.error("No readable content found in the file")
                return {"error": "No readable content found in the file"}
            
            teacher_logger.info(f"Text extracted successfully: {len(full_text)} characters")
            
            # Process document with RAG service
            rag_result = self.rag_service.process_document(documents, file.filename)
            if 'error' in rag_result:
                teacher_logger.error(f"RAG processing failed: {rag_result['error']}")
                return rag_result
            
            # Store the original document's RAG service immediately after processing
            if rag_result['use_rag']:
                self._store_original_document_rag(file.filename)
                teacher_logger.info("Original document RAG service stored for AI review")
            
            # Check if RAG should be used
            if rag_result['use_rag']:
                teacher_logger.info("Using RAG for large document processing")
                
                # Get user prompt
                user_prompt = lesson_details.get('lesson_prompt', '') if lesson_details else ''
                
                # Retrieve relevant chunks
                relevant_chunks = self.rag_service.retrieve_relevant_chunks(user_prompt, k=5)
                if not relevant_chunks:
                    teacher_logger.warning("No relevant chunks found, using first few chunks")
                    relevant_chunks = self.rag_service.documents[:3]
                
                # Create RAG prompt
                rag_prompt = self.rag_service.create_rag_prompt(user_prompt, relevant_chunks, lesson_details)
                
                # Generate lesson using RAG prompt
                teacher_logger.info("Starting AI lesson generation with RAG")
                lesson_response = self._llm_responce(rag_prompt, lesson_details)
            else:
                teacher_logger.info("Document is small, using direct processing")
                
                # Extract specific sections based on prompt if specified
                if lesson_details and lesson_details.get('lesson_prompt'):
                    teacher_logger.info(f"Extracting sections based on prompt: {lesson_details['lesson_prompt']}")
                    extracted_text = self._extract_sections_from_prompt(full_text, lesson_details['lesson_prompt'])
                    if extracted_text:
                        full_text = extracted_text
                        teacher_logger.info(f"Specific sections extracted: {len(extracted_text)} characters")
                        logger.info(f"Extracted specific sections based on prompt: {lesson_details['lesson_prompt']}")
                    else:
                        teacher_logger.info("No specific sections found, using full text")
                
                # Generate structured lesson
                teacher_logger.info("Starting AI lesson generation")
                lesson_response = self._generate_structured_lesson(full_text, lesson_details)
            
            # Check if lesson generation was successful
            if lesson_response.startswith("Error generating lesson:"):
                teacher_logger.error(f"Lesson generation failed: {lesson_response}")
                return {"error": lesson_response}
            
            teacher_logger.info("Lesson generation completed successfully")
            teacher_logger.info(f"Generated lesson response length: {len(lesson_response)} characters")

            # Generate DOCX from the lesson response
            if lesson_response and not lesson_response.startswith("Error"):
                teacher_logger.info("Generating DOCX document")
                docx_bytes = self._create_docx_from_text(lesson_response, lesson_details)
                base_name = os.path.splitext(file.filename)[0]
                filename = f"lesson_{base_name}.docx"
                teacher_logger.info(f"DOCX generated: {filename}, size: {len(docx_bytes)} bytes")
            else:
                teacher_logger.info("Skipping DOCX generation due to error")
                docx_bytes = None
                filename = None
            
            teacher_logger.info("=== TEACHER FILE PROCESSING COMPLETED ===")
            
            return {
                "lesson": lesson_response,
                "docx_bytes": docx_bytes,
                "filename": filename
            }
        except Exception as e:
            teacher_logger.error(f"File processing failed: {str(e)}")
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return {
                "error": "Failed to process file",
                "details": str(e)
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    teacher_logger.info(f"Temporary file cleaned up: {temp_path}")
                except Exception as e:
                    teacher_logger.warning(f"Could not remove temporary file {temp_path}: {str(e)}")
                    logger.warning(f"Could not remove temporary file {temp_path}: {str(e)}")

    
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get or create chat history for a session"""
        # Use class-level dictionary to persist history across service instances
        if session_id not in TeacherLessonService._chat_histories:
            TeacherLessonService._chat_histories[session_id] = InMemoryChatMessageHistory()
            teacher_logger.info(f"Created new chat history for session: {session_id}")
        else:
            history = TeacherLessonService._chat_histories[session_id]
            message_count = len(history.messages) if hasattr(history, 'messages') else 0
            teacher_logger.info(f"Retrieved existing chat history for session: {session_id} ({message_count} messages)")
        return TeacherLessonService._chat_histories[session_id]

    def format_context(self, relevant_chunks: List[Document]) -> str:
        """Format context and escape curly braces to prevent LangChain template errors"""
        rag_context = "\n\n".join([doc.page_content for doc in relevant_chunks])
        # Escape curly braces in context content (this is a value, not a template string)
        # All braces in the context value should be escaped since it will be inserted into {context}
        escaped_context = rag_context.replace("{", "{{").replace("}", "}}")
        return escaped_context
    
    def _format_context_for_system_prompt(self, relevant_chunks: List[Document]) -> str:
        """Format context for system prompt without escaping (will be escaped later)"""
        return "\n\n".join([doc.page_content for doc in relevant_chunks])

    def interactive_chat(
    self, 
    lesson_id: int, 
    user_query: str, 
    session_id: str = None, 
    subject: str = None, 
    grade_level: str = None, 
    focus_area: str = None, 
    document_uploaded: bool = False, 
    document_filename: str = None
) -> InteractiveChatResponse:
        """Interactive chat with Prof. Potter for lesson creation - NO CHAINS VERSION"""
        
        teacher_logger.info("=== INTERACTIVE CHAT STARTED (NO CHAINS) ===")
        
        # Use lesson_id as session_id
        if not session_id:
            session_id = f"lesson_{lesson_id}"
        
        try:
            # Step 1: Load vector DB
            vector_db = FAISS.load_local(
                "vector_store.faiss", 
                self.rag_service.embeddings, 
                allow_dangerous_deserialization=True
            )
            retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            teacher_logger.info("Vector DB loaded successfully")
            
            # Step 2: Handle uploaded document content
            uploaded_doc_content = ""
            if document_uploaded and document_filename:
                try:
                    uploaded_doc_content = f"\n\n### Uploaded Document: {document_filename}\n[Document content]"
                    teacher_logger.info(f"Retrieved uploaded document: {document_filename}")
                except Exception as e:
                    teacher_logger.warning(f"Could not retrieve uploaded document: {str(e)}")
            
            # Step 3: Store form data
            form_context = {
                'subject': subject or focus_area,
                'grade_level': grade_level,
                'document_uploaded': document_uploaded,
                'document_filename': document_filename,
                'uploaded_content': uploaded_doc_content
            }
            
            # Step 4: Build system prompt
            base_system_prompt = self._get_system_prompt(form_context)
            teacher_logger.info("System prompt built")
            
            # Step 5: Get chat history
            chat_history = self.get_session_history(session_id)
            is_first_message = len(chat_history.messages) == 0 if hasattr(chat_history, 'messages') else True
            teacher_logger.info(f"Chat history retrieved: {len(chat_history.messages) if hasattr(chat_history, 'messages') else 0} messages")
            
            # Step 6: Enhance query if first message with document
            enhanced_query = user_query
            if is_first_message and document_uploaded:
                try:
                    overview_query = "What is this document about? Provide a brief summary."
                    overview_docs = retriever.invoke(overview_query)
                    if overview_docs:
                        doc_summary = "\n".join([doc.page_content[:200] for doc in overview_docs[:3]])
                        enhanced_query = f"{user_query}\n\n[Document Context: {doc_summary}...]"
                        teacher_logger.info("Query enhanced with document context")
                except Exception as e:
                    teacher_logger.warning(f"Could not retrieve document overview: {str(e)}")
            
            # === MANUAL EXECUTION - NO LANGCHAIN CHAINS ===
            teacher_logger.info("Starting manual chain execution (no threading)")
            
            # Step 7: Retrieve context from vector store
            docs = retriever.invoke(enhanced_query)
            context = self.format_context(docs)
            teacher_logger.info(f"Retrieved {len(docs)} documents from vector store")
            
            # Step 8: Build messages array manually
            messages = []
            
            # Add system message with context
            system_content = f"{base_system_prompt}\n\n### Knowledge Base Context:\n{context}{uploaded_doc_content}"
            messages.append({"role": "system", "content": system_content})
            
            # Add chat history messages
            if hasattr(chat_history, 'messages'):
                for msg in chat_history.messages:
                    if hasattr(msg, 'type'):
                        role = "user" if msg.type == "human" else "assistant"
                        content = msg.content if hasattr(msg, 'content') else str(msg)
                        messages.append({"role": role, "content": content})
            
            # Add current user query
            messages.append({"role": "user", "content": enhanced_query})
            
            teacher_logger.info(f"Built message array with {len(messages)} messages")
            
            # Step 9: Call LLM directly (no chain, no threading)
            teacher_logger.info("Calling LLM directly...")
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            teacher_logger.info(f"LLM response received: {len(response_text)} characters")
            
            # Step 10: Update chat history manually
            from langchain_core.messages import HumanMessage, AIMessage
            chat_history.add_message(HumanMessage(content=enhanced_query))
            chat_history.add_message(AIMessage(content=response_text))
            teacher_logger.info(f"Chat history updated for session: {session_id}")
            
        except Exception as e:
            teacher_logger.error(f"Interactive chat error: {str(e)}", exc_info=True)
            raise
        
        # Step 11: Check if complete lesson generated
        try:
            lesson_check = check_lesson_response(response_text, self.api_key)
            complete_lesson_status = lesson_check.complete_lesson
            teacher_logger.info(f"Lesson completion check: {complete_lesson_status}")
        except Exception as e:
            teacher_logger.warning(f"Error checking lesson completion: {str(e)}")
            complete_lesson_status = "no"
        
        # Step 12: Force cleanup
        import gc
        gc.collect()
        
        teacher_logger.info("=== INTERACTIVE CHAT COMPLETED ===")
        
        return InteractiveChatResponse(
            ai_response=response_text,
            complete_lesson=complete_lesson_status
        )
    # def interactive_chat(
    #     self, 
    #     lesson_id: int, 
    #     user_query: str, 
    #     session_id: str = None,
    #     subject: str = None,
    #     grade_level: str = None,
    #     focus_area: str = None,
    #     document_uploaded: bool = False,
    #     document_filename: str = None
    # ) -> InteractiveChatResponse:
    #     """Interactive chat with Prof. Potter for lesson creation"""
        
    #     # Use lesson_id as session_id to maintain context per lesson
    #     if not session_id:
    #         session_id = f"lesson_{lesson_id}"
        
    #     # Step 1: Load vector DB
    #     vector_db = FAISS.load_local(
    #         "vector_store.faiss",
    #         self.rag_service.embeddings,
    #         allow_dangerous_deserialization=True
    #     )
    #     retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        
    #     # Step 2: Handle uploaded document content
    #     uploaded_doc_content = ""
    #     if document_uploaded and document_filename:
    #         try:
    #             # TODO: Implement actual document retrieval from your storage
    #             # Example: uploaded_doc_content = self.get_uploaded_document(lesson_id, document_filename)
    #             uploaded_doc_content = f"\n\n### Uploaded Document: {document_filename}\n[Document content should be retrieved and inserted here]"
    #             teacher_logger.info(f"Retrieved uploaded document: {document_filename}")
    #         except Exception as e:
    #             teacher_logger.warning(f"Could not retrieve uploaded document: {str(e)}")
        
    #     # Step 3: Store form data in session context
    #     form_context = {
    #         'subject': subject or focus_area,
    #         'grade_level': grade_level,
    #         'document_uploaded': document_uploaded,
    #         'document_filename': document_filename,
    #         'uploaded_content': uploaded_doc_content  # Add actual content
    #     }
        
    #     # Step 4: Retriever is now used directly in build_chain_input to avoid parallel execution
        
    #     # Step 5: Build system prompt with form context (but NOT with RAG context yet)
    #     # RAG context will be dynamically added per query via {context} placeholder
    #     base_system_prompt = self._get_system_prompt(form_context)
        
    #     # Escape curly braces to prevent template variable errors
    #     escaped_system_prompt = base_system_prompt.replace("{", "{{").replace("}", "}}")
        
    #     # Build prompt template
    #     prompt = ChatPromptTemplate.from_messages([
    #         ("system", escaped_system_prompt + "\n\n### Knowledge Base Context:\n{context}" + uploaded_doc_content),
    #         MessagesPlaceholder(variable_name="chat_history"),
    #         ("human", "{user_query}")
    #     ])

    #     # Step 6: Build chain - restructured to avoid parallel execution that causes thread exhaustion
    #     def extract_query_content(x):
    #         """Extract user query from input - handles both string and message objects"""
    #         user_input = x.get("user_query", "")
    #         if hasattr(user_input, 'content'):
    #             return user_input.content
    #         return str(user_input)
        
    #     # def build_chain_input(x):
    #     #     """Build chain input sequentially to avoid parallel execution"""
    #     #     query = extract_query_content(x)
    #     #     # Retrieve context synchronously (not in parallel)
    #     #     context = self.format_context(retriever.invoke(query))
    #     #     chat_history = x.get("chat_history", [])
    #     #     return {
    #     #         "context": context,
    #     #         "user_query": query,
    #     #         "chat_history": chat_history
    #     #     }
    #     def build_chain_input(x):
    #         query = extract_query_content(x)
    #         docs = retriever.invoke(query)  # Sequential, not parallel
    #         return {
    #             "context": self.format_context(docs),
    #             "user_query": query,
    #             "chat_history": x.get("chat_history", [])
    #         }
        
        
    #     chain = (
    #         RunnableLambda(build_chain_input)
    #         | prompt 
    #         | self.llm
    #     )

    #     # Step 7: Wrap with message history
    #     conversational_chain = RunnableWithMessageHistory(
    #         chain,
    #         self.get_session_history,
    #         input_messages_key="user_query",
    #         history_messages_key="chat_history"
    #     )
        

    #     # Step 8: For initial message, retrieve document overview to inform the greeting
    #     # Check if this is the first message (no chat history)
    #     chat_history = self.get_session_history(session_id)
    #     is_first_message = len(chat_history.messages) == 0 if hasattr(chat_history, 'messages') else True
        
    #     # If first message and document is uploaded, enhance the query with document overview
    #     if is_first_message and document_uploaded:
    #         # Retrieve document overview to understand what it's about
    #         try:
    #             overview_query = "What is this document about? Provide a brief summary of the main topics, themes, and content."
    #             overview_docs = retriever.invoke(overview_query)
    #             if overview_docs:
    #                 # Extract key topics from the document
    #                 doc_summary = "\n".join([doc.page_content[:200] for doc in overview_docs[:3]])  # First 200 chars of top 3 chunks
    #                 # Enhance user query to include document context for better initial response
    #                 enhanced_query = f"{user_query}\n\n[Document Context: The uploaded document covers: {doc_summary}...]"
    #             else:
    #                 enhanced_query = user_query
    #         except Exception as e:
    #             teacher_logger.warning(f"Could not retrieve document overview: {str(e)}")
    #             enhanced_query = user_query
    #     else:
    #         enhanced_query = user_query
        
    #     # Step 8: Invoke with configuration to prevent thread exhaustion
    #     # Use simple config to avoid parallel execution issues

    #     run_config = RunnableConfig(
    #         configurable={"session_id": session_id},
    #         max_concurrency=1,
    #         recursion_limit=3
    #     )
        
    #     response_message = conversational_chain.invoke(
    #         {"user_query": enhanced_query},
    #         config=run_config
    #     )
        # run_config = RunnableConfig(
        #     configurable={"session_id": session_id}
        # )
        # response_message = conversational_chain.invoke(
        #     {"user_query": enhanced_query},
        #     config=run_config
        # )
        
        response_text = response_message.content if hasattr(response_message, 'content') else str(response_message)
        
        # Step 9: Check if complete lesson has been generated
        try:
            lesson_check = check_lesson_response(response_text, self.api_key)
            complete_lesson_status = lesson_check.complete_lesson
            teacher_logger.info(f"Lesson completion check: {complete_lesson_status}")
        except Exception as e:
            teacher_logger.warning(f"Error checking lesson completion status: {str(e)}")
            complete_lesson_status = "no"
        
        return InteractiveChatResponse(
            ai_response=response_text,
            complete_lesson=complete_lesson_status
        )
    # def interactive_chat(
    #     self, 
    #     lesson_id: int, 
    #     user_query: str, 
    #     session_id: str = None,
    #     subject: str = None,
    #     grade_level: str = None,
    #     focus_area: str = None,
    #     document_uploaded: bool = False,
    #     document_filename: str = None
    # ) -> InteractiveChatResponse:
    #     """Interactive chat with Prof. Potter for lesson creation"""
        
    #     # Use lesson_id as session_id to maintain context per lesson
    #     if not session_id:
    #         session_id = f"lesson_{lesson_id}"
        
    #     # Store form data in session context for use in prompts
    #     form_context = {
    #         'subject': subject or focus_area,  # Use focus_area as subject if subject not provided
    #         'grade_level': grade_level,
    #         'document_uploaded': document_uploaded,
    #         'document_filename': document_filename
    #     }
        
    #     # Step 1: Load vector DB
    #     vector_db = FAISS.load_local(
    #         "vector_store.faiss",
    #         self.rag_service.embeddings,
    #         allow_dangerous_deserialization=True
    #     )
    #     retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        
    #     # Step 2: Create retriever runnable that extracts user_query from dict
    #     # Handle both string and message object inputs
    #     def get_query_for_retrieval(x):
    #         """Extract user query for retrieval - handles both string and message objects"""
    #         user_input = x.get("user_query", "")
    #         if hasattr(user_input, 'content'):
    #             return user_input.content
    #         return str(user_input)
        
    #     retriever_runnable = RunnableLambda(
    #         lambda x: self.format_context(
    #             retriever.invoke(get_query_for_retrieval(x))  # Extract query content for retrieval
    #         )
    #     )
        
    #     # Step 3: Build prompt (include context in the system prompt)
    #     # Get initial context for system prompt (returns list of Document objects)
    #     initial_context_docs = retriever.invoke(user_query)
    #     # Format context to string for system prompt (don't escape yet, will escape in system_prompt)
    #     initial_context_str = self._format_context_for_system_prompt(initial_context_docs)
    #     # Pass form context to system prompt
    #     system_prompt = self._get_system_prompt(initial_context_str, form_context)
    #     # Escape curly braces in system_prompt content to prevent template variable errors
    #     # This escapes any braces in the context content like {'producer'} that could be misinterpreted
    #     # The {context} variable is added after escaping, so it remains a valid template variable
    #     escaped_system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")
    #     # Build prompt template with:
    #     # - System prompt with context
    #     # - MessagesPlaceholder for chat_history (automatically populated by RunnableWithMessageHistory)
    #     # - Current user query
    #     prompt = ChatPromptTemplate.from_messages([
    #         ("system", escaped_system_prompt + "\n\nContext from knowledge base:\n{context}"),
    #         MessagesPlaceholder(variable_name="chat_history"),  # Will contain all previous Q&A pairs
    #         ("human", "{user_query}")  # Current user query
    #     ])

    #     # Step 4: Build chain
    #     # RunnableWithMessageHistory will automatically:
    #     # 1. Convert user_query string to HumanMessage and add to history
    #     # 2. Inject full history into chat_history for MessagesPlaceholder
    #     # 3. Pass the original user_query string to the chain for template
    #     def extract_query_content(x):
    #         """Extract user query from input - handles both string and message objects"""
    #         user_input = x.get("user_query", "")
    #         if hasattr(user_input, 'content'):
    #             return user_input.content
    #         return str(user_input)
        
    #     chain = (
    #         {
    #             "context": retriever_runnable,  # Retrieves context based on user_query
    #             "user_query": extract_query_content,  # Extract query content (handles message or string)
    #             "chat_history": lambda x: x.get("chat_history", [])  # Pass chat_history (populated by RunnableWithMessageHistory)
    #         }
    #         | prompt 
    #         | self.llm
    #     )

    #     # Step 5: Wrap with message history
    #     # RunnableWithMessageHistory automatically:
    #     # - Converts user_query string to HumanMessage
    #     # - Adds it to session history
    #     # - Injects full history into chat_history key before passing to chain
    #     conversational_chain = RunnableWithMessageHistory(
    #         chain,
    #         self.get_session_history,
    #         input_messages_key="user_query",  # Key in input dict that contains the message
    #         history_messages_key="chat_history"  # Key in chain input where history will be injected
    #     )

    #     # Step 6: Invoke
    #     # Pass user_query as string - RunnableWithMessageHistory will handle conversion and history
    #     response_message = conversational_chain.invoke(
    #         {"user_query": user_query},  # Pass as string, will be converted to HumanMessage
    #         config={"configurable": {"session_id": session_id}}
    #     )
        
    #     response_text = response_message.content if hasattr(response_message, 'content') else str(response_message)
        
    #     # Step 7: Check if complete lesson has been generated
    #     # Use structured output to determine if the response indicates a complete lesson
    #     try:
    #         lesson_check = check_lesson_response(response_text, self.api_key)
            
    #         complete_lesson_status = lesson_check.complete_lesson
    #         teacher_logger.info(f"Lesson completion check: {complete_lesson_status}")
    #     except Exception as e:
    #         teacher_logger.warning(f"Error checking lesson completion status: {str(e)}")
    #         # Default to "no" if check fails (assume it's still in draft/outline stage)
    #         complete_lesson_status = "no"
        
    #     # Return structured response
    #     return InteractiveChatResponse(
    #         ai_response=response_text,
    #         complete_lesson=complete_lesson_status
    #     )
            
        # except Exception as e:
        #     teacher_logger.error(f"Error in conversational chain: {e}")
        #     # Return fallback response
        #     return InteractiveChatResponse(
        #         ai_response=f"I encountered an error. Let's start fresh. Could you please tell me what lesson you'd like to create?",
        #         state="start",
        #         should_generate_lesson=False
        #     )
    
    # def _parse_response(self, response_text: str, current_state: str) -> InteractiveChatResponse:
    #     """Parse LLM response and extract structured data"""
        
    #     # Try to extract JSON if present
    #     json_match = re.search(r'\{[^}]*"ai_response"[^}]*\}', response_text, re.DOTALL)
    #     if json_match:
    #         try:
    #             data = json.loads(json_match.group())
    #             return InteractiveChatResponse(**data)
    #         except:
    #             pass
        
    #     # Determine next state based on content and current state
    #     next_state = self._determine_next_state(response_text, current_state)
        
    #     # Check if lesson should be generated
    #     should_generate = (
    #         next_state == "completed" or
    #         "here is the complete lesson" in response_text.lower() or
    #         "here's the complete lesson" in response_text.lower()
    #     )
        
    #     return InteractiveChatResponse(
    #         ai_response=response_text.strip(),
    #         state=next_state,
    #         should_generate_lesson=should_generate
    #     )
    
    # def _determine_next_state(self, response_text: str, current_state: str) -> str:
    #     """Determine next state based on response content"""
    #     response_lower = response_text.lower()
        
    #     if current_state == "start":
    #         if "have you uploaded" in response_lower or "upload" in response_lower:
    #             return "gathering_requirements"
    #         return "gathering_requirements"
        
    #     elif current_state == "gathering_requirements":
    #         if "outline" in response_lower or "structure" in response_lower:
    #             return "awaiting_outline_approval"
    #         return "gathering_requirements"
        
    #     elif current_state == "awaiting_outline_approval":
    #         if "generate the complete lesson" in response_lower or "full lesson" in response_lower:
    #             return "ready_to_generate"
    #         return "refining_outline"
        
    #     elif current_state == "refining_outline":
    #         if "ready to generate" in response_lower or "generate" in response_lower:
    #             return "ready_to_generate"
    #         return "refining_outline"
        
    #     elif current_state == "ready_to_generate":
    #         return "completed"
        
    #     elif current_state == "completed":
    #         return "completed"
        
    #     return current_state
    

    def _get_system_prompt(self, rag_context: str = "", form_context: dict = None) -> str:
        """Generate a single unified system prompt for Prof. Potter."""
        
        if form_context is None:
            form_context = {}
        
        # Note: rag_context is typically empty here and filled by {context} placeholder
        # Only include it if explicitly provided (rare case)
        context_section = f"\n\n### RELEVANT CONTEXT FROM KNOWLEDGE BASE:\n{rag_context}\n" if rag_context else ""
        
        # Build form context section
        form_context_section = ""
        # Only show subject if it's not "Other" or empty
        subject = form_context.get('subject', '')
        if subject and subject.lower() not in ['other', 'none', '']:
            form_context_section += f"\n**Subject/Topic:** {subject}\n"
        if form_context.get('grade_level'):
            form_context_section += f"**Grade Level:** {form_context['grade_level']}\n"
        # Document is already uploaded - don't ask about it, just note it's available
        if form_context.get('document_uploaded'):
            form_context_section += f"**Document:** {form_context.get('document_filename', 'file')} (already uploaded and processed)\n"
            form_context_section += "**IMPORTANT:** The document has been uploaded and processed. You have access to its full content through the knowledge base context. Use this content to understand what the document is about and help create lessons from it.\n"
        
        if form_context_section:
            form_context_section = f"\n\n📋 LESSON FORM INFORMATION:\n{form_context_section}\n"

        unified_prompt = f"""
              # Prof. Potter - Lesson Planning Assistant

**Role**: You are Prof. Potter, an expert education assistant helping Faculty/Teachers prepare lesson plans from uploaded documents.

---

## CRITICAL INSTRUCTIONS (Must Always Follow)

**CRITICAL INSTRUCTION 1: Document-Based Responses Only**
* Answer questions ONLY from uploaded document content (when provided)
* If answer not in document, immediately state: "I cannot find this information in the uploaded document. How would you like me to address this?"
* The knowledge base context contains the uploaded document content - use it to understand what the document is about
* For the FIRST message when document is uploaded: Use the knowledge base context to understand the document's main topics and themes, then greet the Faculty by mentioning what the document is about (e.g., "I've reviewed your document about [topics from context]")
* Never fabricate, assume, or infer information not explicitly present in the document
* When uncertain if information is in document, state uncertainty and ask Faculty to confirm
* NEVER ask about uploading documents if the document is already uploaded - you already have access to it through the knowledge base context

**CRITICAL INSTRUCTION 1.5: Wait for Confirmation Before Proceeding**
* After asking ANY question (about prerequisites, topics, confirmation, etc.), you MUST wait for Faculty's response
* Do NOT proceed to explain lesson components, provide content, or move forward until Faculty explicitly confirms
* If you ask "Would you like me to include prerequisites?" - WAIT for yes/no answer before proceeding
* If you ask "Is that correct?" - WAIT for confirmation before explaining anything
* Only provide explanations, lesson content, or proceed to next steps AFTER receiving Faculty's explicit confirmation
* This applies to ALL questions - always wait for the answer before continuing

**CRITICAL INSTRUCTION 2: Ambiguity Resolution Process**
* When a question can be interpreted in multiple ways, STOP immediately
* Present possible interpretations: "I can interpret your question in these ways: [list 2-3 interpretations]. Which one matches your intent?"
* After Faculty responds, reaffirm understanding: "To confirm, you're asking about [restate their interpretation]. Is this correct?"
* Do NOT proceed to answer until you receive explicit confirmation from Faculty
* If still unclear after confirmation, ask additional clarifying questions

**CRITICAL INSTRUCTION 3: Dual-Verification Before Response**
* For every Faculty question, follow this exact process:
  - Step 1: Reread the original question the Faculty asked
  - Step 2: Reread what Faculty said during any clarification exchanges
  - Step 3: Generate two independent answers internally
  - Step 4: Compare both answers for 98% or better agreement
  - Step 5: Only when answers match ≥98%, provide the response to Faculty
* If internal answers don't match ≥98%, this signals ambiguity - return to CRITICAL INSTRUCTION 2
* This verification happens silently - Faculty does not see this process

---

## Important Guidelines

**Important Guideline 1: Communication Style**
* Greeting (first interaction only): 
  - If document is uploaded: Use the knowledge base context to understand what the document is about, then greet with: "Hello, I'm Prof. Potter, here to help you prepare your lesson plan. I've reviewed your uploaded document about [briefly mention main topics/themes from the document]. How would you like me to help you create a lesson from this content?"
  - If no document: "Hello, I'm Prof. Potter, here to help you prepare your lesson plan. Could you please provide me with the document content or topic you'd like to create a lesson about?"
  - NEVER ask about uploading documents if document_uploaded is True - the document is already uploaded
  - NEVER mention "Other" as a subject - if subject is "Other" or empty, don't mention it
* All responses: Concise, clear, confidence-building, self-explanatory (≤150 words per response)
* Exception: Final complete lesson plan may exceed 150 words
* Use confidence-building language throughout: "Let's work together", "This will help your students", "Great question"

**Important Guideline 2: Prerequisite Identification**
* After understanding Faculty's lesson topic, identify prerequisites students need
* Clearly state: "For students to understand [topic], they need to know [prerequisites]. Would you like me to include prerequisite material in the lesson plan?"
* **CRITICAL: WAIT for Faculty's response before proceeding** - Do NOT start explaining lesson components or content until Faculty confirms
* After asking about prerequisites, STOP and wait for Faculty's answer (yes/no/their preference)
* Only after Faculty responds about prerequisites, then proceed to the next step
* If Faculty agrees, review prior sections in uploaded document for prerequisite content
* If prerequisites not in document, inform Faculty and ask: "How would you like me to address prerequisites not covered in this document?"
* Always build lesson logically from prerequisites to main topic
* **NEVER proceed to explain lesson content without explicit Faculty confirmation to continue**

**Important Guideline 3: Logical Lesson Structure**
* **CRITICAL: Only start explaining lesson content AFTER Faculty explicitly confirms they want to proceed**
* Before explaining any lesson component, ask: "Would you like me to start explaining [component/topic] now?" and WAIT for confirmation
* Start from basic explanations and build progressively
* Each explanation must build on the previous one
* Use sequential, methodical progression with no logical gaps
* Break complex topics into "simpler short lectures"
* Each "simpler short lecture" must be self-explanatory and ≤150 words
* Ensure no disjointed statements - every paragraph connects logically to the next
* The complete lesson = all "simpler short lectures" combined sequentially
* **After asking a question, ALWAYS wait for Faculty's response before providing explanations or proceeding**

**Important Guideline 4: Progress Communication**
* Periodically inform Faculty of your location in lesson development: "So far, I've covered [topics completed]. Next, I'll address [upcoming topics]."
* Welcome Faculty suggestions at any point: "Do you have suggestions for how to present this?"
* Analyze suggestions honestly and respectfully
* Incorporate suggestions with merit into the lesson plan
* If you disagree with a suggestion, explain why respectfully: "I understand your suggestion. However, [reason]. Would you like me to proceed differently?"

---

## Standard Practices

**Standard Practice 1: Equation-Based Teaching Protocol**

When the lesson involves equations, follow these steps. Do NOT reveal the complete equation until Step 5:

**Step 1: Individual Term Explanation**
* Explain each term in the equation one at a time
* Define what each term means physically, conceptually, or in real-world context
* Do not show mathematical relationships or operations yet

**Step 2: Mathematical Operations on Terms**
* For each term with a mathematical operator, explain in exact order:
  - First: What the individual term means by itself
  - Second: What the mathematical operator does to that term
  - Third: What the combination produces physically or conceptually

**Step 3: Check for Understanding**
* After explaining each term or operation, ask Faculty: "Does this explanation work for your students at [grade level]?"
* Provide additional clarification if Faculty requests it
* Do not proceed to next term until Faculty confirms understanding or requests to move forward

**Step 4: Complete All Terms**
* Repeat Steps 1-3 for every single term in the equation
* Ensure each term and its operations are explained before moving to next term
* Maintain the ≤150 word limit for each term explanation

**Step 5: Synthesize the Complete Equation**
* NOW reveal the complete equation for the first time
* Connect all previously explained terms together
* Explain the significance of each term's position in the equation
* Describe how the equation behaves in real-world scenarios with concrete examples
* This synthesis may exceed 150 words

**Step 6: Final Confirmation**
* Ask Faculty: "Does this lesson plan address your teaching objectives? Would you like me to adjust anything?"

**Standard Practice 2: Vocabulary Appropriateness**
* Adjust vocabulary to match students' grade level
* When using complex terms, immediately offer simpler alternatives: "In other words..." or "A simpler way to say this is..."
* Ask Faculty: "Is this vocabulary appropriate for your students, or should I simplify further?"

**Standard Practice 3: Hallucination Prevention**
* Generate responses internally before presenting
* Remove any repetitive sentences within response (unless repetition serves to reinforce learning)
* Verify response accuracy by comparing with document content one final time before presenting

**Standard Practice 4: Faculty Encouragement**
* When Faculty introduces creative teaching approaches, acknowledge them: "That's an innovative approach!"
* When Faculty offers new perspectives, commend them: "I hadn't considered that perspective - thank you!"
* Encourage continued creativity: "Your creative input makes this lesson plan stronger."

---

## Quality Assurance Checklist

Before providing any response to Faculty, verify:
* [ ] Did I check the uploaded document for this information?
* [ ] If information not in document, did I inform Faculty and ask how to proceed?
* [ ] Was the Faculty's question ambiguous? Did I resolve ambiguity?
* [ ] Did I complete dual-verification (98%+ agreement)?
* [ ] Is my response ≤150 words (except final lesson plan)?
* [ ] Is my response self-explanatory and confidence-building?
* [ ] Does my response build logically on previous explanations?
* [ ] **If I asked a question, did I wait for Faculty's response before proceeding?**
* [ ] **Am I explaining lesson content only AFTER receiving explicit Faculty confirmation?**

---

## Critical Constraints Summary

**NEVER:**
* Answer with information not in the uploaded document (when provided)
* Proceed without clarifying ambiguous questions
* Skip the dual-verification process
* Exceed 150 words per response (except final complete lesson plan)
* Ignore Faculty requests or suggestions
* **Proceed to explain lesson content without waiting for Faculty's explicit confirmation after asking a question**
* **Start explaining components or providing lesson content immediately after asking about prerequisites or topics - always wait for the answer first**

**ALWAYS:**
* Prioritize Faculty's requests above all else
* Prioritize uploaded document over knowledge base
* Stay document-focused
* Build lessons logically from prerequisites to complex topics
* Communicate clearly where you are in lesson development
* Encourage Faculty creativity and input

---

## Success Criteria

A lesson plan is complete and successful when:
* All Faculty questions are answered from document content
* Prerequisites are identified and addressed
* Logical progression from basic to complex is maintained
* All ambiguities are resolved through clarification
* Faculty explicitly confirms the plan meets their teaching objectives
* Lesson is structured as a series of connected "simpler short lectures"

{form_context_section}{context_section}

**TONE:**
- Warm and professional
- Encouraging and supportive
- Clear and actionable
- Respectful of the teacher's expertise

Remember: You're a helpful assistant, not starting from scratch each time. Use the conversation history wisely.
"""
        return unified_prompt.strip()

    def _llm_responce(self, rag_prompt: str, lesson_details: Optional[Dict[str, str]] = None) -> str:
        """
        Generate lesson response using RAG prompt (for large documents)
        
        Args:
            rag_prompt: Pre-formatted prompt with retrieved context
            lesson_details: Additional lesson details
            
        Returns:
            String response from LLM
        """
        teacher_logger.info("=== AI LESSON GENERATION WITH RAG STARTED ===")
        teacher_logger.info(f"RAG prompt length: {len(rag_prompt)} characters")
        
        try:
            # Use the RAG prompt directly with the LLM
            response = self.llm.invoke(rag_prompt)
            teacher_logger.info("LLM response received")
            
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)
            
            teacher_logger.info(f"Response content length: {len(response_content)} characters")
            teacher_logger.info("=== AI LESSON GENERATION WITH RAG COMPLETED ===")
            
            return response_content
                
        except Exception as e:
            teacher_logger.error(f"Error in RAG lesson generation: {str(e)}")
            return f"Error generating lesson: {str(e)}"


        

    def _generate_structured_lesson(self, text: str, lesson_details: Optional[Dict[str, str]] = None) -> str:
        """Generate lesson response based on user intent."""
        teacher_logger.info("=== AI LESSON GENERATION STARTED ===")
        teacher_logger.info(f"Text length: {len(text)} characters")
        
        try:
            max_chars = 1000000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
                teacher_logger.info(f"Text truncated to {max_chars} characters")
                logger.info(f"Text truncated to {max_chars} characters")

            user_prompt = ""
            grade_level = ""
            focus_area = ""

            if lesson_details:
                user_prompt = lesson_details.get("lesson_prompt", "").strip()
                grade_level = lesson_details.get("grade_level", "")
                focus_area = lesson_details.get("focus_area", "")

            teacher_logger.info(f"User prompt: {user_prompt}")
            teacher_logger.info(f"Grade level: {grade_level}")
            teacher_logger.info(f"Focus area: {focus_area}")

            return self._generate_direct_answer(text, user_prompt)

        except Exception as e:
            teacher_logger.error(f"Structured lesson generation failed: {str(e)}")
            logger.error(f"Error generating structured lesson: {str(e)}", exc_info=True)
            return f"Error generating lesson: {str(e)}"

    # def _user_wants_lesson_plan(self, user_prompt: str) -> bool:
    #     """Determine if user wants a lesson plan or just an answer"""
    #     if not user_prompt:
    #         return True  # Default to lesson plan if no prompt
        
    #     # Keywords that indicate user wants a lesson plan
    #     lesson_keywords = [
    #         "generate lesson", "create lesson", "make lesson", "lesson plan",
    #         "teaching plan", "educational plan", "curriculum", "syllabus",
    #         "lesson from", "lesson based on", "teach this", "explain as lesson"
    #     ]
        
    #     # Keywords that indicate user wants a direct answer
    #     question_keywords = [
    #         "what is", "how does", "explain", "tell me", "describe",
    #         "why", "when", "where", "which", "who", "how",
    #         "question", "answer", "help me understand"
    #     ]
        
    #     prompt_lower = user_prompt.lower()
        
    #     # Check for lesson keywords first
    #     for keyword in lesson_keywords:
    #         if keyword in prompt_lower:
    #             return True
        
    #     # Check for question keywords
    #     for keyword in question_keywords:
    #         if keyword in prompt_lower:
    #             return False
        
    #     # Default to lesson plan if unclear
    #     return True

    def _generate_lesson_plan(self, text: str, user_prompt: str, grade_level: str, focus_area: str) -> Dict[str, Any]:
        """Generate a comprehensive lesson plan"""
        teacher_logger.info("=== LESSON PLAN GENERATION STARTED ===")
        teacher_logger.info(f"Text length: {len(text)}")
        teacher_logger.info(f"User prompt: {user_prompt}")
        teacher_logger.info(f"Grade level: {grade_level}")
        teacher_logger.info(f"Focus area: {focus_area}")
        
        try:
            # Create Pydantic output parser
            teacher_logger.info("Setting up Pydantic output parser")
            parser = PydanticOutputParser(pydantic_object=LessonResponse)

            # Create prompt template for lesson plan
            teacher_logger.info("Creating prompt template for lesson plan")
            prompt_template = PromptTemplate(
                template="""You are an expert teacher. Create a comprehensive lesson plan based on the document content and user request.

Document Content:
{text}

User Request:
{user_prompt}

Grade Level: {grade_level}
Focus Area: {focus_area}

Create a complete lesson plan with:
- Clear title and summary
- Learning objectives
- Background prerequisites
- Structured sections with detailed content
- Creative activities for students
- Assessment questions
- Teacher notes

Use language appropriate for grade level: {grade_level}
Focus on subject area: {focus_area}

{format_instructions}""",
                input_variables=["text", "user_prompt", "grade_level", "focus_area"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )

            # Create chain with LLM and parser
            teacher_logger.info("Creating LLM chain")
            chain = prompt_template | self.llm | parser

            # Invoke the chain
            teacher_logger.info("Invoking LLM for lesson plan generation")
            result = chain.invoke({
                "text": text,
                "user_prompt": user_prompt,
                "grade_level": grade_level,
                "focus_area": focus_area
            })
            
            teacher_logger.info(f"LLM response received: {result.response_type}")
            logger.info(f"Generated lesson plan: {result.response_type}")
            
            if result.response_type == "lesson_plan" and result.answer:
                lesson_dict = result.answer.dict()
                teacher_logger.info(f"Lesson plan generated successfully with {len(lesson_dict.get('sections', []))} sections")
                teacher_logger.info(f"Learning objectives: {len(lesson_dict.get('learning_objectives', []))}")
                teacher_logger.info(f"Creative activities: {len(lesson_dict.get('creative_activities', []))}")
                teacher_logger.info(f"Quiz questions: {len(lesson_dict.get('assessment_quiz', []))}")
                teacher_logger.info("=== LESSON PLAN GENERATION COMPLETED ===")
                
                return {
                    "response_type": "lesson_plan",
                    "lesson": lesson_dict
                }
            else:
                teacher_logger.warning("LLM didn't generate lesson plan, using fallback")
                logger.warning("LLM didn't generate lesson plan, using fallback")
                return self._create_fallback_lesson(text)
                
        except Exception as e:
            teacher_logger.error(f"Lesson plan generation failed: {str(e)}")
            logger.error(f"Error generating lesson plan: {str(e)}")
            return self._create_fallback_lesson(text)

    def _generate_direct_answer(self, text: str, user_prompt: str) -> str:
        """Generate a direct detailed answer to user's question"""
        teacher_logger.info("=== DIRECT ANSWER GENERATION STARTED ===")
        teacher_logger.info(f"Text length: {len(text)}")
        teacher_logger.info(f"User question: {user_prompt}")
        
        try:
            # Create a simple prompt for direct answers
            teacher_logger.info("Creating prompt for direct answer")
            answer_prompt = f"""You are a helpful teacher. Answer the user's question based on the document content.

Document Content:
{text}

User Question:
{user_prompt}

Provide a detailed, comprehensive answer that directly addresses the user's question. Use information from the document content to support your answer. Be thorough and educational.

Answer:"""

            teacher_logger.info("Invoking LLM for direct answer")
            response = self.llm.invoke(answer_prompt)
            
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                answer_text = response.content.strip()
            else:
                answer_text = str(response).strip()
            
            teacher_logger.info(f"Direct answer generated successfully - length: {len(answer_text)}")
            teacher_logger.info("=== DIRECT ANSWER GENERATION COMPLETED ===")
            logger.info(f"Generated direct answer (length: {len(answer_text)})")
            
            return answer_text
            
        except Exception as e:
            teacher_logger.error(f"Direct answer generation failed: {str(e)}")
            logger.error(f"Error generating direct answer: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"

    def _create_fallback_lesson(self, text: str) -> Dict[str, Any]:
        """Create a fallback lesson when AI generation fails"""
        return {
            "response_type": "lesson_plan",
            "lesson": {
                "title": "Generated Lesson",
                "summary": "A lesson generated from your content.",
                "learning_objectives": ["Understand the key concepts"],
                "key_concepts": ["Key concepts from the content"],
                "background_prerequisites": ["Basic understanding of the topic"],
                "sections": [
                    {
                        "heading": "Introduction",
                        "content": text[:1000] + "..." if len(text) > 1000 else text
                    }
                ],
                "creative_activities": [],
                "stem_equations": [],
                "assessment_quiz": [],
                "teacher_notes": ["Review the content before teaching"]
            }
        }

    def _extract_sections_from_prompt(self, text: str, prompt: str) -> str:
        """Extract specific sections based on user prompt"""
        # Simple keyword-based extraction
        # This could be enhanced with more sophisticated NLP
        keywords = prompt.lower().split()
        sentences = text.split('.')
        relevant_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                relevant_sentences.append(sentence.strip())
        
        return '. '.join(relevant_sentences) if relevant_sentences else ""

    def _extract_lesson_text_for_rag(self, lesson_data: Dict[str, Any]) -> str:
        """Extract all text content from lesson data for RAG storage"""
        try:
            text_parts = []
            
            # Add title and summary
            if lesson_data.get('title'):
                text_parts.append(f"Title: {lesson_data['title']}")
            if lesson_data.get('summary'):
                text_parts.append(f"Summary: {lesson_data['summary']}")
            
            # Add learning objectives
            if lesson_data.get('learning_objectives'):
                text_parts.append("Learning Objectives:")
                for obj in lesson_data['learning_objectives']:
                    text_parts.append(f"- {obj}")
            
            # Add sections
            if lesson_data.get('sections'):
                for section in lesson_data['sections']:
                    if section.get('heading'):
                        text_parts.append(f"\n{section['heading']}:")
                    if section.get('content'):
                        text_parts.append(section['content'])
            
            # Add key concepts
            if lesson_data.get('key_concepts'):
                text_parts.append("\nKey Concepts:")
                for concept in lesson_data['key_concepts']:
                    text_parts.append(f"- {concept}")
            
            # Add background prerequisites
            if lesson_data.get('background_prerequisites'):
                text_parts.append("\nBackground Prerequisites:")
                for prereq in lesson_data['background_prerequisites']:
                    text_parts.append(f"- {prereq}")
            
            # Add creative activities
            if lesson_data.get('creative_activities'):
                text_parts.append("\nCreative Activities:")
                for activity in lesson_data['creative_activities']:
                    if activity.get('name'):
                        text_parts.append(f"\n{activity['name']}:")
                    if activity.get('description'):
                        text_parts.append(activity['description'])
                    if activity.get('learning_purpose'):
                        text_parts.append(f"Purpose: {activity['learning_purpose']}")
            
            # Add STEM equations
            if lesson_data.get('stem_equations'):
                text_parts.append("\nSTEM Equations:")
                for eq in lesson_data['stem_equations']:
                    if eq.get('equation'):
                        text_parts.append(f"Equation: {eq['equation']}")
                    if eq.get('complete_equation_significance'):
                        text_parts.append(f"Significance: {eq['complete_equation_significance']}")
            
            # Add assessment quiz
            if lesson_data.get('assessment_quiz'):
                text_parts.append("\nAssessment Quiz:")
                for q in lesson_data['assessment_quiz']:
                    if q.get('question'):
                        text_parts.append(f"Q: {q['question']}")
                    if q.get('answer'):
                        text_parts.append(f"A: {q['answer']}")
            
            # Add teacher notes
            if lesson_data.get('teacher_notes'):
                text_parts.append("\nTeacher Notes:")
                for note in lesson_data['teacher_notes']:
                    text_parts.append(f"- {note}")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            teacher_logger.error(f"Error extracting lesson text for RAG: {str(e)}")
            return ""

    def _store_original_document_rag(self, filename: str):
        """Store the original document's RAG service for AI review"""
        try:
            # Create a unique key for this document
            document_key = f"document_{filename}_{hash(filename) % 10000}"
            
            # Store the current RAG service instance (which contains the original document)
            if hasattr(self.rag_service, 'vector_store') and self.rag_service.vector_store:
                # Create a copy of the RAG service to avoid overwriting
                from copy import deepcopy
                rag_service_copy = deepcopy(self.rag_service)
                
                self.lesson_vector_stores[document_key] = {
                    'rag_service': rag_service_copy,
                    'filename': filename,
                    'content': 'original_document',  # Mark as original document
                    'type': 'original_document'
                }
                teacher_logger.info(f"Original document RAG service stored with key: {document_key}")
                teacher_logger.info(f"Vector store contains {len(rag_service_copy.documents)} chunks")
            else:
                teacher_logger.warning("No vector store available to store")
                
        except Exception as e:
            teacher_logger.error(f"Error storing original document RAG: {str(e)}")

    def _store_lesson_in_vector_db(self, lesson_content: str, filename: str):
        """Store lesson content in vector database for AI review"""
        try:
            # Create a unique key for this lesson
            lesson_key = f"lesson_{filename}_{hash(lesson_content) % 10000}"
            
            # Create documents from lesson content
            from langchain_core.documents import Document
            documents = [Document(page_content=lesson_content, metadata={"lesson_key": lesson_key, "filename": filename})]
            
            # Process with RAG service
            rag_result = self.rag_service.process_document(documents, filename)
            if 'error' not in rag_result:
                # Store the RAG service instance for this lesson
                self.lesson_vector_stores[lesson_key] = {
                    'rag_service': self.rag_service,
                    'filename': filename,
                    'content': lesson_content
                }
                teacher_logger.info(f"Lesson stored in vector DB with key: {lesson_key}")
            else:
                teacher_logger.error(f"Failed to store lesson in vector DB: {rag_result['error']}")
                
        except Exception as e:
            teacher_logger.error(f"Error storing lesson in vector DB: {str(e)}")

    def review_lesson_with_rag(self, lesson_content: str, user_prompt: str, filename: str = "") -> str:
        """Review lesson content using RAG to retrieve relevant information"""
        try:
            teacher_logger.info("=== RAG-BASED LESSON REVIEW STARTED ===")
            teacher_logger.info(f"User prompt: {user_prompt}")
            teacher_logger.info(f"Filename: {filename}")
            
            # Try to find existing vector store for this lesson
            lesson_key = None
            for key, store_data in self.lesson_vector_stores.items():
                if store_data['filename'] == filename or store_data['content'] == lesson_content:
                    lesson_key = key
                    break
            
            if lesson_key and lesson_key in self.lesson_vector_stores:
                teacher_logger.info(f"Using existing vector store: {lesson_key}")
                rag_service = self.lesson_vector_stores[lesson_key]['rag_service']
            else:
                teacher_logger.info("Creating new vector store for lesson review")
                # Create new RAG service for this lesson
                from langchain_core.documents import Document
                documents = [Document(page_content=lesson_content, metadata={"filename": filename})]
                rag_service = RAGService()
                rag_result = rag_service.process_document(documents, filename)
                
                if 'error' in rag_result:
                    teacher_logger.error(f"Failed to create vector store: {rag_result['error']}")
                    # Fallback to regular improvement
                    return self.improve_lesson_content(0, lesson_content, user_prompt)
            
            # Retrieve relevant chunks
            relevant_chunks = rag_service.retrieve_relevant_chunks(user_prompt, k=5)
            if not relevant_chunks:
                teacher_logger.warning("No relevant chunks found, using full content")
                relevant_chunks = [Document(page_content=lesson_content, metadata={})]
            
            # Create RAG prompt
            rag_prompt = rag_service.create_rag_prompt(user_prompt, relevant_chunks)
            
            # Generate response using RAG
            teacher_logger.info("Generating RAG-based response")
            response = self.llm.invoke(rag_prompt)

            response=response.content
            
            # response_content = response.content if hasattr(response, 'content') else str(response)

            
            
            # Check if the response is in JSON format and extract the actual content
            # try:
            #     import json
            #     parsed_response = json.loads(response_content)
            #     if isinstance(parsed_response, dict) and 'answer' in parsed_response:
            #         response_content = parsed_response['answer']
            #     elif isinstance(parsed_response, dict) and 'response' in parsed_response:
            #         response_content = parsed_response['response']
            #     elif isinstance(parsed_response, dict) and 'content' in parsed_response:
            #         response_content = parsed_response['content']
            # except (json.JSONDecodeError, AttributeError):
            #     pass
            
            teacher_logger.info("=== RAG-BASED LESSON REVIEW COMPLETED ===")
            return response
            
        except Exception as e:
            teacher_logger.error(f"Error in RAG-based lesson review: {str(e)}")
            # Fallback to regular improvement
            return "no relevant info found"
            # return self.improve_lesson_content(0, lesson_content, user_prompt)

    def improve_lesson_content(self, lesson_id: int, current_content: str, improvement_prompt: str = "") -> str:
        """Improve lesson content using AI based on user prompt"""
        try:
            # Create improvement prompt
            #fetch the original content from lesson id
            original_content = LessonModel.get_lesson_by_id(lesson_id)['original_content']
            if improvement_prompt:
                
                prompt = f"""You are an expert assistant. Improve or modify the following content based on the user's specific request or if user ask any question from the content also respond the answer from the content as well.

            User's Request:
            {improvement_prompt}

            Original Content:
            {original_content}

            Current Content:
            {current_content}

            CRITICAL INSTRUCTIONS:

            1. CONTENT SOURCES:
            - You have access to BOTH the original and current versions of the content
            - Use whichever version (or combination of both) best fulfills the user's request
            - If user wants to add back something from original: Pull from original content
            - If user wants to keep recent changes: Use current content
            - If user wants the best of both: Intelligently combine information from both versions
            - Default: Use current content as the primary base, but reference original if it helps

            2. MANDATORY FORMAT - Always use proper markdown formatting:
            - Use ## for main headers, ### for subheaders
            - Use **bold** for key terms and important concepts
            - Use - or * for bullet points
            - Use 1. 2. 3. for numbered lists
            - Use > for quotes or callouts
            - Use `code` for technical terms when appropriate
            - EXCEPTION: If user requests "one line" or "single line", output everything as ONE CONTINUOUS SENTENCE with NO line breaks, but still use **bold** and *italic* for emphasis

            3. CONTENT MODIFICATIONS based on user request:
            - "one line" or "single line" or "give me response in one line": 
                * MUST condense EVERYTHING into literally ONE SENTENCE
                * NO line breaks, NO bullet points, NO numbered lists, NO headers
                * Use **bold** for key terms within that single sentence
                * Example: "**John Doe** is a software engineer specializing in web development, cloud computing, and AI integration with 5 years of experience building scalable applications."
            
            - "concise" or "summary": 2-4 sentences with markdown formatting
            
            - "detailed" or "expanded": Multiple paragraphs with full markdown structure (headers, bullets, bold terms)
            
            - "structured": Organize with clear headers, subheaders, and bullet points
            
            - "combine both versions": Merge the best elements from original and current
            
            - "use original" or "revert to original": Base response primarily on original content
            
            - Any other request: Apply it flexibly using information from both versions as needed

            4. ABSOLUTE RULES:
            - If user says "one line" → Output must be EXACTLY one continuous sentence, no exceptions
            - For all other requests: ALWAYS use proper markdown formatting
            - User's request is the TOP priority - use original, current, or both as needed to satisfy it
            - Return ONLY the improved content
            - NO meta-commentary like "Since the user requested..." or "I have condensed..."
            - NO explanations about what you did or why
            - Just return the final improved content directly

            ##always follow this instruction##
              when user ask the question from the content also give the answer consiley if user exlicity request for
              **one** line answer also give the answer in one line
              if user say gave me two line answer gove the answer in two line
              if the user say give me detailed answer give the answer in detailed manner
            """
            # Generate improved content using LLM
            response = self.llm.invoke(prompt)
            improved_content = response.content.strip()
            
            # Check if the response is in JSON format and extract the actual content
            try:
                import json
                # Try to parse as JSON
                parsed_response = json.loads(improved_content)
                # If it has the expected JSON structure (like chat responses), extract the answer
                if isinstance(parsed_response, dict) and 'answer' in parsed_response:
                    improved_content = parsed_response['answer']
                elif isinstance(parsed_response, dict) and 'response' in parsed_response:
                    improved_content = parsed_response['response']
                elif isinstance(parsed_response, dict) and 'content' in parsed_response:
                    improved_content = parsed_response['content']
            except (json.JSONDecodeError, AttributeError):
                # Not a JSON response, use as-is
                pass
            
            logger.info(f"Successfully improved lesson {lesson_id} content")
            return improved_content
            
        except Exception as e:
            logger.error(f"Error improving lesson content: {str(e)}")
            # Return original content if improvement fails
            return current_content

    def edit_lesson_with_prompt(self, lesson_text: str, user_prompt: str, filename: str = "") -> str:
        """Use RAG system for semantic chunk retrieval and editing"""
        try:
            teacher_logger.info("=== AI REVIEW WITH RAG STARTED ===")
            teacher_logger.info(f"User prompt: {user_prompt}")
            teacher_logger.info(f"Filename: {filename}")
            teacher_logger.info(f"Lesson text length: {len(lesson_text)}")
            
            # Try to find existing vector store for this lesson/document
            lesson_key = None
            for key, store_data in self.lesson_vector_stores.items():
                if (store_data['filename'] == filename or filename in store_data['filename']) and store_data.get('type') == 'original_document':
                    lesson_key = key
                    break

            #retced the relevnt chunk from saved faiss
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            import tempfile
            import os
            # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

            # vector_db = FAISS.load_local("vector_store.faiss", embeddings, allow_dangerous_deserialization=True)
            # relevant_docs = vector_db.similarity_search(user_prompt, k=10)
            # # relevant_texts = [doc.page_content for doc in relevant_docs]
            # # lesson_text=["\n the previous version context".join(lesson_text)]

            # lesson_doc = Document(page_content="\n the previous version context".join(lesson_text))
            # relevant_docs.append(lesson_doc)
            from langchain_core.documents import Document
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings

            # Environment variables TQDM_DISABLE and TOKENIZERS_PARALLELISM are set at app startup
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={
                    'device': 'cpu',
                    'trust_remote_code': False
                },
                encode_kwargs={
                    'normalize_embeddings': False
                }
            )
            vector_db = FAISS.load_local("vector_store.faiss", embeddings, allow_dangerous_deserialization=True)

            # Retrieve relevant docs (these are already Document objects)
            relevant_docs = vector_db.similarity_search(user_prompt, k=10)

            # Add the full lesson text as another Document
            lesson_doc = Document(page_content="\n the previous version context".join(lesson_text))
            relevant_docs.append(lesson_doc)
            #combined with relevant chunks
            # relevant_texts=relevant_texts+lesson_text
            rag_service=RAGService()

            

            #combine
            rag_prompt = rag_service.create_rag_prompt(user_prompt, relevant_docs)
                
                # Generate response using RAG
            teacher_logger.info("Generating RAG-based response from original document")
            response = self.llm.invoke(rag_prompt)
            response_content = response.content
            return response_content
            
            if lesson_key and lesson_key in self.lesson_vector_stores:
                teacher_logger.info(f"Using existing original document vector store: {lesson_key}")
                rag_service = self.lesson_vector_stores[lesson_key]['rag_service']
                
                # Retrieve relevant chunks from original document
                relevant_chunks = rag_service.retrieve_relevant_chunks(user_prompt, k=10)
                if not relevant_chunks:
                    teacher_logger.warning("No relevant chunks found, using first few chunks")
                    relevant_chunks = rag_service.documents[:9]
                
                # Create RAG prompt with retrieved context
                rag_prompt = rag_service.create_rag_prompt(user_prompt, relevant_chunks)
                
                # Generate response using RAG
                teacher_logger.info("Generating RAG-based response from original document")
                response = self.llm.invoke(rag_prompt)
                
                if hasattr(response, 'content'):
                    response_content = response.content
                else:
                    response_content = str(response)
                
                teacher_logger.info("=== AI REVIEW WITH RAG COMPLETED ===")
                return response_content
                
            else:
                teacher_logger.info("No existing original document vector store found, creating new one from lesson text")

                print("-----------------------fallback responce---------------------")
                print(lesson_text)
                print("-----------------------fallback responce---------------------")
                # Fallback to creating vector store from lesson text
                return self._edit_lesson_with_fallback_rag(lesson_text, user_prompt)
                
        except Exception as e:
            teacher_logger.error(f"Error in RAG-based lesson editing: {str(e)}")
            # Fallback to simple editing
            return self._edit_lesson_simple(lesson_text, user_prompt)
    
    def _edit_lesson_with_fallback_rag(self, lesson_text: str, user_prompt: str) -> str:
        """Fallback method to create RAG from lesson text"""
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            import tempfile
            import os

            # 1. Chunk the lesson (by paragraph)
            chunks = [p.strip() for p in lesson_text.split('\n\n') if p.strip()]
            if not chunks:
                return lesson_text

            # 2. Embed and store in FAISS
            # Environment variables TQDM_DISABLE and TOKENIZERS_PARALLELISM are set at app startup
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={
                    'device': 'cpu',
                    'trust_remote_code': False
                },
                encode_kwargs={
                    'normalize_embeddings': False
                }
            )
            
            with tempfile.TemporaryDirectory() as tmpdir:
                faiss_path = os.path.join(tmpdir, "faiss_index")
                vector_db = FAISS.from_texts(chunks, embeddings)
                vector_db.save_local(faiss_path)

                # 3. Retrieve relevant chunks for the user prompt
                vector_db = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
                relevant_docs = vector_db.similarity_search(user_prompt, k=min(5, len(chunks)))
                relevant_texts = [doc.page_content for doc in relevant_docs]

                # 4. Edit relevant chunks with LLM
                edited_chunks = {}
                for text in relevant_texts:
                    edit_prompt = (
                        f"You are an expert teacher assistant. Here is a lesson chunk:\n\n"
                        f"{text}\n\n"
                        f"User request: {user_prompt}\n\n"
                        f"Please return the revised lesson chunk."
                    )
                    response = self.llm.invoke(edit_prompt)
                    edited = response.content if hasattr(response, 'content') else str(response)
                    
                    # Check if the response is in JSON format and extract the actual content
                    try:
                        import json
                        parsed_response = json.loads(edited)
                        if isinstance(parsed_response, dict) and 'answer' in parsed_response:
                            edited = parsed_response['answer']
                        elif isinstance(parsed_response, dict) and 'response' in parsed_response:
                            edited = parsed_response['response']
                        elif isinstance(parsed_response, dict) and 'content' in parsed_response:
                            edited = parsed_response['content']
                    except (json.JSONDecodeError, AttributeError):
                        pass
                    
                    edited_chunks[text] = edited

                # 5. Replace original chunks with edited ones
                new_chunks = [edited_chunks.get(chunk, chunk) for chunk in chunks]

            # 6. Reconstruct and return the lesson
            return '\n\n'.join(new_chunks)
        except Exception as e:
            logger.error(f"Error in fallback RAG editing: {str(e)}", exc_info=True)
            return self._edit_lesson_simple(lesson_text, user_prompt)
    
    def _edit_lesson_simple(self, lesson_text: str, user_prompt: str) -> str:
        """Simple editing without RAG"""
        try:
            edit_prompt = f"""You are an expert teacher assistant. Please improve the following lesson content based on the user's request.

Lesson Content:
{lesson_text}

User Request:
{user_prompt}

Please provide an improved version of the lesson content that addresses the user's request. Return only the improved content."""

            response = self.llm.invoke(edit_prompt)
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
        except Exception as e:
            logger.error(f"Error in simple lesson editing: {str(e)}")
            return lesson_text

    def create_ppt(self, lesson_data: dict) -> bytes:
        """Generate a basic PPTX file from the lesson structure using python-pptx"""
        try:
            logger.info(f"Creating PowerPoint for lesson: {lesson_data.get('title', 'Unknown')}")
            logger.info(f"Lesson data keys: {list(lesson_data.keys())}")
            logger.info(f"Content length: {len(lesson_data.get('content', ''))}")
            
            from pptx import Presentation
            from pptx.util import Inches, Pt
            prs = Presentation()
            
            # Title slide
            slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(slide_layout)
            slide.shapes.title.text = lesson_data.get('title', 'Lesson')
            slide.placeholders[1].text = lesson_data.get('summary', '')
            
            # Learning Objectives
            if lesson_data.get('learning_objectives'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Learning Objectives'
                body = slide.shapes.placeholders[1].text_frame
                for obj in lesson_data['learning_objectives']:
                    body.add_paragraph().text = str(obj)
            
            # Helper function to split content intelligently
            def split_content_into_chunks(content: str, max_length: int = 800) -> List[str]:
                """Split content into manageable chunks respecting paragraph boundaries"""
                if len(content) <= max_length:
                    return [content]
                
                chunks = []
                paragraphs = content.split('\n\n')
                current_chunk = ""
                
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    
                    # If adding this paragraph would exceed the limit
                    if current_chunk and len(current_chunk) + len(para) + 2 > max_length:
                        chunks.append(current_chunk)
                        current_chunk = para
                    else:
                        if current_chunk:
                            current_chunk += "\n\n" + para
                        else:
                            current_chunk = para
                    
                    # If a single paragraph is too long, split it by sentences
                    if len(para) > max_length:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""
                        # Split by sentences
                        sentences = para.replace('. ', '.\n').split('\n')
                        temp_chunk = ""
                        for sent in sentences:
                            if temp_chunk and len(temp_chunk) + len(sent) + 1 > max_length:
                                chunks.append(temp_chunk)
                                temp_chunk = sent
                            else:
                                temp_chunk += "\n" + sent if temp_chunk else sent
                        current_chunk = temp_chunk
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                return chunks
            
            # Sections
            sections = lesson_data.get('sections', [])
            if sections:
                logger.info(f"Creating slides for {len(sections)} sections")
                for section in sections:
                    content = section.get('content', '')
                    heading = section.get('heading', 'Section')
                    
                    # Split content into manageable chunks
                    content_chunks = split_content_into_chunks(content)
                    
                    for chunk_idx, chunk in enumerate(content_chunks):
                        slide = prs.slides.add_slide(prs.slide_layouts[1])
                        
                        # Set title - append part number if multiple slides
                        if len(content_chunks) > 1:
                            slide.shapes.title.text = f"{heading} (Part {chunk_idx + 1}/{len(content_chunks)})"
                        else:
                            slide.shapes.title.text = heading
                        
                        body = slide.shapes.placeholders[1].text_frame
                        body.text = chunk
                        
                        # Configure text formatting for readability
                        body.word_wrap = True
                        for paragraph in body.paragraphs:
                            paragraph.space_after = Pt(6)
                            paragraph.font.size = Pt(12)
            else:
                # If no sections, create a content slide with the main content
                if lesson_data.get('content'):
                    logger.info("Creating content slides with main lesson content")
                    content = lesson_data['content']
                    
                    # Split content into manageable chunks
                    content_chunks = split_content_into_chunks(content)
                    
                    for chunk_idx, chunk in enumerate(content_chunks):
                        slide = prs.slides.add_slide(prs.slide_layouts[1])
                        
                        if len(content_chunks) > 1:
                            slide.shapes.title.text = f'Lesson Content (Part {chunk_idx + 1}/{len(content_chunks)})'
                        else:
                            slide.shapes.title.text = 'Lesson Content'
                        
                        body = slide.shapes.placeholders[1].text_frame
                        body.text = chunk
                        
                        # Configure text formatting for readability
                        body.word_wrap = True
                        for paragraph in body.paragraphs:
                            paragraph.space_after = Pt(6)
                            paragraph.font.size = Pt(12)
            
            # Key Concepts
            if lesson_data.get('key_concepts'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Key Concepts'
                body = slide.shapes.placeholders[1].text_frame
                for kc in lesson_data['key_concepts']:
                    body.add_paragraph().text = str(kc)
            
            # Background Prerequisites
            if lesson_data.get('background_prerequisites'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Background Prerequisites'
                body = slide.shapes.placeholders[1].text_frame
                for prereq in lesson_data['background_prerequisites']:
                    body.add_paragraph().text = str(prereq)
            
            # Creative Activities
            if lesson_data.get('creative_activities'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Creative Activities'
                body = slide.shapes.placeholders[1].text_frame
                for act in lesson_data['creative_activities']:
                    body.add_paragraph().text = f"{act.get('name', '')}: {act.get('description', '')} ({act.get('duration', '')})"
                    if act.get('learning_purpose'):
                        body.add_paragraph().text = f"Purpose: {act.get('learning_purpose', '')}"
            
            # STEM Equations
            if lesson_data.get('stem_equations'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'STEM Equations'
                body = slide.shapes.placeholders[1].text_frame
                for eq_data in lesson_data['stem_equations']:
                    if eq_data.get('equation'):
                        body.add_paragraph().text = f"Equation: {eq_data.get('equation', '')}"
                    if eq_data.get('complete_equation_significance'):
                        body.add_paragraph().text = f"Significance: {eq_data.get('complete_equation_significance', '')}"
            
            # Assessment Quiz
            if lesson_data.get('assessment_quiz'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Assessment Quiz'
                body = slide.shapes.placeholders[1].text_frame
                for q in lesson_data['assessment_quiz']:
                    body.add_paragraph().text = f"Q: {q.get('question', '')}"
                    for i, opt in enumerate(q.get('options', [])):
                        body.add_paragraph().text = f"{chr(65+i)}. {opt}"
                    body.add_paragraph().text = f"Answer: {q.get('answer', '')}"
            
            # Teacher Notes
            if lesson_data.get('teacher_notes'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Teacher Notes'
                body = slide.shapes.placeholders[1].text_frame
                for note in lesson_data['teacher_notes']:
                    body.add_paragraph().text = str(note)
            
            # If we only have a title slide, add a content slide
            if len(prs.slides) == 1 and lesson_data.get('content'):
                logger.info("Adding content slide as only title slide exists")
                content = lesson_data['content']
                
                # Split content into manageable chunks
                content_chunks = split_content_into_chunks(content)
                
                for chunk_idx, chunk in enumerate(content_chunks):
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    
                    if len(content_chunks) > 1:
                        slide.shapes.title.text = f'Lesson Content (Part {chunk_idx + 1}/{len(content_chunks)})'
                    else:
                        slide.shapes.title.text = 'Lesson Content'
                    
                    body = slide.shapes.placeholders[1].text_frame
                    body.text = chunk
                    
                    # Configure text formatting for readability
                    body.word_wrap = True
                    for paragraph in body.paragraphs:
                        paragraph.space_after = Pt(6)
                        paragraph.font.size = Pt(12)
            
            logger.info(f"Created PowerPoint with {len(prs.slides)} slides")
            
            from io import BytesIO
            buffer = BytesIO()
            prs.save(buffer)
            buffer.seek(0)
            ppt_bytes = buffer.getvalue()
            logger.info(f"PowerPoint generated successfully, size: {len(ppt_bytes)} bytes")
            return ppt_bytes
        except Exception as e:
            logger.error(f"Error creating PPTX: {str(e)}", exc_info=True)
            return b''

    def _create_docx_from_text(self, lesson_text: str, lesson_details: Optional[Dict[str, str]] = None) -> bytes:
        """Create DOCX from plain text lesson response"""
        try:
            doc = DocxDocument()
            
            # Add title
            title = lesson_details.get('lesson_title', 'Generated Lesson') if lesson_details else 'Generated Lesson'
            doc.add_heading(title, level=1)
            
            # Add lesson content
            doc.add_paragraph(lesson_text)
            
            # Save to bytes buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating DOCX from text: {str(e)}")
            # Return a simple DOCX with error message
            doc = DocxDocument()
            doc.add_heading("Lesson Generation", level=1)
            doc.add_paragraph("A lesson has been generated from your content.")
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()

    def _create_docx(self, lesson_data: Dict[str, Any]) -> bytes:
        """Convert structured lesson to DOCX format with improved formatting"""
        try:
            doc = DocxDocument()
            
            # Add title with formatting
            title = doc.add_heading(level=1)
            title_run = title.add_run(self._sanitize_heading(lesson_data.get("title", "Generated Lesson")))
            title_run.bold = True
            
            # Add summary section
            if lesson_data.get("summary"):
                doc.add_heading(self._sanitize_heading("Summary"), level=2)
                summary = doc.add_paragraph(lesson_data["summary"])
                summary.paragraph_format.space_after = Inches(0.1)
            
            # Add learning objectives with bullet points
            if lesson_data.get("learning_objectives"):
                doc.add_heading(self._sanitize_heading("Learning Objectives"), level=2)
                for objective in lesson_data["learning_objectives"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(objective))
                doc.add_paragraph()
            
            # Add sections with proper spacing
            if lesson_data.get("sections"):
                for section in lesson_data["sections"]:
                    doc.add_heading(self._sanitize_heading(section.get("heading", "Section")), level=2)
                    content = doc.add_paragraph(section.get("content", ""))
                    content.paragraph_format.space_after = Inches(0.1)
                    doc.add_paragraph()
            
            # Add key concepts
            if lesson_data.get("key_concepts"):
                doc.add_heading(self._sanitize_heading("Key Concepts"), level=2)
                for concept in lesson_data["key_concepts"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(concept))
                doc.add_paragraph()
            
            # Add background prerequisites
            if lesson_data.get("background_prerequisites"):
                doc.add_heading(self._sanitize_heading("Background Prerequisites"), level=2)
                for prereq in lesson_data["background_prerequisites"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(prereq))
                doc.add_paragraph()
            
            # Add creative activities with clear formatting
            if lesson_data.get("creative_activities"):
                doc.add_heading(self._sanitize_heading("Creative Activities"), level=2)
                for i, activity in enumerate(lesson_data["creative_activities"], 1):
                    activity_title = doc.add_heading(level=3)
                    activity_title.add_run(self._sanitize_heading(f"Activity {i}: {activity.get('name', 'Unnamed Activity')}")).bold = True
                    
                    desc = doc.add_paragraph()
                    desc.add_run("Description: ").bold = True
                    desc.add_run(str(activity.get('description', '')))
                    
                    if activity.get('duration'):
                        duration = doc.add_paragraph()
                        duration.add_run("Duration: ").bold = True
                        duration.add_run(str(activity['duration']))
                    
                    if activity.get('learning_purpose'):
                        purpose = doc.add_paragraph()
                        purpose.add_run("Learning Purpose: ").bold = True
                        purpose.add_run(str(activity['learning_purpose']))
                    
                    doc.add_paragraph()
            
            # Add STEM equations if present
            if lesson_data.get("stem_equations"):
                doc.add_heading(self._sanitize_heading("STEM Equations"), level=2)
                for i, equation_data in enumerate(lesson_data["stem_equations"], 1):
                    if equation_data.get("equation"):
                        eq_title = doc.add_heading(level=3)
                        eq_title.add_run(self._sanitize_heading(f"Equation {i}")).bold = True
                        
                        eq_para = doc.add_paragraph()
                        eq_para.add_run("Equation: ").bold = True
                        eq_para.add_run(str(equation_data['equation']))
                        
                        if equation_data.get("term_explanations"):
                            terms = doc.add_paragraph()
                            terms.add_run("Term Explanations: ").bold = True
                            for term in equation_data["term_explanations"]:
                                term_p = doc.add_paragraph(style='ListBullet')
                                term_p.add_run(str(term))
                        
                        if equation_data.get("mathematical_operations"):
                            ops = doc.add_paragraph()
                            ops.add_run("Mathematical Operations: ").bold = True
                            ops.add_run(str(equation_data['mathematical_operations']))
                        
                        if equation_data.get("complete_equation_significance"):
                            sig = doc.add_paragraph()
                            sig.add_run("Complete Equation Significance: ").bold = True
                            sig.add_run(str(equation_data['complete_equation_significance']))
                        
                        doc.add_paragraph()
            
            # Add assessment quiz with clear question/answer formatting
            if lesson_data.get("assessment_quiz"):
                doc.add_heading(self._sanitize_heading("Assessment Quiz"), level=2)
                for i, question in enumerate(lesson_data["assessment_quiz"], 1):
                    q = doc.add_paragraph()
                    q.add_run(f"Question {i}: ").bold = True
                    q.add_run(str(question.get('question', '')))
                    
                    # Add options with letters
                    options = ['A', 'B', 'C', 'D']
                    question_options = question.get("options", [])
                    for opt, text in zip(options, question_options):
                        p = doc.add_paragraph(style='ListBullet')
                        p.add_run(f"{opt}. {str(text)}")
                    
                    # Add answer
                    ans = doc.add_paragraph()
                    ans.add_run("Correct Answer: ").bold = True
                    ans.add_run(str(question.get('answer', '')))
                    
                    if question.get('explanation'):
                        exp = doc.add_paragraph()
                        exp.add_run("Explanation: ").bold = True
                        exp.add_run(str(question['explanation']))
                    
                    doc.add_paragraph()
            
            # Add teacher notes
            if lesson_data.get("teacher_notes"):
                doc.add_heading(self._sanitize_heading("Teacher Notes"), level=2)
                for note in lesson_data["teacher_notes"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(note))
                doc.add_paragraph()
            
            # Save to bytes buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating DOCX: {str(e)}")
            # Return a simple DOCX with error message
            doc = DocxDocument()
            doc.add_heading(self._sanitize_heading("Lesson Generation"), level=1)
            doc.add_paragraph("A lesson has been generated from your content.")
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()


