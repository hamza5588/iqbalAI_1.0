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
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
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
# 1. LLM + embeddings
# -------------------
# Use dynamic LLM factory - supports OpenAI and vLLM via environment variables
llm = create_llm(temperature=0.7)
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

def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF and store metadata inside the vector DB.
    Adds documents to the shared vector store with user_id and thread_id metadata.
    """
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    thread_id_str = str(thread_id)
    user_id = _extract_user_id_from_thread_id(thread_id_str)
    
    if user_id is None:
        raise ValueError(f"Could not extract user_id from thread_id: {thread_id_str}")
    
    # Save the original PDF file
    safe_filename = filename or f"document_{thread_id_str}.pdf"
    # Sanitize filename
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._- ")
    file_path = UPLOADED_FILES_DIR / f"{thread_id_str}_{safe_filename}"
    
    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    # Create temp file for PDF loader
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()  # each item = 1 PDF page
        
        # Calculate total number of pages - ensure we have valid pages
        num_pages = len(docs)
        if num_pages == 0:
            raise ValueError("PDF appears to be empty or could not be loaded. No pages found.")
        
        # Verify pages have content
        valid_pages = [doc for doc in docs if doc.page_content and doc.page_content.strip()]
        if len(valid_pages) == 0:
            raise ValueError("PDF loaded but contains no extractable text content.")
        
        # Use valid pages count if different
        if len(valid_pages) != num_pages:
            logger.warning(f"PDF has {num_pages} pages but only {len(valid_pages)} contain extractable text")
            # Still use original count for metadata, but note the difference
            num_pages = len(docs)  # Keep original page count

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

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

        # Split docs, keeping metadata automatically
        chunks = splitter.split_documents(docs)

        # Add even richer metadata to each chunk
        for c in chunks:
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

        # Load or create shared vector store
        global _SHARED_VECTOR_STORE
        vector_store = _load_shared_vector_store()
        
        if vector_store is None:
            # Create new vector store
            vector_store = FAISS.from_documents(chunks, embeddings)
            _SHARED_VECTOR_STORE = vector_store
        else:
            # Add new documents to existing vector store
            vector_store.add_documents(chunks)
            _SHARED_VECTOR_STORE = vector_store

        # Save vector store to disk
        _save_shared_vector_store()

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

        return {
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
llm_with_tools = llm.bind_tools(tools)

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
llm_structured_output = llm.with_structured_output(LessonState)

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
    
    # Get custom prompt from database (user-level, applies to all threads)
    custom_prompt = _get_rag_prompt(user_id, thread_id_str)
    
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
            f"Example: rag_tool(query='user question here', thread_id='{thread_id}')\n\n"
            f"When you call rag_tool, it will return information including:\n"
            f"- The relevant content from the PDF\n"
            f"- Metadata about the pages (including page numbers)\n"
            f"- The total number of pages in the PDF (num_pages or pages field)\n"
            f"- The source filename\n\n"
            f"You can also use web search, stock price, and calculator tools when helpful.\n"
            f"But for PDF-related questions, ALWAYS use rag_tool first with thread_id='{thread_id}'.\n"
            f"When asked about the number of pages, use the num_pages or pages field from the rag_tool response.\n"
            f"Always return the response in markdown format for better readability. Recognize the equations code structure etc.\n\n"
            f"IMPORTANT: When you finalize a lesson (set lesson_finalized to true), you MUST provide a meaningful lesson_title. "
            f"The lesson_title should be a concise, descriptive title that summarizes the main topic of the lesson (e.g., 'Introduction to Newton's Laws', 'Photosynthesis: How Plants Make Food'). "
            f"Do NOT use generic titles like 'Lesson' or 'Lesson from Chat'. Create a specific, educational title that reflects the lesson content."
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
        """Prepare messages list with specified number of conversation messages."""
        if len(conversation_messages) > num_messages:
            limited_messages = conversation_messages[-num_messages:]
            logger.debug(f"Limited conversation history to latest {num_messages} messages")
        else:
            limited_messages = conversation_messages
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
            response = llm_with_tools.invoke(messages, config=config)
            lesson_state = llm_structured_output.invoke(messages, config=config)
          
            # lesson_state is a dict (TypedDict), so access it with dictionary syntax
            if lesson_state.get("lesson_finalized", False):
                # Update the lesson state
                if thread_id_str:
                    if thread_id_str not in _THREAD_METADATA:
                        _THREAD_METADATA[thread_id_str] = {}
                    _THREAD_METADATA[thread_id_str]["lesson_finalized"] = True
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
            
            # Check if it's a token error
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