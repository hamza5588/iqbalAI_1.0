"""
Student-focused lesson service for answering questions and providing learning support
"""
import logging
import re
import sqlite3
import os
from typing import Dict, List, Optional
from langchain_community.embeddings import HuggingFaceEmbeddings
from datetime import datetime
import json

from .base_service import BaseLessonService
from .rag_service import RAGService
from app.models.models import LessonFAQ, LessonModel

logger = logging.getLogger(__name__)

# Set up detailed student service logging
student_logger = logging.getLogger('student_service')
student_logger.setLevel(logging.INFO)

# Create student.log file handler (using same file as teacher for consolidated logging)
if not os.path.exists('logs'):
    os.makedirs('logs')

student_handler = logging.FileHandler('logs/lesson.log')
student_handler.setLevel(logging.INFO)

# Create formatter for student logs
student_formatter = logging.Formatter(
    '%(asctime)s - STUDENT_SERVICE - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
student_handler.setFormatter(student_formatter)
student_logger.addHandler(student_handler)


class StudentLessonService(BaseLessonService):
    """
    Student-focused lesson service for:
    1. Answering questions about lessons
    2. Providing learning support
    3. Managing FAQ and question history
    4. Generating lesson-specific FAQs
    """
    
    def __init__(self, groq_api_key: str):
        super().__init__(groq_api_key)
        self.rag_service = RAGService()
        student_logger.info("RAG service initialized for student service")

    def answer_lesson_question(self, lesson_id: int, question: str) -> Dict[str, str]:
        """Answer a student's question about a specific lesson"""
        student_logger.info(f"=== STUDENT QUESTION PROCESSING STARTED ===")
        student_logger.info(f"Lesson ID: {lesson_id}")
        student_logger.info(f"Question: {question}")
        
        # Get lesson content
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            # Handle demo lessons that don't exist in database
            if lesson_id in [1, 2, 3]:
                student_logger.info(f"Using demo lesson for ID: {lesson_id}")
                demo_lessons = {
                    1: {
                        'title': 'Introduction to Climate',
                        'content': 'Climate refers to the long-term patterns of temperature, humidity, wind, and precipitation in a particular region. Unlike weather, which describes short-term atmospheric conditions, climate represents the average weather conditions over a period of 30 years or more. Key concepts include climate vs weather, climate factors (latitude, altitude, ocean currents, wind patterns, landforms), and climate zones (tropical, temperate, polar, desert). Climate change is a significant topic, with human activities like burning fossil fuels contributing to increased greenhouse gas concentrations.'
                    },
                    2: {
                        'title': 'World History Overview',
                        'content': 'World history encompasses the study of human civilization from its earliest beginnings to the present day. Major periods include Ancient Civilizations (Mesopotamia, Egypt, Greece, Rome), Middle Ages (500-1500 CE), Early Modern Period (1500-1800), and Modern Period (1800-Present). Key themes include power and politics, economics, culture, technology, and environment. Understanding world history helps us make sense of current events and prepare for future challenges.'
                    },
                    3: {
                        'title': 'Physics Fundamentals',
                        'content': 'Physics is the study of matter, energy, and their interactions. Core areas include mechanics (Newton\'s laws, forces, energy, momentum), waves and sound (wave properties, sound waves), electricity and magnetism (electric charges, current, magnetism), and modern physics (quantum mechanics, relativity). Physics principles apply to engineering, medicine, technology, space exploration, and energy. Understanding physics helps us comprehend the natural world and develop technologies that improve our lives.'
                    }
                }
                demo_lesson = demo_lessons[lesson_id]
                lesson_title = demo_lesson['title']
                content = demo_lesson['content']
                student_logger.info(f"Demo lesson loaded: '{lesson_title}'")
                logger.info(f"Using demo lesson '{lesson_title}' for ID: {lesson_id}")
            else:
                student_logger.error(f"Lesson not found: {lesson_id}")
                return {'error': 'Lesson not found'}
        else:
            content = lesson.get('content') or lesson.get('summary')
            if not content:
                student_logger.error(f"No lesson content available for lesson {lesson_id}")
                return {'error': 'No lesson content available'}
            lesson_title = lesson.get('title', 'this lesson')
            student_logger.info(f"Lesson loaded: '{lesson_title}' (ID: {lesson_id})")
            logger.info(f"Answering question for lesson '{lesson_title}' (ID: {lesson_id})")
        
        student_logger.info(f"Lesson content length: {len(content)} characters")
        
        # Check if RAG should be used for large lessons
        if self.rag_service.should_use_rag(content):
            student_logger.info("Using RAG for large lesson content")
            
            # Create a document from the lesson content
            from langchain_core.documents import Document
            lesson_doc = Document(page_content=content, metadata={"lesson_id": lesson_id, "title": lesson_title})
            
            # Process with RAG
            rag_result = self.rag_service.process_document([lesson_doc], f"lesson_{lesson_id}")
            if 'error' in rag_result:
                student_logger.error(f"RAG processing failed: {rag_result['error']}")
                # Fallback to direct processing
                answer = self.llm_answer(content, question, lesson_title)
            else:
                # Retrieve relevant chunks
                relevant_chunks = self.rag_service.retrieve_relevant_chunks(question, k=3)
                if not relevant_chunks:
                    student_logger.warning("No relevant chunks found, using first few chunks")
                    relevant_chunks = self.rag_service.documents[:2]
                
                # Create RAG prompt
                rag_prompt = self.rag_service.create_rag_prompt(question, relevant_chunks)
                
                # Generate answer using RAG
                student_logger.info("Generating AI answer with RAG")
                answer = self.llm_answer_with_rag(rag_prompt, question, lesson_title)
        else:
            student_logger.info("Lesson content is small, using direct processing")
            # Use LLM to answer with lesson-specific context
            student_logger.info("Generating AI answer")
            answer = self.llm_answer(content, question, lesson_title)
        
        student_logger.info(f"AI answer generated - length: {len(answer)} characters")

        # Canonicalize the question and log to FAQ using semantic matching
        try:
            student_logger.info("Canonicalizing question")
            canonical = self.canonicalize_question(lesson_id, question)
            student_logger.info(f"Canonical question: {canonical}")
        except Exception as e:
            student_logger.warning(f"Question canonicalization failed: {str(e)}")
            canonical = question
        
        student_logger.info("Logging question to FAQ")
        LessonFAQ.log_question(lesson_id, canonical)
        student_logger.info("=== STUDENT QUESTION PROCESSING COMPLETED ===")
        
        return {'answer': answer, 'canonical_question': canonical}

    def llm_answer_with_rag(self, rag_prompt: str, question: str, lesson_title: str = "this lesson") -> str:
        """
        Generate answer using RAG prompt (for large documents)
        
        Args:
            rag_prompt: Pre-formatted prompt with retrieved context
            question: Original question
            lesson_title: Title of the lesson
            
        Returns:
            Generated answer
        """
        student_logger.info("=== LLM ANSWER GENERATION WITH RAG STARTED ===")
        student_logger.info(f"Lesson title: {lesson_title}")
        student_logger.info(f"Question: {question}")
        student_logger.info(f"RAG prompt length: {len(rag_prompt)} characters")
        
        try:
            # Use the RAG prompt directly with the LLM
            response = self.llm.invoke(rag_prompt)
            student_logger.info("LLM response received")
            
            # Extract content from AIMessage if needed
            if hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)
            
            student_logger.info(f"Response content length: {len(response_content)} characters")
            student_logger.info("=== LLM ANSWER GENERATION WITH RAG COMPLETED ===")
            return response_content
        except Exception as e:
            student_logger.error(f"Error in RAG answer generation: {str(e)}")
            return f"I apologize, but I encountered an error while processing your question: {str(e)}"

    def llm_answer(self, lesson_content: str, question: str, lesson_title: str = "this lesson") -> str:
        """Generate an answer using the LLM with lesson-specific context"""
        student_logger.info("=== LLM ANSWER GENERATION STARTED ===")
        student_logger.info(f"Lesson title: {lesson_title}")
        student_logger.info(f"Question: {question}")
        student_logger.info(f"Content length: {len(lesson_content)} characters")
        
        # Check if the question references specific lines
        line_references = self._extract_line_references(question)
        student_logger.info(f"Line references found: {line_references}")
        
        # Use Groq LLM (already implemented in the project)
        if line_references:
            student_logger.info("Formatting content with line numbers")
            # Format lesson content with line numbers for context
            numbered_content = self._format_content_with_line_numbers(lesson_content)
            prompt = f"""
You are a helpful teacher for the lesson titled "{lesson_title}". The student is asking about specific lines in the lesson content. Use the following numbered lesson content to answer their question concisely and clearly.

Lesson Title: {lesson_title}
Numbered Lesson Content:
{numbered_content}

Student's Question: {question}

The student is specifically asking about line(s): {', '.join(map(str, line_references))}

Answer as a helpful teacher, focusing on the specific lines mentioned and providing clear explanations for those lines. Base your answer entirely on the content provided in the lesson:
"""
        else:
            student_logger.info("Using standard content format")
            prompt = f"""
You are a helpful teacher for the lesson titled "{lesson_title}". Use the following lesson content to answer the student's question concisely and clearly. Make sure your response is specific to this lesson and its content.

Lesson Title: {lesson_title}
Lesson Content:
{lesson_content}

Student's Question: {question}

Answer as a helpful teacher, being specific to the "{lesson_title}" lesson content. Base your answer entirely on the content provided in the lesson above. If the question asks about something specific (like "what is magnet"), explain it thoroughly using the information from the lesson content:
"""
        try:
            student_logger.info("Invoking LLM for answer generation")
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                answer = response.content.strip()
            else:
                answer = str(response).strip()
            
            student_logger.info(f"LLM answer generated - length: {len(answer)} characters")
            student_logger.info("=== LLM ANSWER GENERATION COMPLETED ===")
            return answer
        except Exception as e:
            student_logger.error(f"LLM answer generation failed: {str(e)}")
            return f"[Error from LLM: {e}]"

    def _extract_line_references(self, question: str) -> List[int]:
        """Extract line references from a question like 'line 1', 'sentence 2', etc."""
        line_patterns = [
            r'line\s+(\d+)',
            r'sentence\s+(\d+)',
            r'paragraph\s+(\d+)',
            r'number\s+(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s+(?:line|sentence|paragraph)'
        ]
        
        references = []
        for pattern in line_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                line_number = int(match)
                if line_number > 0:
                    references.append(line_number)
        
        return references

    def _format_content_with_line_numbers(self, content: str) -> str:
        """Format lesson content with line numbers for AI context"""
        # Split content into paragraphs and sentences
        paragraphs = content.split('\n\n')
        numbered_content = ''
        line_number = 1
        
        for paragraph in paragraphs:
            if paragraph.strip():
                # Split paragraph into sentences
                sentences = re.split(r'[.!?]+', paragraph)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if len(sentences) > 1:
                    # Multiple sentences - number each sentence
                    for sentence in sentences:
                        if sentence:
                            numbered_content += f"{line_number}: {sentence}.\n"
                            line_number += 1
                else:
                    # Single sentence or short paragraph - number as one line
                    numbered_content += f"{line_number}: {paragraph.strip()}\n"
                    line_number += 1
                
                numbered_content += "\n"
        
        return numbered_content

    def canonicalize_question(self, lesson_id: int, question: str) -> str:
        """Return a canonical phrasing for the question using semantic similarity"""
        try:
            conn = sqlite3.connect('instance/chatbot.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS lesson_faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER,
                question TEXT,
                count INTEGER DEFAULT 1,
                canonical_question TEXT
            )''')
            c.execute('SELECT COALESCE(canonical_question, question) FROM lesson_faq WHERE lesson_id = ?', (lesson_id,))
            existing = [row[0] for row in c.fetchall() if row and row[0]]
            conn.close()

            if not existing:
                # No prior questions; generate a canonical phrasing
                return self._generate_canonical(question)

            # Embed existing and incoming question
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            existing_vectors = embeddings.embed_documents(existing)
            query_vector = embeddings.embed_query(question)

            # Compute cosine similarity
            def cosine(a, b):
                import math
                dot = sum(x*y for x, y in zip(a, b))
                na = math.sqrt(sum(x*x for x in a))
                nb = math.sqrt(sum(y*y for y in b))
                return (dot / (na * nb)) if na and nb else 0.0

            sims = [cosine(vec, query_vector) for vec in existing_vectors]
            best_idx, best_sim = (max(enumerate(sims), key=lambda t: t[1]) if sims else (-1, 0.0))

            # Threshold tuned for paraphrase equivalence for MiniLM embeddings
            if best_sim >= 0.82:
                return existing[best_idx]

            # Otherwise, produce a concise canonical phrasing
            return self._generate_canonical(question)
        except Exception:
            # On any error, fall back to original question
            return question

    def _generate_canonical(self, question: str) -> str:
        """Use the LLM to produce a short canonical phrasing for a question"""
        try:
            prompt = (
                "Rewrite the following student question into a short, neutral, canonical phrasing (max 12 words).\n"
                "Keep the meaning identical. Do not include quotes or extra commentary.\n\n"
                f"Question: {question}\n\nCanonical:"
            )
            response = self.llm.invoke(prompt)
            text = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            # Clean up extraneous punctuation/quotes
            text = text.strip('"\'\u201c\u201d ')
            return text or question
        except Exception:
            return question

    def get_lesson_faqs(self, lesson_id: int, limit: int = 5) -> List[Dict[str, str]]:
        """Get frequently asked questions for a lesson"""
        try:
            # Get lesson content from database
            lesson = LessonModel.get_lesson_by_id(lesson_id)
            if not lesson:
                return []
            
            lesson_content = lesson['content']
            
            # Generate FAQs using LLM
            faq_prompt = f"""
            Based on the following lesson content, generate {limit} frequently asked questions that students might have.
            Focus on key concepts, common misconceptions, and important details.
            
            Lesson Content:
            {lesson_content}
            
            Return the questions in this JSON format:
            {{
                "faqs": [
                    {{
                        "question": "What is...?",
                        "answer": "The answer is..."
                    }}
                ]
            }}
            """
            
            response = self.llm.invoke(faq_prompt)
            response_text = response.content
            
            # Parse JSON response
            try:
                import json
                faq_data = json.loads(response_text)
                return faq_data.get('faqs', [])
            except json.JSONDecodeError:
                logger.error(f"Failed to parse FAQ JSON: {response_text}")
                return []
                
        except Exception as e:
            logger.error(f"Error generating FAQs: {str(e)}")
            return []

    def get_lesson_summary(self, lesson_id: int) -> Dict[str, str]:
        """Get a summary of the lesson for students"""
        try:
            lesson = LessonModel.get_lesson_by_id(lesson_id)
            if not lesson:
                return {'error': 'Lesson not found'}
            
            content = lesson.get('content') or lesson.get('summary')
            if not content:
                return {'error': 'No lesson content available'}
            
            title = lesson.get('title', 'Lesson')
            
            # Generate a student-friendly summary
            summary_prompt = f"""
            Create a student-friendly summary of this lesson. Make it engaging and easy to understand.
            
            Lesson Title: {title}
            Lesson Content: {content}
            
            Provide a brief summary (2-3 sentences) that explains what students will learn in this lesson.
            """
            
            response = self.llm.invoke(summary_prompt)
            summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            return {
                'title': title,
                'summary': summary,
                'content': content
            }
            
        except Exception as e:
            logger.error(f"Error generating lesson summary: {str(e)}")
            return {'error': 'Failed to generate summary'}

    def get_lesson_key_points(self, lesson_id: int) -> List[str]:
        """Extract key learning points from a lesson"""
        try:
            lesson = LessonModel.get_lesson_by_id(lesson_id)
            if not lesson:
                return []
            
            content = lesson.get('content') or lesson.get('summary')
            if not content:
                return []
            
            # Generate key points using LLM
            key_points_prompt = f"""
            Extract the 5 most important key learning points from this lesson content.
            Make them clear and concise for students.
            
            Lesson Content: {content}
            
            Return as a simple list, one point per line:
            """
            
            response = self.llm.invoke(key_points_prompt)
            key_points_text = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            # Split into list
            key_points = [point.strip() for point in key_points_text.split('\n') if point.strip()]
            return key_points[:5]  # Limit to 5 points
            
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}")
            return []
