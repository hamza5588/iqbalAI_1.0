from flask import Blueprint, request, jsonify, session
from app.services.chatbot_service import DocumentChatBot
from app.utils.auth import login_required
import os

bp = Blueprint('chatbot', __name__)

@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    print("\n=== Received new chat request ===")
    data = request.get_json()
    print(f"Request data: {data}")  # Debug log
    user_message = data.get("message", "")
    user_id = session.get('user_id')
    
    print(f"User ID from session: {user_id}")  # Debug log

    try:
        # Create chatbot instance with user_id to get API key from database
        chatbot = DocumentChatBot(user_id=user_id)
        print(f"Chatbot created successfully with API key: {chatbot.groq_api_key[:10]}...")  # Debug log (show first 10 chars)
        chatbot_response = chatbot.get_response(user_message)
        print(f"Chatbot response: {chatbot_response}")  # Debug log
        return jsonify(chatbot_response)
    except ValueError as e:
        print(f"ValueError in chat route: {str(e)}")  # Debug log
        return jsonify({
            "redirect": True,
            "message": "Please set up your API key in your account settings.",
            "whatsapp_url": ""
        }), 400
    except Exception as e:
        print(f"Error in chat route: {str(e)}")  # Debug log
        return jsonify({
            "redirect": True,
            "message": "Sorry, I'm having trouble connecting. Please try again later.",
            "whatsapp_url": ""
        }), 500
    
