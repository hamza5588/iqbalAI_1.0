# app/routes/chat.py
from flask import Blueprint, redirect, request, session, jsonify, render_template, url_for
from app.services import ChatService, PromptService
from app.models.models import SurveyModel
from app.utils.decorators import login_required
import logging

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
    return render_template('chat.html')

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
                conversation_id=conversation_id,
                system_prompt=system_prompt
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return jsonify({
                'error': 'Your API key has expired. Please update it from the sidebar where the modal is displayed and enter the new API key here'
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
    """Download a chat conversation as a text file"""
    try:
        chat_service = ChatService(session['user_id'], session['groq_api_key'])
        messages = chat_service.get_conversation_messages(conversation_id)
        
        # Format messages for download
        formatted_messages = []
        for msg in messages:
            role = "Mr. Potter" if msg['role'] == 'bot' else "User"
            formatted_messages.append(f"{role}: {msg['message']}\n")
        
        # Create the text content
        content = "Chat Conversation\n" + "=" * 20 + "\n\n" + "".join(formatted_messages)
        
        # Create response with appropriate headers
        from flask import make_response
        response = make_response(content)
        response.headers["Content-Disposition"] = f"attachment; filename=chat_conversation_{conversation_id}.txt"
        response.headers["Content-type"] = "text/plain"
        
        return response
    except Exception as e:
        logger.error(f"Error downloading chat: {str(e)}")
        return jsonify({'error': 'Failed to download chat'}), 500

@bp.route('/submit_survey', methods=['POST'])
@login_required
def submit_survey():
    """Handle survey submission"""
    try:
        data = request.get_json()
        logger.info(f"Received survey data: {data}")
        
        rating = data.get('rating')
        user_id = session.get('user_id')
        
        logger.info(f"Processing survey - Rating: {rating}, User ID: {user_id}")

        if not user_id:
            logger.error("Survey submission failed: No user_id in session")
            return jsonify({'error': 'Not authenticated'}), 401

        if not isinstance(rating, (int, float)):
            logger.error(f"Survey submission failed: Rating is not a number - Type: {type(rating)}")
            return jsonify({'error': 'Invalid rating. Must be a number between 1 and 10'}), 400
            
        # Convert to integer if it's a float
        rating = int(rating)

        if rating < 1 or rating > 10:  # Updated to match NPS scale
            logger.error(f"Survey submission failed: Rating {rating} is out of range")
            return jsonify({'error': 'Invalid rating. Must be a number between 1 and 10'}), 400

        # Check if user has already submitted
        survey_model = SurveyModel(user_id)
        if survey_model.has_submitted_survey():
            logger.warning(f"User {user_id} attempted to submit multiple surveys")
            return jsonify({'error': 'Survey already submitted'}), 400

        # Create survey model instance and save response
        logger.info(f"Saving survey response - User: {user_id}, Rating: {rating}")
        survey_model.save_survey_response(rating)

        logger.info(f"Survey successfully submitted - User ID: {user_id}, Rating: {rating}")
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        logger.error(f"Survey submission failed with exception: {str(e)}")
        logger.exception("Full traceback:")  # This will log the full stack trace
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/check_survey_status')
@login_required
def check_survey_status():
    """Check if the current user has submitted a survey"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            logger.warning("Survey status check failed: No user_id in session")
            return jsonify({'error': 'Not authenticated'}), 401
            
        logger.info(f"Checking survey status for user_id: {user_id}")
        survey_model = SurveyModel(user_id)
        has_submitted = survey_model.has_submitted_survey()
        
        status_msg = f"User {user_id} has {'submitted' if has_submitted else 'not submitted'} the survey"
        logger.info(status_msg)
        print(f"\n=== Survey Status ===\n{status_msg}\n===================")
        
        return jsonify({
            'has_submitted': has_submitted
        })
        
    except Exception as e:
        logger.error(f"Error checking survey status: {str(e)}")
        return jsonify({'error': 'Failed to check survey status'}), 500

@bp.route('/test_survey_db')
@login_required
def test_survey_db():
    """Test route to verify survey database operations"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        survey_model = SurveyModel(user_id)
        
        # Test database connection and operations
        has_submitted = survey_model.has_submitted_survey()
        all_responses = survey_model.get_user_survey_responses()
        
        return jsonify({
            'user_id': user_id,
            'has_submitted': has_submitted,
            'responses': all_responses
        })
        
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return jsonify({'error': f'Database test failed: {str(e)}'}), 500