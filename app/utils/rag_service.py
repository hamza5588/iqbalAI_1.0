from __future__ import annotations

import os
import sqlite3
import tempfile
import json
import re
import logging
from pathlib import Path
from typing import Annotated, Any, Dict, Optional, TypedDict, List

from dotenv import load_dotenv
from app.utils.db import get_db
from app.models.database_models import RAGPrompt

logger = logging.getLogger(__name__)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.utils.llm_factory import create_llm
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import requests

load_dotenv()

# -------------------
# Global rate limiter for Groq API calls
# -------------------
import time
from threading import Lock

class GroqRateLimiter:
    """Global rate limiter for Groq API to prevent 429 errors"""
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(GroqRateLimiter, cls).__new__(cls)
                    cls._instance.last_request_time = 0
                    cls._instance.min_interval = 3.0  # Increased to 3 seconds between requests
                    cls._instance.consecutive_429_count = 0  # Track consecutive 429 errors
        return cls._instance
    
    def wait_if_needed(self):
        """Wait if needed to respect rate limits"""
        with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            # Increase delay if we've had recent 429 errors
            adjusted_interval = self.min_interval
            if self.consecutive_429_count > 0:
                adjusted_interval = self.min_interval * (1 + self.consecutive_429_count * 0.5)
                logger.warning(f"Rate limiter: increased interval to {adjusted_interval:.1f}s due to {self.consecutive_429_count} recent 429 errors")
            
            if time_since_last < adjusted_interval:
                wait_time = adjusted_interval - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds before next Groq request")
                time.sleep(wait_time)
            self.last_request_time = time.time()
    
    def record_429_error(self):
        """Record a 429 error to adjust rate limiting"""
        with self._lock:
            self.consecutive_429_count += 1
            logger.warning(f"Recorded 429 error. Consecutive count: {self.consecutive_429_count}")
    
    def record_success(self):
        """Record a successful request to reset error count"""
        with self._lock:
            if self.consecutive_429_count > 0:
                logger.info(f"Resetting 429 error count after successful request")
            self.consecutive_429_count = 0

groq_rate_limiter = GroqRateLimiter()

# -------------------
# LLM instance cache to avoid recreating instances
# -------------------
_llm_cache = {}
_llm_cache_lock = Lock()

def get_cached_llm(user_id: int, api_key: str, provider: str):
    """Get or create a cached LLM instance for a user"""
    cache_key = f"{user_id}_{provider}_{api_key[:10] if api_key else 'none'}"
    
    with _llm_cache_lock:
        if cache_key not in _llm_cache:
            logger.debug(f"Creating new LLM instance for cache key: {cache_key[:20]}...")
            _llm_cache[cache_key] = get_rag_llm(api_key=api_key, provider=provider)
        else:
            logger.debug(f"Reusing cached LLM instance for user {user_id}")
        return _llm_cache[cache_key]

# -------------------
# 1. LLM + embeddings
# -------------------
# Use dynamic LLM factory - supports OpenAI, Groq, and vLLM
# Note: RAG service uses a global LLM instance, but individual requests should use user-specific API keys
# This is a fallback for when user API key is not available
def get_rag_llm(api_key=None, provider=None):
    """Get LLM for RAG service, using system settings or provided parameters"""
    if provider is None:
        # Get from system settings
        from app.utils.db import get_db
        from app.models.database_models import SystemSettings
        try:
            db = get_db()
            setting = db.query(SystemSettings).filter(SystemSettings.key == 'llm_provider').first()
            provider = setting.value if setting else os.getenv('LLM_PROVIDER', 'openai').lower()
        except:
            provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    return create_llm(
        temperature=0.7,
        api_key=api_key if provider in ['openai', 'groq'] else None,
        provider=provider
    )

# Global fallback LLM (used when user API key is not available)
llm = get_rag_llm()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# -------------------
# 2. Single shared vector store paths
# -------------------
BASE_DIR = Path(__file__).parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "vector_stores"
SHARED_VECTOR_STORE_PATH = VECTOR_STORE_DIR / "shared_vectorstore.faiss"
UPLOADED_FILES_DIR = BASE_DIR / "uploaded_files"
METADATA_FILE = BASE_DIR / "rag_metadata.json"

# Create directories if they don't exist
VECTOR_STORE_DIR.mkdir(exist_ok=True)
UPLOADED_FILES_DIR.mkdir(exist_ok=True)

# -------------------
# 3. Global shared vector store
# -------------------
_SHARED_VECTOR_STORE: Optional[FAISS] = None
_THREAD_METADATA: Dict[str, dict] = {}

# Load metadata from disk on startup
def _load_metadata():
    """Load metadata from disk."""
    global _THREAD_METADATA
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                _THREAD_METADATA = json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            _THREAD_METADATA = {}

def _save_metadata():
    """Save metadata to disk."""
    try:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(_THREAD_METADATA, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving metadata: {e}")

def _load_shared_vector_store():
    """Load the shared vector store from disk."""
    global _SHARED_VECTOR_STORE
    if _SHARED_VECTOR_STORE is not None:
        return _SHARED_VECTOR_STORE
    
    if SHARED_VECTOR_STORE_PATH.exists():
        try:
            _SHARED_VECTOR_STORE = FAISS.load_local(
                str(SHARED_VECTOR_STORE_PATH.parent),
                embeddings,
                allow_dangerous_deserialization=True,
                index_name=SHARED_VECTOR_STORE_PATH.stem
            )
            print(f"Loaded shared vector store with {_SHARED_VECTOR_STORE.index.ntotal} vectors")
        except Exception as e:
            print(f"Error loading shared vector store: {e}")
            _SHARED_VECTOR_STORE = None
    
    return _SHARED_VECTOR_STORE

def _save_shared_vector_store():
    """Save the shared vector store to disk."""
    if _SHARED_VECTOR_STORE is not None:
        try:
            _SHARED_VECTOR_STORE.save_local(
                str(SHARED_VECTOR_STORE_PATH.parent),
                index_name=SHARED_VECTOR_STORE_PATH.stem
            )
            print(f"Saved shared vector store with {_SHARED_VECTOR_STORE.index.ntotal} vectors")
        except Exception as e:
            print(f"Error saving shared vector store: {e}")

def _extract_user_id_from_thread_id(thread_id: str) -> Optional[int]:
    """Extract user_id from thread_id format: user_{user_id}_conv_{conversation_id} or user_{user_id}_default"""
    if not thread_id:
        return None
    
    match = re.match(r'user_(\d+)(?:_conv_\d+|_default|_thread_\d+_\w+)?', thread_id)
    if match:
        return int(match.group(1))
    return None


def _get_rag_prompt(user_id: Optional[int], thread_id: Optional[str] = None) -> Optional[str]:
    """
    Get custom RAG prompt for user from database.
    Prompts are user-level and apply to all threads for that user.
    Returns None if no custom prompt is set (will use default).
    """
    if not user_id:
        return None
    
    try:
        db = get_db()
        # Get user-specific prompt (applies to all threads)
        prompt = db.query(RAGPrompt).filter(
            RAGPrompt.user_id == user_id,
            RAGPrompt.thread_id.is_(None)
        ).order_by(RAGPrompt.updated_at.desc()).first()
        
        if prompt:
            return prompt.prompt
        
        return None
    except Exception as e:
        logger.error(f"Error retrieving RAG prompt: {str(e)}")
        return None

def _get_retriever(thread_id: Optional[str], user_id: Optional[int] = None):
    """
    Get a retriever for a specific thread with metadata filtering.
    Filters results to only include documents from the specified thread_id and user_id.
    """
    if not thread_id:
        return None
    
    # Extract user_id from thread_id if not provided
    if user_id is None:
        user_id = _extract_user_id_from_thread_id(thread_id)
    
    if user_id is None:
        return None
    
    # Load shared vector store
    vector_store = _load_shared_vector_store()
    if vector_store is None:
        return None
    
    # Create a custom retriever that filters by thread_id and user_id
    class FilteredRetriever:
        def __init__(self, vector_store: FAISS, thread_id: str, user_id: int):
            self.vector_store = vector_store
            self.thread_id = thread_id
            self.user_id = user_id
        
        def invoke(self, query: str) -> List[Document]:
            """Retrieve documents and filter by thread_id and user_id."""
            # Get more results than needed, then filter
            docs = self.vector_store.similarity_search_with_score(query, k=20)
            
            # Filter documents by thread_id and user_id
            filtered_docs = []
            for doc, score in docs:
                meta = doc.metadata
                doc_thread_id = meta.get('thread_id', '')
                doc_user_id = meta.get('user_id')
                
                # Check if document belongs to this thread and user
                if doc_thread_id == self.thread_id and doc_user_id == self.user_id:
                    filtered_docs.append(doc)
                
                # Stop when we have enough results
                if len(filtered_docs) >= 4:
                    break
            
            return filtered_docs
    
    return FilteredRetriever(vector_store, thread_id, user_id)

def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None, progress_callback: Optional[callable] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store metadata inside the vector DB.
    Adds documents to the shared vector store with user_id and thread_id metadata.
    
    Args:
        file_bytes: PDF file bytes
        thread_id: Thread ID for the document
        filename: Optional filename
        progress_callback: Optional callback function(step, progress, message) for progress updates
    """
    def _send_progress(step: str, progress: int, message: str):
        """Helper to send progress updates"""
        if progress_callback:
            try:
                progress_callback(step, progress, message)
            except Exception as e:
                logger.warning(f"Error sending progress update: {e}")
    
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    _send_progress("init", 5, "Initializing PDF processing...")
    
    thread_id_str = str(thread_id)
    user_id = _extract_user_id_from_thread_id(thread_id_str)
    
    if user_id is None:
        raise ValueError(f"Could not extract user_id from thread_id: {thread_id_str}")
    
    # Save the original PDF file
    safe_filename = filename or f"document_{thread_id_str}.pdf"
    # Sanitize filename
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._- ")
    file_path = UPLOADED_FILES_DIR / f"{thread_id_str}_{safe_filename}"
    
    _send_progress("saving", 10, "Saving PDF file...")
    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    # Create temp file for PDF loader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        _send_progress("loading", 15, "Reading PDF document...")
        loader = PyPDFLoader(temp_path)
        docs = loader.load()  # each item = 1 PDF page
        
        # Calculate total number of pages - ensure we have valid pages
        num_pages = len(docs)
        if num_pages == 0:
            raise ValueError("PDF appears to be empty or could not be loaded. No pages found.")
        
        _send_progress("validating", 25, f"Validating {num_pages} pages...")
        
        # Verify pages have content
        valid_pages = [doc for doc in docs if doc.page_content and doc.page_content.strip()]
        if len(valid_pages) == 0:
            raise ValueError("PDF loaded but contains no extractable text content.")
        
        # Use valid pages count if different
        if len(valid_pages) != num_pages:
            logger.warning(f"PDF has {num_pages} pages but only {len(valid_pages)} contain extractable text")
            # Still use original count for metadata, but note the difference
            num_pages = len(docs)  # Keep original page count

        _send_progress("metadata", 30, "Adding metadata to pages...")
        # Inject additional metadata directly INTO the documents before splitting
        for i, doc in enumerate(docs):
            doc.metadata = {
                **doc.metadata,
                "thread_id": thread_id_str,
                "user_id": user_id,  # Add user_id to metadata
                "filename": filename or os.path.basename(temp_path),
                "page": i + 1,
                "page_number": i + 1,  # Alternative key for clarity
                "total_pages": num_pages,  # Store total pages in each page's metadata
            }

        _send_progress("splitting", 40, "Splitting document into chunks...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1600,
            chunk_overlap=600,
            separators=["\n\n", "\n", " ", ""]
        )

        # Split docs, keeping metadata automatically
        chunks = splitter.split_documents(docs)
        _send_progress("splitting", 50, f"Created {len(chunks)} text chunks from {num_pages} pages")

        _send_progress("chunk_metadata", 55, "Enriching chunk metadata...")
        # Add even richer metadata to each chunk
        for i, c in enumerate(chunks):
            # Preserve page number from original metadata
            page_num = c.metadata.get("page") or c.metadata.get("page_number", "unknown")
            c.metadata = {
                **c.metadata,
                "chunk_length": len(c.page_content),
                "source_pdf": filename or os.path.basename(temp_path),
                "thread_id": thread_id_str,
                "user_id": user_id,  # Ensure user_id is in every chunk
                "page": page_num,  # Ensure page number is preserved
                "page_number": page_num,  # Alternative key
                "num_pages": num_pages,  # Total pages in PDF
                "total_pages": num_pages,  # Alternative key
            }
            # Update progress for large documents
            if (i + 1) % 50 == 0:
                _send_progress("chunk_metadata", 55 + int((i + 1) / len(chunks) * 5), f"Processing chunk {i + 1}/{len(chunks)}...")

        _send_progress("vector_store", 60, "Loading vector store...")
        # Load or create shared vector store
        global _SHARED_VECTOR_STORE
        vector_store = _load_shared_vector_store()
        
        if vector_store is None:
            _send_progress("embeddings", 65, "Creating embeddings for chunks (this may take a moment)...")
            # Create new vector store
            vector_store = FAISS.from_documents(chunks, embeddings)
            _SHARED_VECTOR_STORE = vector_store
            _send_progress("embeddings", 80, f"Created embeddings for {len(chunks)} chunks")
        else:
            _send_progress("embeddings", 70, f"Adding {len(chunks)} chunks to vector store...")
            # Add new documents to existing vector store
            vector_store.add_documents(chunks)
            _SHARED_VECTOR_STORE = vector_store
            _send_progress("embeddings", 80, f"Added {len(chunks)} chunks to vector store")

        _send_progress("saving", 85, "Saving vector store to disk...")
        # Save vector store to disk
        _save_shared_vector_store()

        _send_progress("metadata", 90, "Saving document metadata...")
        # Save thread metadata (num_pages was already calculated above)
        _THREAD_METADATA[thread_id_str] = {
            "filename": filename or safe_filename,
            "file_path": str(file_path),
            "user_id": user_id,
            "documents": num_pages,  # Keep for backward compatibility
            "num_pages": num_pages,  # Explicit page count
            "pages": num_pages,  # Alternative key for clarity
            "chunks": len(chunks),
        }
        
        # Persist metadata to disk
        _save_metadata()
        _send_progress("cleanup", 95, "Cleaning up temporary files...")

        # Delete temporary PDF file after chunks are created and stored
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Deleted temporary PDF file: {temp_path}")
        except OSError as e:
            logger.warning(f"Failed to delete temporary PDF file {temp_path}: {e}")

        # Delete the uploaded file from uploaded_files directory after processing
        try:
            if file_path.exists():
                os.remove(file_path)
                logger.debug(f"Deleted uploaded PDF file: {file_path}")
        except OSError as e:
            logger.warning(f"Failed to delete uploaded PDF file {file_path}: {e}")

        _send_progress("complete", 100, f"PDF processing complete! Processed {num_pages} pages into {len(chunks)} chunks.")
        
        return {
            "thread_id": thread_id_str,  # Include thread_id in response
            "filename": filename or safe_filename,
            "documents": num_pages,  # Keep for backward compatibility
            "num_pages": num_pages,  # Explicit page count
            "pages": num_pages,  # Alternative key
            "chunks": len(chunks),
        }

    finally:
        # Safety net: ensure temp file is deleted even if an error occurred
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Deleted temporary PDF file in finally block: {temp_path}")
        except OSError as e:
            logger.warning(f"Failed to delete temporary PDF file in finally block {temp_path}: {e}")


# -------------------
# 4. Tools
# -------------------



@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}




@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool.
    """
    # Extract user_id from thread_id for filtering
    user_id = _extract_user_id_from_thread_id(thread_id) if thread_id else None
    
    retriever = _get_retriever(thread_id, user_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    result = retriever.invoke(query)
    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]
    
    # Get thread metadata for page count
    thread_meta = _THREAD_METADATA.get(str(thread_id), {})
    num_pages = thread_meta.get("num_pages") or thread_meta.get("pages") or thread_meta.get("documents")

    return {
        "query": query,
        "context": context,
        "metadata": metadata,
        "source_file": thread_meta.get("filename"),
        "num_pages": num_pages,  # Total number of pages in the PDF
        "pages": num_pages,  # Alternative key
    }


tools = [calculator, rag_tool]
# Note: llm_with_tools and llm_structured_output are now created per-request in chat_node
# to use user-specific API keys and provider settings

# -------------------
# 5. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    lesson_in_progress: bool
    lesson_finalized: bool
    last_lesson_text: str

class LessonState(TypedDict):
    lesson_in_progress: bool
    lesson_finalized: bool
    last_lesson_text: str
    lesson_title: str

# -------------------
# 6. Nodes
# -------------------

def chat_node(state: ChatState, config=None):
    """LLM node that may answer or request a tool call."""
    thread_id = None
    thread_id_str = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            thread_id_str = str(thread_id)

    # Check if a PDF document exists for this thread
    has_document = False
    if thread_id_str:
        # Check metadata
        if thread_id_str in _THREAD_METADATA:
            has_document = True
        # Also check if vector store exists and has documents for this thread
        else:
            _load_metadata()  # Reload in case it was updated
            if thread_id_str in _THREAD_METADATA:
                has_document = True
    
    # Get user_id from thread_id
    user_id = _extract_user_id_from_thread_id(thread_id_str) if thread_id_str else None
    
    # Get user-specific API key and provider for this request
    user_api_key = None
    provider = None
    if user_id:
        try:
            from app.models.database_models import User as DBUser
            db = get_db()
            
            # Get provider from system settings first
            from app.models.database_models import SystemSettings
            setting = db.query(SystemSettings).filter(SystemSettings.key == 'llm_provider').first()
            provider = setting.value if setting else os.getenv('LLM_PROVIDER', 'openai').lower()
            
            # If OpenAI is set from admin, use environment variable instead of database key
            if provider == 'openai' and setting:
                user_api_key = os.getenv('OPENAI_API_KEY')
            else:
                # Get user's API key from database
                # Note: The field is named 'groq_api_key' but it stores the API key for the selected provider
                user = db.query(DBUser).filter(DBUser.id == user_id).first()
                if user:
                    user_api_key = user.groq_api_key or None
                    # If no API key in database, try to get from environment as fallback
                    if not user_api_key:
                        if provider == 'groq':
                            user_api_key = os.getenv('GROQ_API_KEY')
                        elif provider == 'openai':
                            user_api_key = os.getenv('OPENAI_API_KEY')
                else:
                    user_api_key = None
        except Exception as e:
            logger.warning(f"Error getting user API key or provider: {str(e)}, falling back to defaults")
            provider = os.getenv('LLM_PROVIDER', 'openai').lower()
            user_api_key = os.getenv('GROQ_API_KEY') if provider == 'groq' else os.getenv('OPENAI_API_KEY')
    else:
        # Fallback to environment variables if no user_id
        provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        user_api_key = os.getenv('GROQ_API_KEY') if provider == 'groq' else os.getenv('OPENAI_API_KEY')
    
    # Create user-specific LLM instance with correct provider and API key
    # Log the provider and whether API key is available (without logging the actual key)
    logger.info(f"Creating LLM for user {user_id}: provider={provider}, has_api_key={bool(user_api_key)}")
    
    # Validate API key is present when required
    if provider in ['openai', 'groq'] and not user_api_key:
        error_msg = (
            f"{provider.upper()} API key is required when {provider} is selected as the LLM provider. "
            f"Please configure your {provider.upper()} API key using the key icon in the chat interface."
        )
        logger.error(f"Missing API key for provider {provider}: {error_msg}")
        # Return error message as AI response
        error_response = AIMessage(
            content=(
                f"⚠️ **API Key Required**: {error_msg}\n\n"
                f"Please configure your {provider.upper()} API key to continue using the chat feature."
            )
        )
        return {"messages": [error_response]}
    
    try:
        # Use cached LLM instance to avoid recreating on every call
        if user_id:
            user_llm = get_cached_llm(user_id, user_api_key, provider)
        else:
            user_llm = get_rag_llm(api_key=user_api_key, provider=provider)
        
        user_llm_with_tools = user_llm.bind_tools(tools)
        user_llm_structured_output = user_llm.with_structured_output(LessonState)
        logger.debug(f"Successfully created/retrieved {provider} LLM instance for user {user_id}")
    except Exception as e:
        logger.error(f"Error creating user-specific LLM: {str(e)}, falling back to global LLM")
        # Fallback to global LLM if user-specific LLM creation fails
        # But only if it's not a missing API key error
        if "API key" in str(e) or "api key" in str(e).lower():
            error_response = AIMessage(
                content=(
                    f"⚠️ **API Key Error**: {str(e)}\n\n"
                    f"Please configure your {provider.upper()} API key to continue using the chat feature."
                )
            )
            return {"messages": [error_response]}
        user_llm_with_tools = llm.bind_tools(tools)
        user_llm_structured_output = llm.with_structured_output(LessonState)
    
    # Get custom prompt from database (user-level, applies to all threads)
    custom_prompt = _get_rag_prompt(user_id, thread_id_str)
    # custom_prompt = """
    # Section A
    # # Prof. Potter - Lesson Planning Assistant
    # 1.	You are Prof. Potter, an expert education assistant helping Faculty/Teachers prepare lesson plans from uploaded documents.
    # **Communication Style**
    # 2.	Greeting (first interaction only): "Hello, I'm Prof. Potter, here to help you prepare your lesson plan." (≤20 words)
    # **CRITICAL INSTRUCTION 1: Dual-Verification Before Response**
    # 4.	For every Faculty question, follow this exact process:
    # 4.1.	Reread the original question the Faculty asked and ask for any clarification, engage in the conversation, and exchange after the teacher has made it clear as to what he/she are looking for
    # 4.2.	Generate two independent answers to the teacher's question internally
    # 4.3.	Compare both answers and only when answers match ≥98%, provide the answer to the Faculty
    # 4.4.	If internal answers don't match ≥98%, this signals ambiguity - return to instruction 4.
    # 4.5.	This verification happens silently - Faculty does not see this process
    # 5.	Remove any repetitive sentences within the response (unless repetition serves to reinforce learning)

    # **CRITICAL INSTRUCTION 2: Ambiguity Resolution Process**
    # 6.	When a question can be interpreted in multiple ways, STOP immediately and ask additional clarifying questions
    # 7.	Always build the lesson logically from the prerequisites to the main topic
    #  
    # Section B: The method
    # 1.	The teacher proceeds to ask LLM a question, and LLM uses the following process, without revealing until step N: 
    # Given the teacher's request for help in preparing a class lesson, the LLM first identifies the subject, then the topic, and finally the concept to be explained in the lesson. 
    # 1.1.	Ask the teacher for confirmation.
    # 1.1.1.	If confirmed by the teacher, then LLM continues.
    # 1.1.2.	Otherwise, ask the teacher for clarification
    # 2.	Continuing, the LLM identifies the corresponding mathematical equation associated with the lesson plan’s content. (This is the first critical path to teaching, connecting the concept with the mathematical equation.)
    # DISSECTING EQUATIONS
    # 2.1.	LLM identifies and explains all the terms in the equations.
    # 2.2.	LLM explains the PHYSICAL meaning of each term in the equation
    # 3.	LLM explains that equations involve an equal sign, where one side of the equation is equal to the other side. Another way of saying the same thing is that the term on one side of the equal sign balances the terms on the other side of the equal sign.
    # 4.	Breaking down the equation, LLM explains that when looking at terms individually, one side of the term is proportional to the term on the other side of the equation.
    # Significance of the Terms Location in the Complete Equation
    # 5.	LLM explains the significance of the position of these terms, for example, whether they are in the numerator or the denominator.
    # 6.	Mathematical operations on Equation’s terms.
    # 6.1.	LLM so far has explained what the individual term means by itself
    # 6.2.	Now, LLM explains what the following mathematical operators do to the terms and then explains what the resulting terms mean physically
    # 6.2.1.	Exponents (positive or negative powers)
    # 6.2.2.	Square roots (√) and cube roots and more
    # 6.2.3.	Squared terms (²), Cubed terms, and more
    # 6.2.4.	Multiplied terms with exponents
    # 6.2.5.	Coefficients and their meaning
    # 6.3.	What the operator acting on the term produces weather physically or conceptually, meaning, what does it mean when the term is either squared, multiplied by a coefficient, multiplied by an exponent, and more
    # 6.4.	Explain the significance of each term's position in the equation (numerator vs denominator, exponents, powers, coefficients)
    # 7.	Narrate the equation as follows: verbally in a manner easily explainable at the student's grade level. 
    # 7.1.	Here we assume there is one term on the left side of the equal sign, and on the other side of the equal sign, there are two terms multiplied by each other and another term in the denominator that is squared. The term on the right side is multiplied by another term. This is how LLM will explain the equation
    # 7.2.	The left side term is proportional to the right side’s first term
    # 7.3.	The left side term is proportional to the right side’s second term
    # 7.4.	The left side term is inversely proportional to the right side of the equation; it is inversely proportional since it is in the denominator.
    # 7.5.	Important point is the term in the denominator is squared, so it decreases the value on the left side of the equation by a square, meaning if the denominator term doubles, the term on left side decreases by fourth, and if the denominator term increases by a cube and is squared, the term on the left side will decrease by 9 times.
    # 7.6.	After LLM explained that the combination of all terms on the right side is proportional to the term on the left side, the proportional sign is now replaced with an equal sign and a constant. 
    # 7.6.1.	Explain to students that when a proportionality is removed and replaced by an equal sign, it also adds a constant. This is the complete equation.
    # 8.	Real world example
    # 8.1.	Newton Gravitational Law; 
    # 8.2.	Hydrostatic Pressure
    # 8.3.	Equation of continuity in fluids, LLM adopts the following process and explains lessons from simpler to more detailed
    # 8.3.1.	Explain by saying the cross-sectional area where fluid is passing through with velocity is a constant. 
    # 8.3.2.	The cross-sectional area size of a pipe multiplied by the velocity of the same fluid passing through the same size cross-section is equal to a different cross-sectional area size and multiplied by a different velocity. 
    # 8.3.3.	Furthermore, it means cross-sectional area 1, which has a liquid passing through, is multiplied by the same liquid's velocity 1, and that is EQUAL to different cross-sectional area 2 multiplied by different velocity 2.  
    # 8.3.4.	Giving a real-world example: Imagine a long hose, and water is passing through. At one point in the long pipe, the pipe is squeezed, and by the action of squeezing, the cross-section of the pipe is reduced. What the equation of continuity states is that two quantities, that is, cross-sectional area multiplied by velocity of the liquid passing through the same cross-sectional area, must remain a constant value. Meaning, imagine the constant here is 16, so the equation states that when you multiply the two quantities, it must always be equal to 16. The two quantities multiplied here are cross-sectional area and velocity; when multiplied, they need to produce a result of 16. For example, if one quantity is 8, the other must be 2. If one quantity is 4, the other must also be 4 to produce the same constant, 16. 
    # 8.3.5.	What does it mean physically? It means enlarging one quantity automatically reduces the other’s quantity, so if you reduce the cross-sectional area, the velocity needs to increase. Let's look at this with a real-life example, say you are holding the end of the garden hose where the water is flowing out. By squeezing the end of the garden hose with your hand, you immediately observe the water exiting the hose more rapidly. Stated differently, reducing the cross-sectional area at the end of the hose increases the water velocity exiting the hose.
    # 9.	This Section A:  The Method, happens silently – Faculty/Teacher does not see this process
    



    #  
    # Section C: The Lecture Generation Process
    # 1.	The following steps are in the lesson to be generated
    # 1.1.	State the subject being discussed
    # 1.2.	State the subject's context as to what is being talked about
    # 1.3.	State the verbal definition of the concept, clearly with heavy emphasis on using the correct definition and, within it, using the exact terminology, and before diving deep into the lesson. 
    # 1.4.	Understand the Faculty's lesson topic, and suggest the prerequisites students need
    # 1.4.1.	Clearly state: "For students to understand [topic], they need to know [prerequisites]. Would you like me to include prerequisite material in the lesson plan?"
    # 1.4.2.	If prerequisites are not in the document, inform the Faculty and ask: "How would you like me to address prerequisites not covered in this document?" Follow the instructions of the Faculty/Teacher
    # 1.4.3.	Go through Section B  
    # 1.5.	Most importantly, differentiate by comparing the current lesson from the previous lesson, and if not available, check the curriculum as to what was taught before the current lesson, and differentiate the two clearly by doing the following
    # 1.5.1.	Differentiate the subject of the current lesson from the previous lesson
    # 1.5.2.	Differentiate the context of the previous lesson from the current lesson
    # 1.5.3.	Describe and explain what the lesson is to be learnt here and compare with the previous lesson or previous subject in the curriculum
    # 1.6.	Differentiate each term involved in the current lesson from each term involved in the previous lesson
    # 1.7.	If one lesson has an equation while the other lesson is a concept, explain both, compare both, and differentiate both.
    # 2.	LLM narrate the complete equation verbally in a manner easily understandable at the student's grade level.
    # 3.	Build the lesson logically from the prerequisites to the main topic and the conclusion
    #  
    # Section D: Lesson Structure
    # Step 1: State formal definition → Section B

    # Step 2: List prerequisites → justify necessity → rank importance →  Section B

    # Step 3: Teach prerequisites (def + explanation + example) → justify universal coverage (strong/struggling/all benefits)

    # Step 4: Connect to prerequisites → differentiate explicitly (use exact pattern) → confront misconception (state/why wrong/correct/why develops) → Follow instructions in Section B

    # Step 5: Extract key terms → define each → identify CRITICAL term (essential because/missing causes/this means) → Follow instructions Section C 

    # Step 6: Create concrete scenario with numbers → work step-by-step → highlight distinction → show misconception fails → Follow instructions Section C

    # Step 7: Show concept interaction → give real applications → synthesize completely → Follow instructions Section B

    # Step 8: Ask assessment questions → address remaining confusion → confirm all objectives → Confer uploaded document
    # **instruction**
    # **very very important instruction***
    # #while creating te lecture each headings should be present in paragraph form and max of 9 to 10 lines explanation on each headings

    # Output: Complete explanation with all 8 Steps, all mandatory components, meeting all quality standards
        
        
        
    
    
    # """
    
    if has_document:
        # Get document info
        doc_meta = _THREAD_METADATA.get(str(thread_id), {})
        filename = doc_meta.get("filename", "PDF")
        num_pages = doc_meta.get("num_pages") or doc_meta.get("pages") or doc_meta.get("documents")
        page_info = f" The PDF has {num_pages} pages." if num_pages else ""
        
        # Default RAG instructions (always included)
        rag_instructions = (
    f"IMPORTANT: When the user asks ANY question that could be answered by the PDF, you MUST:\n"
    f"1. Call the rag_tool function\n"
    f"2. Pass the user's question as the 'query' parameter\n"
    f"3. Pass '{thread_id}' as the 'thread_id' parameter (this is REQUIRED)\n\n"

    f"When generating a LECTURE or LESSON, you MUST follow these rules strictly:\n"
    f"- Use clear and meaningful headings\n"
    f"- Under EACH heading, write a DETAILED explanation in PARAGRAPH form\n"
    f"- Each paragraph should be 7 to 8 complete sentences\n"
    f"- DO NOT write one-line summaries under headings\n"
    f"- DO NOT use bullet points unless the user explicitly asks for them\n"
    f"- Write in an academic, lecture-style tone suitable for teaching\n"
    f"- Explain concepts clearly, as if teaching students\n\n"

    f"When you call rag_tool, it will return:\n"
    f"- Relevant content from the PDF\n"
    f"- Page numbers and metadata\n"
    f"- Total number of pages (num_pages or pages field)\n"
    f"- Source filename\n\n"

    f"Always integrate PDF content naturally into explanations instead of copying verbatim.\n"
    f"When asked about number of pages, use ONLY the num_pages or pages field.\n"
    f"Always return the response in MARKDOWN format.\n\n"

    f"CRITICAL: Lesson Finalization Rules:\n"
    f"- ONLY set lesson_finalized = true when the user EXPLICITLY requests to finalize the lesson\n"
    f"- User must say things like: 'finalize', 'this is final', 'I am satisfied', 'complete the lesson', 'save the lesson', etc.\n"
    f"- DO NOT automatically finalize lessons - wait for explicit user confirmation\n"
    f"- When user explicitly requests finalization, you MUST:\n"
    f"  * Set lesson_finalized = true\n"
    f"  * Provide a meaningful and specific lesson_title\n"
    f"  * The lesson_title must clearly reflect the lecture topic\n"
    f"  * Example titles: 'AI-Based Scheduling Systems', 'Conversational SaaS Platforms'\n"
    f"  * DO NOT use generic titles like 'Lesson' or 'Lecture'\n"
    f"- The output should be more than 15 to 16 lines in each heading in lesson creation\n"
    f"- In each heading the minimum words should be 120 to 150"
)

        # Combine custom prompt with default RAG instructions
        if custom_prompt:
            # Custom prompt + default RAG instructions
            base_content = (
                f"{custom_prompt}\n\n"
                f"---\n\n"
                f"You are a helpful assistant. A PDF document ({filename}) has been uploaded for this conversation.{page_info}\n\n"
                f"{rag_instructions}"
            )
        else:
            # Default system message with RAG instructions
            base_content = (
                f"You are a helpful assistant. A PDF document ({filename}) has been uploaded for this conversation.{page_info}\n\n"
                f"{rag_instructions}"
            )
        
        system_message = SystemMessage(content=base_content)
    else:
        # No document uploaded
        if custom_prompt:
            # Use custom prompt even when no document
            system_message = SystemMessage(content=custom_prompt)
        else:
            # Default message when no document
            system_message = SystemMessage(
                content=(
                    "You are a helpful assistant. No PDF document has been uploaded yet. "
                    "You can use web search, stock price, and calculator tools when helpful. "
                    "If the user asks about a PDF, ask them to upload one first."
                )
            )

    # Progressive message reduction on token errors
    conversation_messages = state["messages"]
    initial_max_messages = 7  # Start with 7 messages
    max_attempts = 4  # Try with 7, 5, 3, 1 messages
    
    def _is_token_error(error_msg: str) -> bool:
        """Check if error is related to token/context length limits."""
        error_lower = error_msg.lower()
        token_keywords = [
            "maximum context length",
            "context length exceeded",
            "exceeds maximum",
            "too many tokens",
            "maximum tokens",
            "context window",
            "token limit",
            "token count",
            "input length",
            "maximum input length",
            "input tokens",
        ]
        return any(keyword in error_lower for keyword in token_keywords)
    
    def _prepare_messages(num_messages: int):
        """Prepare messages list with specified number of conversation messages.
        Ensures tool messages are always properly paired with their assistant messages.
        Only includes complete tool call sequences (assistant with tool_calls + all corresponding tool messages)."""
        if len(conversation_messages) <= num_messages:
            return [system_message, *conversation_messages]
        
        # Helper function to check if a message is an assistant with tool_calls
        def is_assistant_with_tool_calls(msg):
            return isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls
        
        # Helper function to check if a message is a tool message
        def is_tool_message(msg):
            return isinstance(msg, ToolMessage)
        
        # Helper function to find complete tool call sequence starting from an assistant message
        def get_tool_sequence_start(assistant_idx):
            """Returns the start index of a complete tool call sequence, or None if incomplete."""
            if assistant_idx < 0 or assistant_idx >= len(conversation_messages):
                return None
            
            assistant_msg = conversation_messages[assistant_idx]
            if not is_assistant_with_tool_calls(assistant_msg):
                return None
            
            # Get all tool_call_ids from the assistant message
            tool_call_ids = {tc.get('id') for tc in assistant_msg.tool_calls if isinstance(tc, dict) and 'id' in tc}
            if not tool_call_ids:
                return None
            
            # Look forward to find all corresponding tool messages
            found_tool_ids = set()
            tool_start_idx = assistant_idx + 1
            
            # Collect all consecutive tool messages
            for j in range(assistant_idx + 1, len(conversation_messages)):
                msg = conversation_messages[j]
                if is_tool_message(msg):
                    tool_id = getattr(msg, 'tool_call_id', None)
                    if tool_id and tool_id in tool_call_ids:
                        found_tool_ids.add(tool_id)
                else:
                    # Stop at first non-tool message
                    break
            
            # Only return if we found all tool responses
            if found_tool_ids == tool_call_ids:
                return assistant_idx
            return None
        
        # Start from the end and work backwards, including complete sequences only
        limited_messages = []
        included_indices = set()
        i = len(conversation_messages) - 1
        
        while i >= 0 and len(limited_messages) < num_messages:
            if i in included_indices:
                i -= 1
                continue
            
            msg = conversation_messages[i]
            
            # If this is a tool message, skip it - we'll handle it when we encounter its assistant
            if is_tool_message(msg):
                i -= 1
                continue
            elif is_assistant_with_tool_calls(msg):
                # Check if this is a complete sequence
                seq_start = get_tool_sequence_start(i)
                if seq_start == i:
                    # Complete sequence, include it
                    tool_msgs = []
                    for k in range(i + 1, len(conversation_messages)):
                        if k in included_indices:
                            break
                        next_msg = conversation_messages[k]
                        if is_tool_message(next_msg):
                            tool_msgs.append((k, next_msg))
                        else:
                            break
                    
                    sequence_size = 1 + len(tool_msgs)
                    if len(limited_messages) + sequence_size <= num_messages:
                        # Add assistant message
                        limited_messages.insert(0, msg)
                        included_indices.add(i)
                        # Add tool messages right after assistant (in order)
                        for idx, (tool_idx, tool_msg) in enumerate(tool_msgs):
                            limited_messages.insert(1 + idx, tool_msg)
                            included_indices.add(tool_idx)
                    i -= 1
                else:
                    # Incomplete sequence, skip it
                    i -= 1
            else:
                # Regular message (user, system, etc.), include it
                if len(limited_messages) < num_messages:
                    limited_messages.insert(0, msg)
                    included_indices.add(i)
                i -= 1
        
        logger.debug(f"Limited conversation history to latest {len(limited_messages)} messages (requested {num_messages})")
        return [system_message, *limited_messages]
    
    # Try with progressively fewer messages if token errors occur
    for attempt in range(max_attempts):
        # Calculate number of messages for this attempt: 7, 5, 3, 1
        if attempt == 0:
            current_max = initial_max_messages
        elif attempt == 1:
            current_max = 5
        elif attempt == 2:
            current_max = 3
        else:
            current_max = 1
        
        messages = _prepare_messages(current_max)
        
        try:
            # Make sequential calls to avoid rate limits
            # Use global rate limiter for Groq
            if provider == 'groq':
                groq_rate_limiter.wait_if_needed()
            
            # First get the main response
            response = user_llm_with_tools.invoke(messages, config=config)
            
            # Record success to reset error count
            if provider == 'groq':
                groq_rate_limiter.record_success()
            
            # Try to get lesson state, but make it optional to save tokens and avoid rate limits
            # Skip lesson_state call for Groq to reduce API calls and avoid rate limits
            lesson_state = None
            if provider != 'groq':
                # Only call lesson_state for non-Groq providers to avoid rate limits
                try:
                    # Add delay before the second call to avoid rate limits
                    time.sleep(0.5)  # 500ms for other providers
                    lesson_state = user_llm_structured_output.invoke(messages, config=config)
                except Exception as lesson_error:
                    logger.warning(f"Failed to get lesson state (non-critical): {str(lesson_error)}")
                    lesson_state = {
                        "lesson_in_progress": False,
                        "lesson_finalized": False,
                        "last_lesson_text": "",
                        "lesson_title": ""
                    }
            else:
                # For Groq, skip lesson_state to avoid rate limits and save tokens
                logger.debug("Skipping lesson_state call for Groq to avoid rate limits")
                lesson_state = {
                    "lesson_in_progress": False,
                    "lesson_finalized": False,
                    "last_lesson_text": "",
                    "lesson_title": ""
                }
          
            # lesson_state is a dict (TypedDict), so access it with dictionary syntax
            # Only finalize lesson if user explicitly requests it
            # Check the last user message for explicit finalization requests
            user_wants_to_finalize = False
            if conversation_messages:
                # Get the last user message
                last_user_msg = None
                for msg in reversed(conversation_messages):
                    from langchain_core.messages import HumanMessage
                    if isinstance(msg, HumanMessage):
                        last_user_msg = msg.content.lower() if hasattr(msg, 'content') else str(msg).lower()
                        break
                
                # Check for explicit finalization requests
                if last_user_msg:
                    finalization_keywords = [
                        'finalize', 'finalise', 'final', 'this is final', 'this is the final',
                        'i am satisfied', "i'm satisfied", 'i am done', "i'm done",
                        'complete the lesson', 'finish the lesson', 'save the lesson',
                        'this lesson is complete', 'lesson is ready', 'ready to save',
                        'finalize this lesson', 'finalise this lesson', 'make this final'
                    ]
                    user_wants_to_finalize = any(keyword in last_user_msg for keyword in finalization_keywords)
            
            # Only process if lesson_state was successfully retrieved AND user explicitly wants to finalize
            if lesson_state and lesson_state.get("lesson_finalized", False) and user_wants_to_finalize:
                # Update the lesson state
                if thread_id_str:
                    if thread_id_str not in _THREAD_METADATA:
                        _THREAD_METADATA[thread_id_str] = {}
                    _THREAD_METADATA[thread_id_str]["lesson_finalized"] = True
                    _THREAD_METADATA[thread_id_str]["last_lesson_text"] = lesson_state.get("last_lesson_text", "")
                    _THREAD_METADATA[thread_id_str]["lesson_title"] = lesson_state.get("lesson_title", "")
                    _save_metadata()
            elif lesson_state and lesson_state.get("lesson_finalized", False) and not user_wants_to_finalize:
                # LLM wants to finalize but user hasn't explicitly requested it - don't finalize
                logger.debug("LLM suggested finalization but user hasn't explicitly requested it - keeping lesson in progress")
                # Keep lesson in progress, but update the lesson text and title for display
                if thread_id_str:
                    if thread_id_str not in _THREAD_METADATA:
                        _THREAD_METADATA[thread_id_str] = {}
                    _THREAD_METADATA[thread_id_str]["lesson_finalized"] = False
                    _THREAD_METADATA[thread_id_str]["last_lesson_text"] = lesson_state.get("last_lesson_text", "")
                    _THREAD_METADATA[thread_id_str]["lesson_title"] = lesson_state.get("lesson_title", "")
                    _save_metadata()

            # Log if we had to reduce messages
            if attempt > 0:
                logger.info(f"Successfully processed request after reducing to {current_max} messages (attempt {attempt + 1})")
            
            return {"messages": [response]}
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"LLM API error in chat_node (attempt {attempt + 1} with {current_max} messages): {error_msg}")
            
            # Record 429 errors for rate limiter adjustment
            if provider == 'groq' and '429' in error_msg or 'Rate limit' in error_msg:
                groq_rate_limiter.record_429_error()
            
            # Check if it's a Groq daily token limit error (429 with type 'tokens')
            if 'Rate limit reached' in error_msg and 'tokens per day' in error_msg and 'TPD' in error_msg:
                # Parse the error to extract useful information
                import re
                try:
                    # Extract limit, used, requested, and wait time
                    limit_match = re.search(r'Limit (\d+)', error_msg)
                    used_match = re.search(r'Used (\d+)', error_msg)
                    requested_match = re.search(r'Requested (\d+)', error_msg)
                    wait_match = re.search(r'try again in ([\dm\.]+)', error_msg)
                    
                    limit = limit_match.group(1) if limit_match else '100,000'
                    used = used_match.group(1) if used_match else 'Unknown'
                    requested = requested_match.group(1) if requested_match else 'Unknown'
                    wait_time = wait_match.group(1) if wait_match else 'Unknown'
                    
                    # Format numbers with commas
                    try:
                        limit = f"{int(limit):,}"
                        used = f"{int(used):,}"
                        requested = f"{int(requested):,}"
                    except:
                        pass
                    
                    error_response = AIMessage(
                        content=(
                            f"⚠️ **Groq Daily Token Limit Reached**\n\n"
                            f"You've reached your daily token limit for Groq API:\n"
                            f"- **Limit**: {limit} tokens/day\n"
                            f"- **Used**: {used} tokens\n"
                            f"- **Requested**: {requested} tokens\n"
                            f"- **Wait Time**: {wait_time}\n\n"
                            f"Please wait for the limit to reset, or upgrade your Groq plan at "
                            f"https://console.groq.com/settings/billing\n\n"
                            f"*The limit resets daily. You can continue using the service after the reset.*"
                        )
                    )
                    logger.error(f"Groq daily token limit reached: Used {used}/{limit}, Wait {wait_time}")
                    return {"messages": [error_response]}
                except Exception as parse_error:
                    logger.error(f"Error parsing Groq token limit error: {parse_error}")
                    # Fall through to generic error handling
            
            # Check if it's a token error (context length)
            if _is_token_error(error_msg):
                # If this is not the last attempt, try with fewer messages
                if attempt < max_attempts - 1:
                    logger.info(f"Token error detected, retrying with fewer messages (current: {current_max}, next: {current_max - 2 if current_max > 2 else 1})")
                    continue  # Retry with fewer messages
                else:
                    # Last attempt failed, show error
                    logger.error(f"All retry attempts failed with token errors. Final attempt with {current_max} messages.")
                    error_response = AIMessage(
                        content=(
                            "⚠️ **Context Length Error**: The conversation is too long to process. "
                            "Please start a new conversation or upload a shorter document.\n\n"
                            f"*Error details: {error_msg}*"
                        )
                    )
                    return {"messages": [error_response]}
            else:
                # Not a token error, check if it's a connection error
                if "Connection error" in error_msg or "No connection could be made" in error_msg or "actively refused" in error_msg:
                    error_response = AIMessage(
                        content=(
                            "⚠️ **Connection Error**: Unable to connect to the AI service. "
                            "The server may be temporarily unavailable.\n\n"
                            "Please try again in a few moments, or contact support if the issue persists.\n\n"
                            f"*Error details: {error_msg}*"
                        )
                    )
                else:
                    # Generic error handling (only show if not retrying)
                    if attempt < max_attempts - 1:
                        # Try one more time with fewer messages even for non-token errors
                        logger.info(f"Non-token error detected, retrying with fewer messages (attempt {attempt + 2})")
                        continue
                    else:
                        # Final attempt failed
                        error_response = AIMessage(
                            content=(
                                "⚠️ **Error**: An error occurred while processing your request.\n\n"
                                "Please try again, or contact support if the issue persists.\n\n"
                                f"*Error details: {error_msg}*"
                            )
                        )
                
                return {"messages": [error_response]}

tool_node = ToolNode(tools)

# -------------------
# 7. Checkpointer
# -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# -------------------
# 8. Graph
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

# -------------------
# 9. Helpers
# -------------------
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def thread_has_document(thread_id: str) -> bool:
    """Check if thread has a document (check metadata)."""
    thread_id_str = str(thread_id)
    
    # Check metadata
    if thread_id_str in _THREAD_METADATA:
        return True
    
    # Reload metadata in case it was updated
    _load_metadata()
    return thread_id_str in _THREAD_METADATA


def thread_document_metadata(thread_id: str) -> dict:
    """Get document metadata for a thread. Loads from disk if needed."""
    thread_id_str = str(thread_id)
    
    # Reload metadata if not in memory
    if thread_id_str not in _THREAD_METADATA:
        _load_metadata()
    
    return _THREAD_METADATA.get(thread_id_str, {})


def update_lesson_finalized_status(thread_id: str, finalized: bool) -> bool:
    """
    Update the lesson finalized status for a thread.
    
    Args:
        thread_id: The thread ID to update
        finalized: Boolean indicating if the lesson is finalized
        
    Returns:
        True if the update was successful, False if thread not found
    """
    thread_id_str = str(thread_id)
    
    # Reload metadata if not in memory
    if thread_id_str not in _THREAD_METADATA:
        _load_metadata()
    
    # Check if thread exists
    if thread_id_str not in _THREAD_METADATA:
        return False
    
    # Update the finalized status
    _THREAD_METADATA[thread_id_str]["lesson_finalized"] = finalized
    
    # Save metadata to disk
    _save_metadata()
    
    return True

# Load metadata on module import
_load_metadata()