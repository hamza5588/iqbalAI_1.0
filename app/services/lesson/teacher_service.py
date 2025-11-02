"""
Teacher-focused lesson service for creating and managing lessons
"""
import os
import logging
import tempfile
from typing import Any, Dict, List, Optional
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
    
    def __init__(self, groq_api_key: str):
        super().__init__(groq_api_key)
        self.rag_service = RAGService()
        self.lesson_vector_stores = {}  # Store vector DBs for each lesson
        teacher_logger.info("RAG service initialized")

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


    def interactive_chat(self, lesson_id: int, user_query: str) -> str:
        """Interactive chat with the lesson"""
        # Retrieve relevant chunks
        relevant_chunks = self.rag_service.retrieve_relevant_chunks(user_query, k=5)
        if not relevant_chunks:
            teacher_logger.warning("No relevant chunks found, using first few chunks")
            relevant_chunks = self.rag_service.documents[:3]
        
        # Create RAG prompt
        rag_prompt = self.rag_service.create_rag_prompt(user_prompt, relevant_chunks, lesson_details)
        
        # Generate lesson using RAG prompt
        teacher_logger.info("Starting AI lesson generation with RAG")
        lesson_response = self._llm_responce(rag_prompt, lesson_details)
        return lesson_response


        return 
    # def _generate_structured_lesson_with_rag(self, rag_prompt: str, lesson_details: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    #     """
    #     Generate structured lesson using RAG prompt (for large documents)
        
    #     Args:
    #         rag_prompt: Pre-formatted prompt with retrieved context
    #         lesson_details: Additional lesson details
            
    #     Returns:
    #         Dictionary with lesson data or error
    #     """
    #     teacher_logger.info("=== AI LESSON GENERATION WITH RAG STARTED ===")
    #     teacher_logger.info(f"RAG prompt length: {len(rag_prompt)} characters")
        
    #     try:
    #         # Use the RAG prompt directly with the LLM
    #         response = self.llm.invoke(rag_prompt)

    #         teacher_logger.info("LLM response received")
            
    #         # Extract content from AIMessage if needed
    #         if hasattr(response, 'content'):
    #             response_content = response.content
    #         else:
    #             response_content = str(response)
            
    #         # Check if the response is in JSON format and extract the actual content
    #         try:
    #             import json
    #             parsed_response = json.loads(response_content)
    #             if isinstance(parsed_response, dict) and 'answer' in parsed_response:
    #                 response_content = parsed_response['answer']
    #             elif isinstance(parsed_response, dict) and 'response' in parsed_response:
    #                 response_content = parsed_response['response']
    #             elif isinstance(parsed_response, dict) and 'content' in parsed_response:
    #                 response_content = parsed_response['content']
    #         except (json.JSONDecodeError, AttributeError):
    #             pass
            
    #         teacher_logger.info(f"Response content length: {len(response_content)} characters")
            
    #         # Parse the response
    #         if lesson_details and self._user_wants_lesson_plan(lesson_details.get('lesson_prompt', '')):
    #             # Try to parse as structured lesson plan
    #             try:
    #                 parser = PydanticOutputParser(pydantic_object=LessonResponse)
    #                 lesson_response = parser.parse(response_content)
    #                 teacher_logger.info("Successfully parsed as lesson plan")
    #                 return {
    #                     "response_type": "lesson_plan",
    #                     "lesson": lesson_response.dict(),
    #                     "user_question": lesson_details.get('lesson_prompt', '')
    #                 }
    #             except Exception as e:
    #                 teacher_logger.warning(f"Failed to parse as lesson plan: {str(e)}")
    #                 # Fallback to direct answer
    #                 return {
    #                     "response_type": "direct_answer",
    #                     "answer": response_content,
    #                     "user_question": lesson_details.get('lesson_prompt', '')
    #                 }
    #         else:
    #             # Direct answer
    #             teacher_logger.info("Generated direct answer")
    #             return {
    #                 "response_type": "direct_answer",
    #                 "answer": response_content,
    #                 "user_question": lesson_details.get('lesson_prompt', '') if lesson_details else ''
    #             }
                
    #     except Exception as e:
    #         teacher_logger.error(f"Error in RAG lesson generation: {str(e)}")
    #         return {"error": f"Error generating lesson: {str(e)}"}


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

            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
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
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
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


