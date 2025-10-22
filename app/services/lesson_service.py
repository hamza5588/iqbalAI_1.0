"""
Main lesson service - now uses structured approach with separate teacher and student services
"""
import logging
from typing import Any, Dict, Optional
from werkzeug.datastructures import FileStorage

from .lesson.teacher_service import TeacherLessonService
from .lesson.student_service import StudentLessonService

# Set up logging
logger = logging.getLogger(__name__)


class LessonService:
    """
    Main lesson service that delegates to specialized teacher and student services.
    This maintains backward compatibility while providing a structured approach.
    """
    def __init__(self, api_key: str):
        """Initialize the LessonService with API key from database."""
        self.api_key = api_key
        self.teacher_service = TeacherLessonService(api_key)
        self.student_service = StudentLessonService(api_key)

    # Delegate methods to appropriate services
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is supported"""
        return self.teacher_service.allowed_file(filename)

    def process_file(self, file: FileStorage, lesson_details: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process an uploaded file and return structured lesson content with DOCX bytes."""
        return self.teacher_service.process_file(file, lesson_details)

    def create_ppt(self, lesson_data: dict) -> bytes:
        """Generate a basic PPTX file from the lesson structure using python-pptx."""
        return self.teacher_service.create_ppt(lesson_data)

    def edit_lesson_with_prompt(self, lesson_text: str, user_prompt: str) -> str:
        """Use a FAISS vector database for semantic chunk retrieval and editing."""
        return self.teacher_service.edit_lesson_with_prompt(lesson_text, user_prompt)

    def improve_lesson_content(self, lesson_id: int, current_content: str, improvement_prompt: str = "") -> str:
        """Improve lesson content using AI based on user prompt"""
        return self.teacher_service.improve_lesson_content(lesson_id, current_content, improvement_prompt)

    def review_lesson_with_rag(self, lesson_content: str, user_prompt: str, filename: str = "") -> str:
        """Review lesson content using RAG to retrieve relevant information from vector database"""
        return self.teacher_service.review_lesson_with_rag(lesson_content, user_prompt, filename)

    # Student-focused methods
    def answer_lesson_question(self, lesson_id: int, question: str) -> Dict[str, str]:
        """Answer a student's question about a specific lesson"""
        return self.student_service.answer_lesson_question(lesson_id, question)

    def get_lesson_faqs(self, lesson_id: int, limit: int = 5) -> list:
        """Get frequently asked questions for a lesson"""
        return self.student_service.get_lesson_faqs(lesson_id, limit)

    def get_lesson_summary(self, lesson_id: int) -> Dict[str, str]:
        """Get a summary of the lesson for students"""
        return self.student_service.get_lesson_summary(lesson_id)

    def get_lesson_key_points(self, lesson_id: int) -> list:
        """Extract key learning points from a lesson"""
        return self.student_service.get_lesson_key_points(lesson_id)

    # Legacy methods for backward compatibility
    def llm_answer(self, lesson_content: str, question: str, lesson_title: str = "this lesson") -> str:
        """Generate an answer using the LLM with lesson-specific context"""
        return self.student_service.llm_answer(lesson_content, question, lesson_title)

    def canonicalize_question(self, lesson_id: int, question: str) -> str:
        """Return a canonical phrasing for the question using semantic similarity"""
        return self.student_service.canonicalize_question(lesson_id, question)