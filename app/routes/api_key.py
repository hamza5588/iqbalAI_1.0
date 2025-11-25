from flask import Blueprint, request, jsonify, session
from app.models import UserModel
from app.models.database_models import User as DBUser
from app.services import ChatService
from app.utils.db import get_db
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('api_key', __name__)

@bp.route('/update_api_key', methods=['POST'])
def update_api_key():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.json
        new_api_key = data.get('api_key')
        
        if not new_api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Test the API key by making a simple request first
        try:
            chat_service = ChatService(session['user_id'], new_api_key)
            chat_service.chat_model.generate_response("test")
        except Exception as e:
            logger.error(f"Invalid API key: {str(e)}")
            return jsonify({'error': 'Invalid API key'}), 400

        # If API key is valid, update in database
        user_model = UserModel(session['user_id'])
        user_model.update_api_key(new_api_key)
        
        # Update session with new API key
        session.pop('groq_api_key', None)  # Remove old key
        session['groq_api_key'] = new_api_key  # Set new key
        session.modified = True  # Mark session as modified
        
        # Verify the update by checking the database directly
        db = get_db()
        updated_user = db.query(DBUser).filter(DBUser.id == session['user_id']).first()
        
        if not updated_user or updated_user.groq_api_key != new_api_key:
            logger.error("Failed to verify API key update in database")
            return jsonify({'error': 'Failed to verify API key update'}), 500

        return jsonify({
            'success': True,
            'message': 'API key updated successfully'
        })

    except Exception as e:
        logger.error(f"API key update error: {str(e)}")
        return jsonify({'error': 'Failed to update API key'}), 500

@bp.route('/check_api_key_status')
def check_api_key_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Check if API key exists in session
        has_api_key = bool(session.get('groq_api_key'))
        
        # If API key exists, verify it works
        if has_api_key:
            try:
                chat_service = ChatService(session['user_id'], session['groq_api_key'])
                # Use a minimal test message to avoid rate limits
                chat_service.chat_model.generate_response("Hi")
            except Exception as e:
                logger.error(f"Invalid API key: {str(e)}")
                has_api_key = False
                
        return jsonify({
            'has_api_key': has_api_key
        })
        
    except Exception as e:
        logger.error(f"API key status check error: {str(e)}")
        return jsonify({'error': 'Failed to check API key status'}), 500 