from flask import Blueprint, request, jsonify, session, render_template
from app.utils.auth import login_required
from app.utils.rag_service import (
    ingest_pdf,
    chatbot,
    thread_has_document,
    thread_document_metadata,
    update_lesson_finalized_status
)
from app.utils.db import get_db
from app.models.database_models import RAGThread, RAGPrompt
from langchain_core.messages import HumanMessage
import logging
import uuid
from datetime import datetime
import os
from tempfile import NamedTemporaryFile

from openai import OpenAI

logger = logging.getLogger(__name__)
bp = Blueprint('rag', __name__)


def _get_openai_client():
    """
    Lazily create an OpenAI client for Whisper STT.
    Expects OPENAI_API_KEY in environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def _get_thread_id(user_id: int, conversation_id: int = None) -> str:
    """
    Generate a unique thread_id for the RAG service.
    Creates a new unique thread ID for each upload.
    """
    if conversation_id:
        return f"user_{user_id}_conv_{conversation_id}"
    # Generate unique thread ID with timestamp and UUID
    unique_id = str(uuid.uuid4())[:8]
    timestamp = int(datetime.utcnow().timestamp())
    return f"user_{user_id}_thread_{timestamp}_{unique_id}"


@bp.route('/chatbot', methods=['GET'])
@login_required
def chatbot_page():
    """
    Render the PDF chat interface.
    """
    try:
        # Redirect to main chat interface instead of separate chatbot page
        return render_template('chat.html')
    except Exception as e:
        logger.error(f"Error rendering chatbot page: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to render page: {str(e)}'}), 500


def _validate_thread_id(thread_id: str, user_id: int) -> bool:
    """
    Validate that a thread_id belongs to the current user.
    Prevents users from accessing other users' threads.
    """
    if not thread_id:
        return False
    
    # Thread ID must start with the user's ID
    expected_prefix = f"user_{user_id}_"
    return thread_id.startswith(expected_prefix)


@bp.route('/ingest', methods=['POST'])
@login_required
def ingest():
    """
    Upload and ingest a PDF document for RAG.
    Expects a file in the 'file' field of the request.
    Optionally accepts 'thread_id' or 'conversation_id' in form data.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session['user_id']
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400

        # Get thread_id from request or create new thread
        conversation_id = request.form.get('conversation_id', type=int)
        provided_thread_id = request.form.get('thread_id')
        create_new_thread = request.form.get('create_new_thread', 'true').lower() == 'true'
        
        # If thread_id is provided and we're not creating a new thread, validate it belongs to this user
        if provided_thread_id and not create_new_thread:
            if not _validate_thread_id(provided_thread_id, user_id):
                return jsonify({'error': 'Invalid thread_id. You can only use your own threads.'}), 403
            
            # Check if thread already has a document - only one document per thread allowed
            if thread_has_document(provided_thread_id):
                return jsonify({
                    'error': 'This thread already has a document. Only one document per thread is allowed. Please create a new thread for a new document.'
                }), 400
            
            thread_id = provided_thread_id
        else:
            # Always create a new thread for new uploads
            thread_id = _get_thread_id(user_id, conversation_id)
        
        filename = file.filename

        # Read file bytes
        file_bytes = file.read()
        if not file_bytes:
            return jsonify({'error': 'File is empty'}), 400

        # Ingest the PDF
        result = ingest_pdf(
            file_bytes=file_bytes,
            thread_id=thread_id,
            filename=filename
        )

        # Save thread to database
        db = get_db()
        try:
            # Check if thread already exists
            existing_thread = db.query(RAGThread).filter_by(thread_id=thread_id).first()
            if not existing_thread:
                # Create new thread record
                thread_name = f"Thread {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                rag_thread = RAGThread(
                    user_id=user_id,
                    thread_id=thread_id,
                    name=thread_name,
                    filename=filename
                )
                db.add(rag_thread)
                db.commit()
                db.refresh(rag_thread)
            else:
                # Update existing thread (only if it doesn't already have a document)
                # This should not happen if create_new_thread is true, but handle it safely
                if not thread_has_document(thread_id):
                    existing_thread.filename = filename
                    existing_thread.updated_at = datetime.utcnow()
                    db.commit()
                else:
                    logger.warning(f"Attempted to update thread {thread_id} that already has a document")
        except Exception as e:
            logger.error(f"Error saving thread to database: {str(e)}")
            db.rollback()
            # Continue even if database save fails

        return jsonify({
            'success': True,
            'message': 'PDF ingested successfully',
            'thread_id': thread_id,
            'filename': result['filename'],
            'documents': result.get('documents', result.get('num_pages', 0)),  # Backward compatibility
            'num_pages': result.get('num_pages', result.get('documents', 0)),  # Explicit page count
            'pages': result.get('pages', result.get('num_pages', result.get('documents', 0))),  # Alternative key
            'chunks': result['chunks']
        })

    except ValueError as e:
        logger.error(f"Value error in ingest: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error ingesting PDF: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to ingest PDF: {str(e)}'}), 500


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    Chat with the RAG-enabled chatbot.
    Accepts JSON or form-data with 'message' and optionally 'thread_id' or 'conversation_id'.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']

        # If audio is sent (voice input), transcribe it first using Whisper
        audio_text = None
        try:
            audio_file = request.files.get('audio')
            if audio_file and audio_file.filename:
                client = _get_openai_client()
                with NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    audio_file.save(tmp.name)
                    tmp_path = tmp.name

                with open(tmp_path, "rb") as f:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="json"
                    )

                audio_text = getattr(transcription, "text", None) or transcription.get("text")
        except Exception as stt_error:
            logger.error(f"Error transcribing audio for RAG chat: {str(stt_error)}", exc_info=True)
            # Continue without audio_text; will fall back to text message if provided
        
        # Try to get JSON data first
        data = request.get_json(force=True, silent=True)
        
        # If no JSON data, try form data
        if not data:
            if request.form:
                data = {
                    'message': request.form.get('message', '').strip(),
                    'thread_id': request.form.get('thread_id'),
                    'conversation_id': request.form.get('conversation_id', type=int)
                }
            elif request.args:  # Also support query parameters
                data = {
                    'message': request.args.get('message', '').strip(),
                    'thread_id': request.args.get('thread_id'),
                    'conversation_id': request.args.get('conversation_id', type=int)
                }
            elif audio_text:
                # Pure audio request – use transcribed text as the message
                data = {
                    'message': audio_text,
                    'thread_id': request.args.get('thread_id') if request.args else None,
                    'conversation_id': request.args.get('conversation_id', type=int) if request.args else None
                }
        
        if not data:
            return jsonify({'error': 'No data provided. Please send JSON, form-data with \"message\" field, or an audio file.'}), 400

        message = data.get('message', '').strip()
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get thread_id from request or generate default
        provided_thread_id = data.get('thread_id')
        conversation_id = data.get('conversation_id')
        
        # If thread_id is provided, validate it belongs to this user
        if provided_thread_id:
            if not _validate_thread_id(provided_thread_id, user_id):
                return jsonify({'error': 'Invalid thread_id. You can only access your own threads.'}), 403
            thread_id = provided_thread_id
        else:
            # Generate thread_id based on user_id
            thread_id = _get_thread_id(user_id, conversation_id)

        # Prepare config for LangGraph
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        # Create HumanMessage
        human_message = HumanMessage(content=message)

        # Invoke the chatbot - LangGraph returns the final state
        state = chatbot.invoke(
            {"messages": [human_message]},
            config=config
        )

        # Extract the last message from the state
        messages = state.get("messages", [])
        if not messages:
            response_content = "I'm sorry, I couldn't generate a response."
        else:
            # Get the last message (should be the AI response)
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                response_content = last_msg.content
            elif isinstance(last_msg, dict):
                response_content = last_msg.get('content', str(last_msg))
            else:
                response_content = str(last_msg)

        # Get thread metadata to check if lesson is finalized
        metadata = thread_document_metadata(thread_id)
        lesson_finalized = metadata.get("lesson_finalized", False)
        last_lesson_text = metadata.get("last_lesson_text", "")
        lesson_title = metadata.get("lesson_title", "")

        return jsonify({
            'success': True,
            'message': response_content,
            'thread_id': thread_id,
            'has_document': thread_has_document(thread_id),
            'lesson_finalized': lesson_finalized,
            'last_lesson_text': last_lesson_text,
            'lesson_title': lesson_title
        })

    except Exception as e:
        logger.error(f"Error in RAG chat: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to process chat: {str(e)}'}), 500


@bp.route('/thread/status/<thread_id>', methods=['GET'])
@login_required
def get_thread_status(thread_id):
    """
    Get the status of a thread, including whether it has a document.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        # Validate thread_id belongs to this user
        if not _validate_thread_id(thread_id, user_id):
            return jsonify({'error': 'Access denied. You can only access your own threads.'}), 403

        has_doc = thread_has_document(thread_id)
        metadata = thread_document_metadata(thread_id) if has_doc else {}

        return jsonify({
            'thread_id': thread_id,
            'has_document': has_doc,
            'metadata': metadata
        })

    except Exception as e:
        logger.error(f"Error getting thread status: {str(e)}")
        return jsonify({'error': f'Failed to get thread status: {str(e)}'}), 500


@bp.route('/thread/document/<thread_id>', methods=['GET'])
@login_required
def get_thread_document(thread_id):
    """
    Get document metadata for a thread.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        # Validate thread_id belongs to this user
        if not _validate_thread_id(thread_id, user_id):
            return jsonify({'error': 'Access denied. You can only access your own threads.'}), 403

        if not thread_has_document(thread_id):
            return jsonify({
                'error': 'No document found for this thread',
                'thread_id': thread_id
            }), 404

        metadata = thread_document_metadata(thread_id)
        return jsonify({
            'thread_id': thread_id,
            'metadata': metadata
        })

    except Exception as e:
        logger.error(f"Error getting thread document: {str(e)}")
        return jsonify({'error': f'Failed to get thread document: {str(e)}'}), 500


@bp.route('/threads', methods=['GET'])
@login_required
def get_threads():
    """
    Get all RAG threads for the current user, ordered by most recent first.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        db = get_db()
        try:
            # Get all threads for this user, ordered by most recent first
            threads = db.query(RAGThread).filter_by(user_id=user_id).order_by(RAGThread.created_at.desc()).all()
            
            threads_list = []
            for thread in threads:
                threads_list.append({
                    'thread_id': thread.thread_id,
                    'name': thread.name,
                    'filename': thread.filename,
                    'created_at': thread.created_at.isoformat() if thread.created_at else None,
                    'updated_at': thread.updated_at.isoformat() if thread.updated_at else None,
                    'has_document': thread_has_document(thread.thread_id)
                })
            
            return jsonify({
                'success': True,
                'threads': threads_list
            })
        except Exception as e:
            logger.error(f"Error retrieving threads from database: {str(e)}")
            return jsonify({'error': f'Failed to retrieve threads: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error getting threads: {str(e)}")
        return jsonify({'error': f'Failed to get threads: {str(e)}'}), 500


@bp.route('/prompt', methods=['GET'])
@login_required
def get_rag_prompt():
    """
    Get the custom RAG prompt for the current user.
    Prompts are user-level and apply to all threads for that user.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        db = get_db()
        try:
            # Get user-specific prompt (applies to all threads)
            prompt_obj = db.query(RAGPrompt).filter(
                RAGPrompt.user_id == user_id,
                RAGPrompt.thread_id.is_(None)
            ).order_by(RAGPrompt.updated_at.desc()).first()
            
            if prompt_obj:
                return jsonify({
                    'success': True,
                    'prompt': prompt_obj.prompt,
                    'thread_id': None,
                    'updated_at': prompt_obj.updated_at.isoformat() if prompt_obj.updated_at else None
                })
            else:
                return jsonify({
                    'success': True,
                    'prompt': None,
                    'message': 'No custom prompt set'
                })
        except Exception as e:
            logger.error(f"Error retrieving RAG prompt: {str(e)}")
            return jsonify({'error': f'Failed to retrieve prompt: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error getting RAG prompt: {str(e)}")
        return jsonify({'error': f'Failed to get prompt: {str(e)}'}), 500


@bp.route('/prompt', methods=['POST'])
@login_required
def set_rag_prompt():
    """
    Set or update the custom RAG prompt for the current user.
    Prompts are user-level and apply to all threads for that user.
    Thread_id parameter is ignored - prompts always apply to all threads.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        db = get_db()
        try:
            # Delete existing user-level prompt (thread_id is always None)
            db.query(RAGPrompt).filter(
                RAGPrompt.user_id == user_id,
                RAGPrompt.thread_id.is_(None)
            ).delete()
            
            # Create new user-level prompt (applies to all threads)
            rag_prompt = RAGPrompt(
                user_id=user_id,
                thread_id=None,  # Always None - prompts are user-level
                prompt=prompt
            )
            db.add(rag_prompt)
            db.commit()
            db.refresh(rag_prompt)
            
            return jsonify({
                'success': True,
                'message': 'Prompt saved successfully. It will apply to all your threads.',
                'prompt_id': rag_prompt.id,
                'thread_id': None
            })
        except Exception as e:
            logger.error(f"Error saving RAG prompt: {str(e)}")
            db.rollback()
            return jsonify({'error': f'Failed to save prompt: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error setting RAG prompt: {str(e)}")
        return jsonify({'error': f'Failed to set prompt: {str(e)}'}), 500


@bp.route('/prompt', methods=['DELETE'])
@login_required
def delete_rag_prompt():
    """
    Delete the custom RAG prompt for the current user.
    Prompts are user-level and apply to all threads.
    Thread_id parameter is ignored - always deletes the user-level prompt.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        db = get_db()
        try:
            # Delete user-level prompt (thread_id is always None)
            deleted_count = db.query(RAGPrompt).filter(
                RAGPrompt.user_id == user_id,
                RAGPrompt.thread_id.is_(None)
            ).delete()
            db.commit()
            
            if deleted_count > 0:
                return jsonify({
                    'success': True,
                    'message': 'Prompt deleted successfully'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'No prompt found to delete'
                })
        except Exception as e:
            logger.error(f"Error deleting RAG prompt: {str(e)}")
            db.rollback()
            return jsonify({'error': f'Failed to delete prompt: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error deleting RAG prompt: {str(e)}")
        return jsonify({'error': f'Failed to delete prompt: {str(e)}'}), 500


@bp.route('/thread/<thread_id>/lesson-finalized', methods=['PUT'])
@login_required
def update_lesson_finalized(thread_id):
    """
    Update the lesson_finalized status for a thread.
    Expects JSON with 'finalized' boolean field.
    """
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = session['user_id']
        
        # Validate thread_id belongs to this user
        if not _validate_thread_id(thread_id, user_id):
            return jsonify({'error': 'Access denied. You can only access your own threads.'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        finalized = data.get('finalized')
        if not isinstance(finalized, bool):
            return jsonify({'error': 'finalized must be a boolean value'}), 400

        # Update the status
        success = update_lesson_finalized_status(thread_id, finalized)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Lesson finalized status updated to {finalized}',
                'thread_id': thread_id,
                'finalized': finalized
            })
        else:
            return jsonify({
                'error': 'Thread not found or no document associated with this thread'
            }), 404

    except Exception as e:
        logger.error(f"Error updating lesson finalized status: {str(e)}")
        return jsonify({'error': f'Failed to update lesson finalized status: {str(e)}'}), 500

