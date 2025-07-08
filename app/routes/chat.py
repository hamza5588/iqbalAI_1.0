# app/routes/chat.py
from flask import Blueprint, redirect, request, session, jsonify, render_template, url_for
from app.services import ChatService, PromptService
from app.models.models import SurveyModel
# from app.utils.decorators import login_required
from app.utils.auth import login_required
import logging
from app.utils.db import get_db

logger = logging.getLogger(__name__)
bp = Blueprint('chat', __name__)

@bp.route('/health')
def health_check():
    """Health check endpoint for container orchestration"""
    return jsonify({'status': 'healthy'}), 200

@bp.route('/')
@login_required
def index():
    """Render the main chat interface"""
    try:
        # Check if user has submitted survey
        survey_model = SurveyModel(session['user_id'])
        has_submitted_survey = survey_model.has_submitted_survey()
        
        return render_template('chat.html', has_submitted_survey=has_submitted_survey)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('chat.html', has_submitted_survey=False)

# Add these routes to chat.py

from app.services import PromptService

@bp.route('/get_prompt')
def get_prompt():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        prompt_service = PromptService(session['user_id'])
        current_prompt = prompt_service.get_prompt()
        return jsonify({'prompt': current_prompt})
    except Exception as e:
        logger.error(f"Error retrieving prompt: {str(e)}")
        return jsonify({'error': 'Failed to retrieve prompt'}), 500

@bp.route('/update_prompt', methods=['POST'])
def update_prompt():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        data = request.json
        new_prompt = data.get('prompt')
   
        
        if not new_prompt:
            return jsonify({'error': 'Prompt is required'}), 400
            
        prompt_service = PromptService(session['user_id'])
        prompt_service.update_prompt(new_prompt)
        
        return jsonify({
            'success': True,
            'message': 'Prompt updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating prompt: {str(e)}")
        return jsonify({'error': 'Failed to update prompt'}), 500

@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages and generate responses"""
    try:
        data = request.json
        user_input = data.get('input', '').strip()
        conversation_id = data.get('conversation_id')

        if not user_input:
            return jsonify({'error': 'Empty message'}), 400

        # Initialize services
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        prompt_service = PromptService(session['user_id'])

        # Get system prompt
        system_prompt = prompt_service.get_prompt()

        # Process message and generate response
        try:
            result = chat_service.process_message(
                message=user_input,
                conversation_id=conversation_id
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return jsonify({
                'error': """1:Your free key has expired,please login after 24 hours
                            2:Create another gmail account and login
                            3:Login to paid service-avalible in oct 2025"""
            }), 500

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@bp.route('/create_conversation', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.json
        title = data.get('title', 'New Conversation')
        
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        conversation_id = chat_service.create_conversation(title)
        
        return jsonify({
            'conversation_id': conversation_id,
            'title': title
        })
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        return jsonify({'error': 'Failed to create conversation'}), 500

@bp.route('/get_conversations')
@login_required
def get_conversations():
    """Get user's recent conversations"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        conversations = chat_service.get_recent_conversations()
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error retrieving conversations: {str(e)}")
        return jsonify({'error': 'Failed to retrieve conversations'}), 500

@bp.route('/get_messages/<int:conversation_id>')
@login_required
def get_messages(conversation_id):
    """Get messages for a specific conversation"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        messages = chat_service.get_conversation_messages(conversation_id)
        return jsonify(messages)
    except Exception as e:
        logger.error(f"Error retrieving messages: {str(e)}")
        return jsonify({'error': 'Failed to retrieve messages'}), 500

@bp.route('/delete_conversation/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        chat_service.delete_conversation(conversation_id)
        return jsonify({'message': 'Conversation deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': 'Failed to delete conversation'}), 500

@bp.route('/delete_all_conversations', methods=['DELETE'])
@login_required
def delete_all_conversations():
    """Delete all conversations for the current user"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        chat_service.reset_all_conversations()
        return jsonify({'message': 'All conversations deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting all conversations: {str(e)}")
        return jsonify({'error': 'Failed to delete conversations'}), 500

@bp.route('/download_chat/<int:conversation_id>')
@login_required
def download_chat(conversation_id):
    """Download a chat conversation as a Word document"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        messages = chat_service.get_conversation_messages(conversation_id)
        
        # Create a new Word document
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Add title
        title = doc.add_heading('Chat Conversation', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add messages
        for msg in messages:
            role = "Mr. Potter" if msg['role'] == 'bot' else "User"
            p = doc.add_paragraph()
            p.add_run(f"{role}: ").bold = True
            p.add_run(msg['message'])
            p.paragraph_format.space_after = Pt(12)
        
        # Save the document to a BytesIO object
        from io import BytesIO
        doc_io = BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)
        
        # Create response with appropriate headers
        from flask import make_response
        response = make_response(doc_io.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=chat_conversation_{conversation_id}.docx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        return response
    except Exception as e:
        logger.error(f"Error downloading chat: {str(e)}")
        return jsonify({'error': 'Failed to download chat'}), 500

@bp.route('/get_token_usage')
@login_required
def get_token_usage():
    """Get current token usage information"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        token_usage = chat_service.get_token_usage()
        return jsonify(token_usage)
    except Exception as e:
        logger.error(f"Error getting token usage: {str(e)}")
        return jsonify({
            'daily_limit': '100,000',
            'used_tokens': '0',
            'requested_tokens': '0',
            'wait_time': None
        }), 500
    



# TOKEN USAGE ROUTE 

@bp.route('/token_status', methods=['GET'])
@login_required
def get_token_status():
    try:
        # Get current API key from session
        current_api_key = session.get('groq_api_key')
        
        # Initialize chat service
        chat_service = ChatService(session['user_id'], current_api_key)
        
        # Verify the API key matches what's being used
        if chat_service.chat_model.api_key != current_api_key:
            chat_service.chat_model.api_key = current_api_key  # This will trigger reset
            
        token_status = chat_service.chat_model.get_token_status()
        
        return jsonify({
            'used': token_status['used'],
            'remaining': token_status['remaining'],
            'limit': token_status['limit'],
            'reset_in': token_status['reset_in'],
            'api_key_changed': False  # Can be used by frontend if needed
        })
    except Exception as e:
        logger.error(f"Error getting token status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/user_info')
def get_user_info():
    """Get current user information including role"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from app.models import UserModel
        user_model = UserModel(session['user_id'])
        user_info = UserModel.get_user_by_id(session['user_id'])
        
        if not user_info:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_info['id'],
                'username': user_info['username'],
                'role': user_info.get('role', 'student'),
                'class_standard': user_info['class_standard'],
                'medium': user_info['medium']
            }
        })
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500