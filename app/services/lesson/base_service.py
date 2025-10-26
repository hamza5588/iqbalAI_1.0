"""
Base lesson service with common functionality
"""
import logging
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tempfile
import os

logger = logging.getLogger(__name__)


class BaseLessonService:
    """
    Base class for lesson services with common functionality
    """
    
    def __init__(self, groq_api_key: str):
        """Initialize the base service with API key"""
        self.api_key = groq_api_key
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.1
        )
        logger.info("Base lesson service initialized")

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is supported"""
        if not filename:
            return False
        
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt'}
        return any(filename.lower().endswith(ext) for ext in allowed_extensions)

    def _load_document(self, file_path: str, filename: str) -> List[Document]:
        """Load document based on file type"""
        try:
            if filename.lower().endswith('.pdf'):
                loader = PyMuPDFLoader(file_path)
            elif filename.lower().endswith(('.doc', '.docx')):
                loader = UnstructuredWordDocumentLoader(file_path)
            elif filename.lower().endswith('.txt'):
                loader = TextLoader(file_path)
            else:
                logger.error(f"Unsupported file type: {filename}")
                return []
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} pages from {filename}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {filename}: {str(e)}")
            return []

    def _sanitize_heading(self, heading: str) -> str:
        """Sanitize heading text for DOCX generation"""
        if not heading:
            return "Untitled"
        
        # Remove or replace problematic characters
        heading = heading.replace('\n', ' ').replace('\r', ' ')
        heading = heading.strip()
        
        # Limit length
        if len(heading) > 100:
            heading = heading[:97] + "..."
        
        return heading
