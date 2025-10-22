"""
Base lesson service with common functionality
"""
import os
import logging
import tempfile
import json
import re
from typing import Any, Dict, List, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from docx import Document as DocxDocument
from docx.shared import Inches
from io import BytesIO

from .models import LessonResponse, LessonPlan

logger = logging.getLogger(__name__)


class BaseLessonService:
    """Base class with common functionality for lesson services"""
    
    def __init__(self, api_key: str):
        """Initialize the service with API key"""
        if not api_key:
            raise ValueError("API key is required. Please provide api_key parameter from database.")
        
        self.api_key = api_key
        
        try:
            self.llm = ChatGroq(
                api_key=api_key,
                model="llama-3.3-70b-versatile",
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq: {str(e)}")
            raise ValueError(f"Failed to initialize AI model: {str(e)}")

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is supported"""
        if not filename:
            return False
        ext = filename.split(".")[-1].lower()
        return ext in ["pdf", "doc", "docx", "txt"]

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

    def _extract_sections_from_prompt(self, full_text: str, lesson_prompt: str) -> Optional[str]:
        """Extract specific sections from the document based on the lesson prompt"""
        try:
            # Look for section patterns in the prompt
            section_patterns = [
                r'sections?\s+(\d+\.\d+)\s+to\s+(\d+\.\d+)',  # "sections 1.1 to 1.4"
                r'section\s+(\d+\.\d+)',  # "section 1.1"
                r'chapter\s+(\d+)',  # "chapter 3"
                r'topics?\s+([A-Za-z0-9\.\s,]+)',  # "topics A and B"
                r'(\d+\.\d+)\s+to\s+(\d+\.\d+)',  # "1.1 to 1.4"
            ]
            
            extracted_sections = []
            
            for pattern in section_patterns:
                matches = re.findall(pattern, lesson_prompt, re.IGNORECASE)
                if matches:
                    if len(matches[0]) == 2:  # Range pattern (e.g., "1.1 to 1.4")
                        start_section, end_section = matches[0]
                        extracted_sections.extend(self._extract_section_range(full_text, start_section, end_section))
                    else:  # Single section
                        section = matches[0]
                        extracted_sections.extend(self._extract_single_section(full_text, section))
            
            if extracted_sections:
                return "\n\n".join(extracted_sections)
            
            # If no specific sections found, try to extract based on keywords
            return self._extract_by_keywords(full_text, lesson_prompt)
            
        except Exception as e:
            logger.error(f"Error extracting sections from prompt: {str(e)}")
            return None

    def _extract_section_range(self, text: str, start_section: str, end_section: str) -> List[str]:
        """Extract a range of sections (e.g., 1.1 to 1.4)"""
        try:
            # Pattern to match section headers
            section_pattern = r'^(\d+\.\d+)\s+(.+)$'
            lines = text.split('\n')
            
            sections = []
            current_section = None
            in_range = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line is a section header
                match = re.match(section_pattern, line)
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2)
                    
                    # Check if we're starting the range
                    if section_num == start_section:
                        in_range = True
                        current_section = []
                        current_section.append(f"{section_num} {section_title}")
                        continue
                    
                    # Check if we're ending the range
                    if in_range and section_num == end_section:
                        current_section.append(f"{section_num} {section_title}")
                        sections.append('\n'.join(current_section))
                        break
                    
                    # If we're in range, add to current section
                    if in_range:
                        current_section.append(f"{section_num} {section_title}")
                    elif section_num > end_section:
                        break
                elif in_range and current_section:
                    # Add content to current section
                    current_section.append(line)
            
            return sections
            
        except Exception as e:
            logger.error(f"Error extracting section range {start_section} to {end_section}: {str(e)}")
            return []

    def _extract_single_section(self, text: str, section: str) -> List[str]:
        """Extract a single section"""
        try:
            # Pattern to match section headers
            section_pattern = r'^(\d+\.\d+)\s+(.+)$'
            lines = text.split('\n')
            
            sections = []
            current_section = None
            found_section = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line is a section header
                match = re.match(section_pattern, line)
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2)
                    
                    # Check if this is our target section
                    if section_num == section:
                        found_section = True
                        current_section = [f"{section_num} {section_title}"]
                        continue
                    elif found_section and re.match(r'^\d+\.\d+', line):
                        # Found next section, stop
                        break
                
                if found_section and current_section:
                    current_section.append(line)
            
            if current_section:
                sections.append('\n'.join(current_section))
            
            return sections
            
        except Exception as e:
            logger.error(f"Error extracting single section {section}: {str(e)}")
            return []

    def _extract_by_keywords(self, text: str, lesson_prompt: str) -> Optional[str]:
        """Extract content based on keywords in the prompt"""
        try:
            # Extract keywords from the prompt
            keywords = re.findall(r'\b\w+\b', lesson_prompt.lower())
            
            # Look for sections that contain these keywords
            lines = text.split('\n')
            relevant_sections = []
            current_section = []
            in_relevant_section = False
            
            for line in lines:
                line_lower = line.lower()
                
                # Check if this line contains any keywords
                if any(keyword in line_lower for keyword in keywords if len(keyword) > 3):
                    if not in_relevant_section:
                        in_relevant_section = True
                        current_section = []
                    current_section.append(line)
                elif in_relevant_section and line.strip():
                    current_section.append(line)
                elif in_relevant_section and not line.strip():
                    # Empty line, continue adding to current section
                    current_section.append(line)
                elif in_relevant_section and re.match(r'^\d+\.\d+', line):
                    # Found next section, stop
                    break
            
            if current_section:
                relevant_sections.append('\n'.join(current_section))
            
            if relevant_sections:
                return '\n\n'.join(relevant_sections)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting by keywords: {str(e)}")
            return None

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

    def _sanitize_heading(self, heading: str) -> str:
        """Remove or replace newlines from heading values for docx compatibility"""
        if not isinstance(heading, str):
            heading = str(heading)
        return heading.replace('\n', ' ').replace('\r', ' ').strip()

    def _create_fallback_lesson(self, text: str) -> Dict[str, Any]:
        """Create a basic lesson structure when AI generation fails"""
        
        # Extract first few sentences for summary
        sentences = text.split('.')[:3]
        summary = '. '.join(sentences).strip()
        if not summary:
            summary = "An engaging creative learning adventure based on the provided content."
        
        # Create basic lesson structure
        lesson_data = {
            "title": "Creative Learning Adventure",
            "summary": summary,
            "learning_objectives": [
                "Understand the main concepts through creative exploration",
                "Identify key points and themes with practical applications",
                "Develop creative thinking and problem-solving skills"
            ],
            "background_prerequisites": [
                "Basic understanding of foundational concepts",
                "Previous knowledge that builds to this lesson",
                "Essential skills needed for success"
            ],
            "sections": [
                {
                    "heading": "1. Introduction: Setting the Foundation",
                    "content": "Welcome to our creative learning journey! This lesson connects to what you already know and sparks your curiosity about new discoveries."
                },
                {
                    "heading": "2. Core Concept Development",
                    "content": text[:1000] + "..." if len(text) > 1000 else text
                },
                {
                    "heading": "3. Practical Applications",
                    "content": "See how these concepts apply to real life! Discover the creative and practical ways this knowledge helps us understand our world."
                },
                {
                    "heading": "4. Synthesis and Connection",
                    "content": "Now let's connect all the pieces together to see the complete picture and understand how everything works as a whole."
                },
                {
                    "heading": "5. Conclusion and Next Steps",
                    "content": "Great work! Let's summarize what we've learned and prepare for your continued creative exploration of this fascinating topic."
                }
            ],
            "key_concepts": [
                "Essential concept explained simply",
                "Important idea with creative connection",
                "Core principle emphasizing practical value"
            ],
            "creative_activities": [
                {
                    "name": "Creative Content Exploration",
                    "description": "Engage in hands-on creative exploration of the main concepts through discussion and practical application",
                    "duration": "20 minutes",
                    "learning_purpose": "Develop understanding through creative engagement and practical application"
                }
            ],
            "stem_equations": [
                {
                    "equation": "Relevant equation (if applicable)",
                    "term_explanations": [
                        "Simple explanation of each term",
                        "Real-world meaning of components",
                        "Practical significance"
                    ],
                    "mathematical_operations": "How operations transform terms",
                    "complete_equation_significance": "What the complete equation reveals about our world"
                }
            ],
            "assessment_quiz": [
                {
                    "question": "What creative approach helps you understand this lesson best?",
                    "options": [
                        "Hands-on exploration",
                        "Visual connections", 
                        "Real-world examples",
                        "All of the above"
                    ],
                    "answer": "D",
                    "explanation": "The best learning happens when we combine multiple creative approaches to build understanding."
                }
            ],
            "teacher_notes": [
                "Adapt activities to different learning styles",
                "Encourage creative thinking and innovation",
                "Provide additional challenges for advanced students",
                "Offer support strategies for students who need extra help"
            ]
        }
        
        # Wrap in the expected response structure
        return {
            "response_type": "lesson_plan",
            "lesson": lesson_data
        }
