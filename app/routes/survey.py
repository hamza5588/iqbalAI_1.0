from flask import Blueprint, request, jsonify
from app.models.models import SurveyModel
from app.utils.auth import login_required
from app.utils.logger import logger

survey_bp = Blueprint('survey', __name__)

@survey_bp.route('/api/survey', methods=['POST'])
@login_required
def submit_survey():
    """Submit a survey response"""
    try:
        data = request.get_json()
        rating = data.get('rating')
        message = data.get('message')
        
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 10:
            return jsonify({'error': 'Invalid rating. Must be an integer between 1 and 10'}), 400
        
        survey_model = SurveyModel(user_id=request.user_id)
        response_id = survey_model.save_survey_response(rating=rating, message=message)
        
        return jsonify({
            'message': 'Survey response submitted successfully',
            'response_id': response_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error submitting survey: {str(e)}")
        return jsonify({'error': 'Failed to submit survey response'}), 500

@survey_bp.route('/api/survey/responses', methods=['GET'])
@login_required
def get_survey_responses():
    """Get all survey responses for the current user"""
    try:
        survey_model = SurveyModel(user_id=request.user_id)
        responses = survey_model.get_user_survey_responses()
        
        return jsonify({
            'responses': responses
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving survey responses: {str(e)}")
        return jsonify({'error': 'Failed to retrieve survey responses'}), 500 