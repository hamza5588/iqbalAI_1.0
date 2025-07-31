# import os
# import logging
# from typing import Any, Dict, List, Optional
# from werkzeug.datastructures import FileStorage
# from werkzeug.utils import secure_filename
# from langchain_core.documents import Document
# from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
# from langchain_groq import ChatGroq
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from docx import Document as DocxDocument
# from docx.shared import Inches
# from io import BytesIO
# import tempfile
# import json

# # Set up logging
# logger = logging.getLogger(__name__)

# class LessonService:
#     def __init__(self, api_key: Optional[str] = None):
#         """
#         Initialize the LessonService with API key.
#         Falls back to GROQ_API_KEY environment variable if not provided.
#         """
#         self.api_key = api_key or os.getenv("GROQ_API_KEY")
#         if not self.api_key:
#             raise ValueError("API key is required. Please provide api_key parameter or set GROQ_API_KEY environment variable.")
        
#         try:
#             self.llm = ChatGroq(
#                 api_key=self.api_key,
#                 model="llama3-70b-8192",
#                 temperature=0.3,
#                 max_tokens=2048
#             )
#         except Exception as e:
#             logger.error(f"Failed to initialize ChatGroq: {str(e)}")
#             raise ValueError(f"Failed to initialize AI model: {str(e)}")

#         self.lesson_prompt = ChatPromptTemplate.from_template("""
# You are an expert teacher. Given the following educational document, create a comprehensive lesson plan.

# Document Content:
# {text}

# Create a detailed lesson plan in the following strict JSON format ONLY. Do not include any additional text or explanations outside the JSON structure:

# {{
#     "title": "Clear and descriptive lesson title",
#     "summary": "Brief 2-3 sentence summary of the lesson",
#     "learning_objectives": [
#         "Specific learning objective 1",
#         "Specific learning objective 2",
#         "Specific learning objective 3"
#     ],
#     "sections": [
#         {{
#             "heading": "Section heading",
#             "content": "Detailed explanation with examples and key concepts"
#         }}
#     ],
#     "key_concepts": [
#         "Important concept 1",
#         "Important concept 2",
#         "Important concept 3"
#     ],
#     "activities": [
#         {{
#             "name": "Activity name",
#             "description": "How to perform the activity",
#             "duration": "Estimated time"
#         }}
#     ],
#     "quiz": [
#         {{
#             "question": "Multiple choice question",
#             "options": ["Option A", "Option B", "Option C", "Option D"],
#             "answer": "Correct option letter (A, B, C, or D)",
#             "explanation": "Brief explanation of why this is correct"
#         }}
#     ]
# }}

# IMPORTANT: Your response must be valid JSON only, with no additional text before or after the JSON structure.
# """)

#         self.parser = JsonOutputParser()

#     def allowed_file(self, filename: str) -> bool:
#         """Check if file extension is supported"""
#         if not filename:
#             return False
#         ext = filename.split(".")[-1].lower()
#         return ext in ["pdf", "doc", "docx", "txt"]

#     def process_file(self, file: FileStorage) -> Dict[str, Any]:
#         """
#         Process an uploaded file and return structured lesson content with DOCX bytes.
        
#         Args:
#             file: Uploaded file to process
            
#         Returns:
#             Dictionary containing lesson content, DOCX bytes, and filename
#         """
#         temp_path = None
        
#         try:
#             if not file or not file.filename:
#                 return {"error": "No file provided"}
            
#             if not self.allowed_file(file.filename):
#                 return {"error": "File type not supported. Please upload PDF, DOC, DOCX, or TXT files."}
            
#             # Create temporary file
#             with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}") as temp_file:
#                 temp_path = temp_file.name
#                 file.save(temp_path)
            
#             # Load and process the document
#             documents = self._load_document(temp_path, file.filename)
            
#             if not documents:
#                 return {"error": "Could not extract content from the file"}
            
#             # Combine all document content
#             full_text = "\n".join([doc.page_content for doc in documents])
            
#             if not full_text.strip():
#                 return {"error": "No readable content found in the file"}
            
#             # Generate structured lesson
#             lesson_data = self._generate_structured_lesson(full_text)
            
#             if 'error' in lesson_data:
#                 return lesson_data
            
#             # Create DOCX file
#             docx_bytes = self._create_docx(lesson_data)
            
#             # Generate filename
#             base_name = os.path.splitext(file.filename)[0]
#             filename = f"lesson_{base_name}.docx"
            
#             return {
#                 "lesson": lesson_data,
#                 "docx_bytes": docx_bytes,
#                 "filename": filename
#             }

#         except Exception as e:
#             logger.error(f"Error processing file: {str(e)}", exc_info=True)
#             return {
#                 "error": "Failed to process file",
#                 "details": str(e)
#             }
        
#         finally:
#             # Clean up temporary file
#             if temp_path and os.path.exists(temp_path):
#                 try:
#                     os.remove(temp_path)
#                 except Exception as e:
#                     logger.warning(f"Could not remove temporary file {temp_path}: {str(e)}")

#     def _load_document(self, path: str, filename: str) -> List[Document]:
#         """Load document based on file extension"""
#         ext = filename.split(".")[-1].lower()
        
#         try:
#             if ext == "pdf":
#                 loader = PyMuPDFLoader(path)
#                 docs = loader.load()
                
#                 # Check if we got meaningful content
#                 if not docs or not any(doc.page_content.strip() for doc in docs):
#                     # Try alternative PDF reading if needed
#                     try:
#                         from pypdf import PdfReader
#                         reader = PdfReader(path)
#                         text = ""
#                         for page in reader.pages:
#                             text += page.extract_text() + "\n\n"
#                         if text.strip():
#                             return [Document(page_content=text)]
#                     except Exception:
#                         pass
                
#                 return docs
                
#             elif ext in ["doc", "docx"]:
#                 loader = UnstructuredWordDocumentLoader(path)
#                 return loader.load()
                
#             elif ext == "txt":
#                 loader = TextLoader(path, encoding='utf-8')
#                 return loader.load()
                
#             else:
#                 raise ValueError(f"Unsupported file format: .{ext}")
                
#         except Exception as e:
#             logger.error(f"Error loading document {filename}: {str(e)}")
#             raise ValueError(f"Failed to load document: {str(e)}")

#     def _generate_structured_lesson(self, text: str) -> Dict[str, Any]:
#         """Generate structured lesson from text content"""
#         try:
#             # Truncate text if too long to avoid token limits
#             max_chars = 10000  # Adjust based on your needs
#             if len(text) > max_chars:
#                 text = text[:max_chars] + "..."
#                 logger.info(f"Text truncated to {max_chars} characters")
            
#             chain = self.lesson_prompt | self.llm | self.parser
#             logger.info("Invoking LLM for structured lesson generation...")
#             result = chain.invoke({"text": text})
#             logger.info("Received LLM response.")
            
#             # If we get a string response (which might contain JSON), try to extract JSON
#             if isinstance(result, str):
#                 try:
#                     # Try to find JSON in the string
#                     json_start = result.find('{')
#                     json_end = result.rfind('}') + 1
#                     if json_start != -1 and json_end != -1:
#                         result = json.loads(result[json_start:json_end])
#                 except json.JSONDecodeError as e:
#                     logger.error(f"Failed to parse JSON from string: {str(e)}")
#                     return {
#                         "error": "Failed to parse lesson content",
#                         "details": str(e)
#                     }
            
#             # Validate the result structure
#             if not isinstance(result, dict):
#                 return {"error": "Invalid response format from AI model"}
            
#             # Ensure required fields exist
#             required_fields = ["title", "summary", "sections"]
#             for field in required_fields:
#                 if field not in result:
#                     result[field] = f"Generated {field}"
            
#             return result
            
#         except Exception as e:
#             logger.error(f"Error generating lesson: {str(e)}")
#             return {
#                 "error": "Failed to generate lesson",
#                 "details": str(e)
#             }

#     def _create_docx(self, lesson_data: Dict[str, Any]) -> bytes:
#         """Convert structured lesson to DOCX format with improved formatting"""
#         try:
#             doc = DocxDocument()
            
#             # Add title with formatting
#             title = doc.add_heading(level=1)
#             title_run = title.add_run(lesson_data.get("title", "Generated Lesson"))
#             title_run.bold = True
#             title_run.font.size = Inches(0.5)
            
#             # Add summary section
#             if lesson_data.get("summary"):
#                 doc.add_heading("Summary", level=2)
#                 summary = doc.add_paragraph(lesson_data["summary"])
#                 summary.paragraph_format.space_after = Inches(0.1)
            
#             # Add learning objectives with bullet points
#             if lesson_data.get("learning_objectives"):
#                 doc.add_heading("Learning Objectives", level=2)
#                 for objective in lesson_data["learning_objectives"]:
#                     p = doc.add_paragraph(style='ListBullet')
#                     p.add_run(objective)
#                 doc.add_paragraph()
            
#             # Add sections with proper spacing
#             if lesson_data.get("sections"):
#                 for section in lesson_data["sections"]:
#                     doc.add_heading(section.get("heading", "Section"), level=2)
#                     content = doc.add_paragraph(section.get("content", ""))
#                     content.paragraph_format.space_after = Inches(0.1)
#                     doc.add_paragraph()
            
#             # Add key concepts
#             if lesson_data.get("key_concepts"):
#                 doc.add_heading("Key Concepts", level=2)
#                 for concept in lesson_data["key_concepts"]:
#                     p = doc.add_paragraph(style='ListBullet')
#                     p.add_run(concept)
#                 doc.add_paragraph()
            
#             # Add activities with clear formatting
#             if lesson_data.get("activities"):
#                 doc.add_heading("Activities", level=2)
#                 for i, activity in enumerate(lesson_data["activities"], 1):
#                     activity_title = doc.add_heading(level=3)
#                     activity_title.add_run(f"Activity {i}: {activity.get('name', 'Unnamed Activity')}").bold = True
                    
#                     desc = doc.add_paragraph()
#                     desc.add_run("Description: ").bold = True
#                     desc.add_run(activity.get('description', ''))
                    
#                     if activity.get('duration'):
#                         duration = doc.add_paragraph()
#                         duration.add_run("Duration: ").bold = True
#                         duration.add_run(activity['duration'])
                    
#                     doc.add_paragraph()
            
#             # Add quiz with clear question/answer formatting
#             if lesson_data.get("quiz"):
#                 doc.add_heading("Quiz", level=2)
#                 for i, question in enumerate(lesson_data["quiz"], 1):
#                     q = doc.add_paragraph()
#                     q.add_run(f"Question {i}: ").bold = True
#                     q.add_run(question.get('question', ''))
                    
#                     # Add options with letters
#                     options = ['A', 'B', 'C', 'D']
#                     for opt, text in zip(options, question.get("options", [])):
#                         p = doc.add_paragraph(style='ListBullet')
#                         p.add_run(f"{opt}. {text}")
                    
#                     # Add answer
#                     ans = doc.add_paragraph()
#                     ans.add_run("Correct Answer: ").bold = True
#                     ans.add_run(question.get('answer', ''))
                    
#                     if question.get('explanation'):
#                         exp = doc.add_paragraph()
#                         exp.add_run("Explanation: ").bold = True
#                         exp.add_run(question['explanation'])
                    
#                     doc.add_paragraph()
            
#             # Save to bytes buffer
#             buffer = BytesIO()
#             doc.save(buffer)
#             buffer.seek(0)
#             return buffer.getvalue()
            
#         except Exception as e:
#             logger.error(f"Error creating DOCX: {str(e)}")
#             # Return a simple DOCX with error message
#             doc = DocxDocument()
#             doc.add_heading("Lesson Generation Error", level=1)
#             doc.add_paragraph(f"An error occurred while generating the lesson: {str(e)}")
#             buffer = BytesIO()
#             doc.save(buffer)
#             buffer.seek(0)
#             return buffer.getvalue()







import os
import logging
from typing import Any, Dict, List, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from docx import Document as DocxDocument
from langchain_nomic import NomicEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from docx.shared import Inches
from io import BytesIO
import tempfile
import json
import re
from app.models.models import LessonFAQ, LessonModel

# Set up logging
logger = logging.getLogger(__name__)

class LessonService:
    """
    LessonService handles the teacher-focused lesson generation workflow:
    1. Teacher selects 'Generate Lesson' from the sidebar.
    2. Uploads a PDF file (e.g., textbook, handout).
    3. Teacher enters details about the lesson plan to be generated (title, objectives, focus areas, etc.).
    4. iqbalAI processes the file and user inputs, generates a structured lesson plan.
    5. Teacher can review, ask follow-up questions, edit/refine lesson parts.
    6. After final screening and edits, the final document is ready.
    7. User/teacher can download the final version.
    """
    def __init__(self, api_key: str):
        """
        Initialize the LessonService with API key from database.
        API key is required and must be provided.
        """
        if not api_key:
            raise ValueError("API key is required. Please provide api_key parameter from database.")
        
        self.api_key = api_key
        
        try:
            self.llm = ChatGroq(
                api_key=api_key,
                model="llama3-70b-8192",
                temperature=0.3,
                # max_tokens=4096  # Increased token limit
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq: {str(e)}")
            raise ValueError(f"Failed to initialize AI model: {str(e)}")

        # FIXED: Improved prompt with clearer instructions
        self.lesson_prompt = ChatPromptTemplate.from_template("""
You are an expert teacher. Create a comprehensive lesson plan from the following document content.

Document Content:
{text}

CRITICAL: You must respond with ONLY a valid JSON object. Do not include any text before or after the JSON.

Return this exact JSON structure:

{{
    "title": "Clear and descriptive lesson title",
    "summary": "Brief 2-3 sentence summary of the lesson",
    "learning_objectives": [
        "Specific learning objective 1",
        "Specific learning objective 2",
        "Specific learning objective 3"
    ],
    "sections": [
        {{
            "heading": "Introduction (use a clear, bolded heading)",
            "content": "Detailed explanation with examples and key concepts"
        }},
        {{
            "heading": "Main Content (use a clear, bolded heading)",
            "content": "Core lesson material with detailed explanations"
        }},
        {{
            "heading": "Conclusion (use a clear, bolded heading)",
            "content": "Summary and key takeaways"
        }}
    ],
    "key_concepts": [
        "Important concept 1",
        "Important concept 2",
        "Important concept 3"
    ],
    "activities": [
        {{
            "name": "Activity name",
            "description": "How to perform the activity",
            "duration": "15 minutes"
        }}
    ],
    "quiz": [
        {{
            "question": "Multiple choice question",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "A",
            "explanation": "Brief explanation of why this is correct"
        }}
    ]
}}

IMPORTANT:
- Return ONLY the JSON object
- No markdown code blocks
- No additional text or explanations
- Ensure all JSON strings are properly escaped
- Answer field must be only "A", "B", "C", or "D"
- **All section headings must be clear, bold, and numbered (e.g., '1. Introduction', '2. Main Content', '3. Conclusion')**
- Do NOT omit any section headings. Every section must have a heading.
""")

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is supported"""
        if not filename:
            return False
        ext = filename.split(".")[-1].lower()
        return ext in ["pdf", "doc", "docx", "txt"]

    def process_file(self, file: FileStorage, lesson_details: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process an uploaded file and return structured lesson content with DOCX bytes.
        Accepts additional lesson details (title, objectives, focus areas, etc.) for teacher-focused workflow.
        Args:
            file: Uploaded file to process
            lesson_details: Optional dictionary with lesson plan details (title, objectives, etc.)
        Returns:
            Dictionary containing lesson content, DOCX bytes, and filename
        """
        temp_path = None
        try:
            if not file or not file.filename:
                return {"error": "No file provided"}
            if not self.allowed_file(file.filename):
                return {"error": "File type not supported. Please upload PDF, DOC, DOCX, or TXT files."}
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}") as temp_file:
                temp_path = temp_file.name
                file.save(temp_path)
            documents = self._load_document(temp_path, file.filename)
            if not documents:
                return {"error": "Could not extract content from the file"}
            full_text = "\n".join([doc.page_content for doc in documents])
            if not full_text.strip():
                return {"error": "No readable content found in the file"}
            # Merge lesson_details into prompt if provided
            lesson_data = self._generate_structured_lesson(full_text, lesson_details)
            if 'error' in lesson_data:
                return lesson_data
            docx_bytes = self._create_docx(lesson_data)
            base_name = os.path.splitext(file.filename)[0]
            filename = f"lesson_{base_name}.docx"
            return {
                "lesson": lesson_data,
                "docx_bytes": docx_bytes,
                "filename": filename
            }
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return {
                "error": "Failed to process file",
                "details": str(e)
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {temp_path}: {str(e)}")

    def _load_document(self, path: str, filename: str) -> List[Document]:
        """Load document based on file extension"""
        ext = filename.split(".")[-1].lower()
        
        try:
            if ext == "pdf":
                loader = PyMuPDFLoader(path)
                docs = loader.load()
                
                # Check if we got meaningful content
                if not docs or not any(doc.page_content.strip() for doc in docs):
                    # Try alternative PDF reading if needed
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(path)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n\n"
                        if text.strip():
                            return [Document(page_content=text)]
                    except Exception:
                        pass
                
                return docs
                
            elif ext in ["doc", "docx"]:
                loader = UnstructuredWordDocumentLoader(path)
                return loader.load()
                
            elif ext == "txt":
                loader = TextLoader(path, encoding='utf-8')
                return loader.load()
                
            else:
                raise ValueError(f"Unsupported file format: .{ext}")
                
        except Exception as e:
            logger.error(f"Error loading document {filename}: {str(e)}")
            raise ValueError(f"Failed to load document: {str(e)}")

    def _generate_structured_lesson(self, text: str, lesson_details: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate structured lesson from text content and optional teacher-provided lesson details.
        """
        try:
            # Remove or greatly increase character limit for detailed lessons
            max_chars = 1000000  # Effectively no truncation
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
                logger.info(f"Text truncated to {max_chars} characters")
            logger.info(f"Processing text of length: {len(text)}")
            logger.info("About to invoke LLM...")
            # Compose prompt with lesson_details if provided
            prompt_text = text
            if lesson_details:
                details_str = "\n".join([f"{k}: {v}" for k, v in lesson_details.items() if v])
                prompt_text = f"Lesson Details Provided by Teacher:\n{details_str}\n\nDocument Content:\n{text}"
            response = self.llm.invoke(self.lesson_prompt.format(text=prompt_text))
            logger.info(f"Received LLM response type: {type(response)}")
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            logger.info(f"Response text (first 200 chars): {response_text[:200]}")
            lesson_data = self._extract_and_parse_json(response_text)
            if not lesson_data:
                logger.error("Failed to extract valid JSON from response")
                return self._create_fallback_lesson(text)
            lesson_data = self._validate_and_fix_lesson(lesson_data)
            logger.info("Successfully generated structured lesson")
            return lesson_data
        except Exception as e:
            logger.error(f"Error generating lesson: {str(e)}", exc_info=True)
            return self._create_fallback_lesson(text)

    def _extract_and_parse_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM response with multiple strategies"""
        
        # Strategy 1: Try to parse the entire response as JSON
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Look for JSON within the response
        try:
            # Find the first { and last }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = response_text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Remove markdown code blocks if present
        try:
            # Remove ```json and ``` markers
            cleaned = re.sub(r'```json\s*\n?', '', response_text)
            cleaned = re.sub(r'\n?\s*```', '', cleaned)
            
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = cleaned[start_idx:end_idx + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Strategy 4: Try to fix common JSON issues
        try:
            # Fix common issues like trailing commas, single quotes, etc.
            fixed_json = self._fix_common_json_issues(response_text)
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            pass
        
        logger.error("All JSON parsing strategies failed")
        return None

    def _fix_common_json_issues(self, text: str) -> str:
        """Fix common JSON formatting issues"""
        # Extract JSON part
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx == -1 or end_idx == -1:
            return text
            
        json_part = text[start_idx:end_idx + 1]
        
        # Fix trailing commas
        json_part = re.sub(r',\s*}', '}', json_part)
        json_part = re.sub(r',\s*]', ']', json_part)
        
        # Fix single quotes to double quotes (but be careful with apostrophes)
        json_part = re.sub(r"'([^']*)':", r'"\1":', json_part)
        
        return json_part

    def _validate_and_fix_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix lesson structure"""
        # Ensure required fields exist with defaults
        default_lesson = {
            "title": "Generated Lesson",
            "summary": "A comprehensive lesson based on the provided content.",
            "learning_objectives": [
                "Understand the main concepts",
                "Apply the knowledge learned",
                "Analyze the key points"
            ],
            "sections": [
                {
                    "heading": "Introduction",
                    "content": "This lesson covers the key concepts from the provided material."
                },
                {
                    "heading": "Main Content",
                    "content": "The core material and important points are discussed here."
                },
                {
                    "heading": "Conclusion",
                    "content": "Summary of the key takeaways and next steps."
                }
            ],
            "key_concepts": [
                "Key concept 1",
                "Key concept 2",
                "Key concept 3"
            ],
            "activities": [
                {
                    "name": "Discussion Activity",
                    "description": "Discuss the main points with peers",
                    "duration": "15 minutes"
                }
            ],
            "quiz": [
                {
                    "question": "What is the main topic of this lesson?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "A",
                    "explanation": "This covers the primary subject matter."
                }
            ]
        }
        
        # Merge with defaults
        for key, default_value in default_lesson.items():
            if key not in lesson_data or not lesson_data[key]:
                lesson_data[key] = default_value
        
        # Validate sections structure
        if not isinstance(lesson_data.get("sections"), list):
            lesson_data["sections"] = default_lesson["sections"]
        else:
            for section in lesson_data["sections"]:
                if not isinstance(section, dict):
                    continue
                if "heading" not in section:
                    section["heading"] = "Section"
                if "content" not in section:
                    section["content"] = "Content for this section."
        
        # Validate quiz structure
        if not isinstance(lesson_data.get("quiz"), list):
            lesson_data["quiz"] = default_lesson["quiz"]
        else:
            for question in lesson_data["quiz"]:
                if not isinstance(question, dict):
                    continue
                if "question" not in question:
                    question["question"] = "Sample question"
                if "options" not in question or len(question["options"]) < 4:
                    question["options"] = ["Option A", "Option B", "Option C", "Option D"]
                if "answer" not in question or question["answer"] not in ["A", "B", "C", "D"]:
                    question["answer"] = "A"
                if "explanation" not in question:
                    question["explanation"] = "Explanation for the answer."
        
        return lesson_data

    def _create_fallback_lesson(self, text: str) -> Dict[str, Any]:
        """Create a basic lesson structure when AI generation fails"""
        
        # Extract first few sentences for summary
        sentences = text.split('.')[:3]
        summary = '. '.join(sentences).strip()
        if not summary:
            summary = "A lesson based on the provided content."
        
        # Create basic lesson structure
        return {
            "title": "Generated Lesson",
            "summary": summary,
            "learning_objectives": [
                "Understand the main concepts from the material",
                "Identify key points and themes",
                "Apply the knowledge in practical contexts"
            ],
            "sections": [
                {
                    "heading": "Introduction",
                    "content": "This lesson is based on the provided material and covers the essential concepts and ideas presented."
                },
                {
                    "heading": "Main Content",
                    "content": text[:1000] + "..." if len(text) > 1000 else text
                },
                {
                    "heading": "Key Takeaways",
                    "content": "The main points and conclusions from this material provide valuable insights for understanding the topic."
                }
            ],
            "key_concepts": [
                "Primary topic concepts",
                "Supporting ideas and details",
                "Practical applications"
            ],
            "activities": [
                {
                    "name": "Content Review",
                    "description": "Review and discuss the main points covered in this lesson",
                    "duration": "20 minutes"
                }
            ],
            "quiz": [
                {
                    "question": "What is the main focus of this lesson content?",
                    "options": [
                        "Understanding core concepts",
                        "Memorizing details",
                        "Completing exercises",
                        "Reading additional material"
                    ],
                    "answer": "A",
                    "explanation": "The lesson focuses on understanding the core concepts presented in the material."
                }
            ]
        }

    def _sanitize_heading(self, heading: str) -> str:
        """Remove or replace newlines from heading values for docx compatibility."""
        if not isinstance(heading, str):
            heading = str(heading)
        return heading.replace('\n', ' ').replace('\r', ' ').strip()

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
            
            # Add activities with clear formatting
            if lesson_data.get("activities"):
                doc.add_heading(self._sanitize_heading("Activities"), level=2)
                for i, activity in enumerate(lesson_data["activities"], 1):
                    activity_title = doc.add_heading(level=3)
                    activity_title.add_run(self._sanitize_heading(f"Activity {i}: {activity.get('name', 'Unnamed Activity')}")) .bold = True
                    
                    desc = doc.add_paragraph()
                    desc.add_run("Description: ").bold = True
                    desc.add_run(str(activity.get('description', '')))
                    
                    if activity.get('duration'):
                        duration = doc.add_paragraph()
                        duration.add_run("Duration: ").bold = True
                        duration.add_run(str(activity['duration']))
                    
                    doc.add_paragraph()
            
            # Add quiz with clear question/answer formatting
            if lesson_data.get("quiz"):
                doc.add_heading(self._sanitize_heading("Quiz"), level=2)
                for i, question in enumerate(lesson_data["quiz"], 1):
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

    def edit_lesson_with_prompt(self, lesson_text: str, user_prompt: str) -> str:
        """
        Use a FAISS vector database for semantic chunk retrieval and editing.
        Chunks the lesson, stores in FAISS, retrieves relevant chunks for the prompt, edits them, and reconstructs the lesson.
        """
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
            # nomic embeddings
          

            # embeddings = NomicEmbeddings(
            #     model="nomic-embed-text-v1.5",
            #     # api_key="nk-7Ad201NonNkEv_pYdRwb-EkNjf84mVLW205ihoE7RyU"
       
            # )
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
                        f"You are an expert teacher assistant. Here is a lesson chunk in markdown:\n\n"
                        f"{text}\n\n"
                        f"User request: {user_prompt}\n\n"
                        f"Please return the revised lesson chunk in markdown only."
                    )
                    response = self.llm.invoke(edit_prompt)
                    edited = response.content if hasattr(response, 'content') else str(response)
                    edited_chunks[text] = edited

                # 5. Replace original chunks with edited ones
                new_chunks = [edited_chunks.get(chunk, chunk) for chunk in chunks]

                # 6. (FAISS index is deleted automatically with TemporaryDirectory)

            # 7. Reconstruct and return the lesson
            return '\n\n'.join(new_chunks)
        except Exception as e:
            logger.error(f"Error editing lesson with prompt: {str(e)}", exc_info=True)
            return lesson_text

    def create_ppt(self, lesson_data: dict) -> bytes:
        """
        Generate a basic PPTX file from the lesson structure using python-pptx.
        """
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
            
            # Sections
            sections = lesson_data.get('sections', [])
            if sections:
                logger.info(f"Creating {len(sections)} section slides")
                for section in sections:
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = section.get('heading', 'Section')
                    body = slide.shapes.placeholders[1].text_frame
                    content = section.get('content', '')
                    # Limit content to avoid slide overflow
                    if len(content) > 1000:
                        content = content[:1000] + "..."
                    body.text = content
            else:
                # If no sections, create a content slide with the main content
                if lesson_data.get('content'):
                    logger.info("Creating content slide with main lesson content")
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = 'Lesson Content'
                    body = slide.shapes.placeholders[1].text_frame
                    content = lesson_data['content']
                    # Split long content into multiple slides if needed
                    if len(content) > 1000:
                        # Create multiple slides for long content
                        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                        logger.info(f"Splitting content into {len(chunks)} slides")
                        for i, chunk in enumerate(chunks):
                            if i > 0:  # First chunk already added above
                                slide = prs.slides.add_slide(prs.slide_layouts[1])
                                slide.shapes.title.text = f'Lesson Content (Continued {i+1})'
                                body = slide.shapes.placeholders[1].text_frame
                            body.text = chunk
                    else:
                        body.text = content
            
            # Key Concepts
            if lesson_data.get('key_concepts'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Key Concepts'
                body = slide.shapes.placeholders[1].text_frame
                for kc in lesson_data['key_concepts']:
                    body.add_paragraph().text = str(kc)
            
            # Activities
            if lesson_data.get('activities'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Activities'
                body = slide.shapes.placeholders[1].text_frame
                for act in lesson_data['activities']:
                    body.add_paragraph().text = f"{act.get('name', '')}: {act.get('description', '')} ({act.get('duration', '')})"
            
            # Quiz
            if lesson_data.get('quiz'):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Quiz'
                body = slide.shapes.placeholders[1].text_frame
                for q in lesson_data['quiz']:
                    body.add_paragraph().text = f"Q: {q.get('question', '')}"
                    for i, opt in enumerate(q.get('options', [])):
                        body.add_paragraph().text = f"{chr(65+i)}. {opt}"
                    body.add_paragraph().text = f"Answer: {q.get('answer', '')}"
            
            # If we only have a title slide, add a content slide
            if len(prs.slides) == 1 and lesson_data.get('content'):
                logger.info("Adding content slide as only title slide exists")
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = 'Lesson Content'
                body = slide.shapes.placeholders[1].text_frame
                content = lesson_data['content']
                if len(content) > 1000:
                    content = content[:1000] + "..."
                body.text = content
            
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

    def answer_lesson_question(self, lesson_id, question):
        # Get lesson content
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            return {'error': 'Lesson not found'}
        content = lesson.get('content') or lesson.get('summary')
        if not content:
            return {'error': 'No lesson content available'}
        # Use LLM to answer
        answer = self.llm_answer(content, question)
        # Log the question
        LessonFAQ.log_question(lesson_id, question)
        return {'answer': answer}

    def llm_answer(self, lesson_content, question):
        # Use Groq LLM (already implemented in the project)
        prompt = f"""
You are a helpful teacher. Use the following lesson content to answer the student's question concisely and clearly.

Lesson Content:
{lesson_content}

Question: {question}
Answer as a helpful teacher:
"""
        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content.strip()
            else:
                return str(response).strip()
        except Exception as e:
            return f"[Error from LLM: {e}]"

    def get_lesson_faqs(self, lesson_id, limit=5):
        """Get frequently asked questions for a lesson"""
        try:
            # Get lesson content from database
            from app.models.models import LessonModel
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

    def improve_lesson_content(self, lesson_id: int, current_content: str, improvement_prompt: str = "") -> str:
        """
        Improve lesson content using AI based on user prompt
        
        Args:
            lesson_id: ID of the lesson to improve
            current_content: Current lesson content
            improvement_prompt: User's specific improvement request
            
        Returns:
            str: Improved lesson content
        """
        try:
            # Create improvement prompt
            if improvement_prompt:
                prompt = f"""
                You are an expert teacher. Please improve the following lesson content based on the user's specific request.
                
                User's Improvement Request:
                {improvement_prompt}
                
                Current Lesson Content:
                {current_content}
                
                Please provide an improved version of the lesson content that addresses the user's request.
                Maintain the same structure and format, but enhance the content according to the improvement request.
                Return only the improved content, no additional explanations.
                """
            else:
                prompt = f"""
                You are an expert teacher. Please improve the following lesson content to make it more engaging, 
                comprehensive, and effective for students.
                
                Current Lesson Content:
                {current_content}
                
                Please provide an improved version that:
                1. Enhances clarity and readability
                2. Adds more examples and explanations where needed
                3. Improves the overall educational value
                4. Maintains the same structure and format
                
                Return only the improved content, no additional explanations.
                """
            
            # Generate improved content using LLM
            response = self.llm.invoke(prompt)
            improved_content = response.content.strip()
            
            logger.info(f"Successfully improved lesson {lesson_id} content")
            return improved_content
            
        except Exception as e:
            logger.error(f"Error improving lesson content: {str(e)}")
            # Return original content if improvement fails
            return current_content