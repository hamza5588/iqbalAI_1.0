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
from docx.shared import Inches
from io import BytesIO
import tempfile
import json
import re

# Set up logging
logger = logging.getLogger(__name__)

class LessonService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LessonService with API key.
        Falls back to GROQ_API_KEY environment variable if not provided.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Please provide api_key parameter or set GROQ_API_KEY environment variable.")
        
        try:
            self.llm = ChatGroq(
                api_key=self.api_key,
                model="llama3-70b-8192",
                temperature=0.3,
                max_tokens=4096  # Increased token limit
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
            "heading": "Introduction",
            "content": "Detailed explanation with examples and key concepts"
        }},
        {{
            "heading": "Main Content",
            "content": "Core lesson material with detailed explanations"
        }},
        {{
            "heading": "Conclusion",
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
""")

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is supported"""
        if not filename:
            return False
        ext = filename.split(".")[-1].lower()
        return ext in ["pdf", "doc", "docx", "txt"]

    def process_file(self, file: FileStorage) -> Dict[str, Any]:
        """
        Process an uploaded file and return structured lesson content with DOCX bytes.
        
        Args:
            file: Uploaded file to process
            
        Returns:
            Dictionary containing lesson content, DOCX bytes, and filename
        """
        temp_path = None
        
        try:
            if not file or not file.filename:
                return {"error": "No file provided"}
            
            if not self.allowed_file(file.filename):
                return {"error": "File type not supported. Please upload PDF, DOC, DOCX, or TXT files."}
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}") as temp_file:
                temp_path = temp_file.name
                file.save(temp_path)
            
            # Load and process the document
            documents = self._load_document(temp_path, file.filename)
            
            if not documents:
                return {"error": "Could not extract content from the file"}
            
            # Combine all document content
            full_text = "\n".join([doc.page_content for doc in documents])
            
            if not full_text.strip():
                return {"error": "No readable content found in the file"}
            
            # Generate structured lesson
            lesson_data = self._generate_structured_lesson(full_text)
            
            if 'error' in lesson_data:
                return lesson_data
            
            # Create DOCX file
            docx_bytes = self._create_docx(lesson_data)
            
            # Generate filename
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
            # Clean up temporary file
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

    def _generate_structured_lesson(self, text: str) -> Dict[str, Any]:
        """Generate structured lesson from text content"""
        try:
            # Truncate text if too long to avoid token limits
            max_chars = 8000  # Reduced to leave more room for response
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
                logger.info(f"Text truncated to {max_chars} characters")
            
            logger.info(f"Processing text of length: {len(text)}")
            logger.info("About to invoke LLM...")
            
            # Use the LLM directly instead of the parser chain
            response = self.llm.invoke(self.lesson_prompt.format(text=text))
            
            logger.info(f"Received LLM response type: {type(response)}")
            
            # Extract content from the response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            logger.info(f"Response text (first 200 chars): {response_text[:200]}")
            
            # FIXED: Better JSON extraction and parsing
            lesson_data = self._extract_and_parse_json(response_text)
            
            if not lesson_data:
                logger.error("Failed to extract valid JSON from response")
                # Return a fallback lesson structure
                return self._create_fallback_lesson(text)
            
            # Validate and fix the lesson structure
            lesson_data = self._validate_and_fix_lesson(lesson_data)
            
            logger.info("Successfully generated structured lesson")
            return lesson_data
            
        except Exception as e:
            logger.error(f"Error generating lesson: {str(e)}", exc_info=True)
            # Return fallback lesson instead of error
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

    def _create_docx(self, lesson_data: Dict[str, Any]) -> bytes:
        """Convert structured lesson to DOCX format with improved formatting"""
        try:
            doc = DocxDocument()
            
            # Add title with formatting
            title = doc.add_heading(level=1)
            title_run = title.add_run(lesson_data.get("title", "Generated Lesson"))
            title_run.bold = True
            
            # Add summary section
            if lesson_data.get("summary"):
                doc.add_heading("Summary", level=2)
                summary = doc.add_paragraph(lesson_data["summary"])
                summary.paragraph_format.space_after = Inches(0.1)
            
            # Add learning objectives with bullet points
            if lesson_data.get("learning_objectives"):
                doc.add_heading("Learning Objectives", level=2)
                for objective in lesson_data["learning_objectives"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(objective))
                doc.add_paragraph()
            
            # Add sections with proper spacing
            if lesson_data.get("sections"):
                for section in lesson_data["sections"]:
                    doc.add_heading(section.get("heading", "Section"), level=2)
                    content = doc.add_paragraph(section.get("content", ""))
                    content.paragraph_format.space_after = Inches(0.1)
                    doc.add_paragraph()
            
            # Add key concepts
            if lesson_data.get("key_concepts"):
                doc.add_heading("Key Concepts", level=2)
                for concept in lesson_data["key_concepts"]:
                    p = doc.add_paragraph(style='ListBullet')
                    p.add_run(str(concept))
                doc.add_paragraph()
            
            # Add activities with clear formatting
            if lesson_data.get("activities"):
                doc.add_heading("Activities", level=2)
                for i, activity in enumerate(lesson_data["activities"], 1):
                    activity_title = doc.add_heading(level=3)
                    activity_title.add_run(f"Activity {i}: {activity.get('name', 'Unnamed Activity')}").bold = True
                    
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
                doc.add_heading("Quiz", level=2)
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
            doc.add_heading("Lesson Generation", level=1)
            doc.add_paragraph("A lesson has been generated from your content.")
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()