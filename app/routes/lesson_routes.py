from flask import Blueprint, request, jsonify, session, send_file
from app.models.models import UserModel, LessonModel
from app.services.lesson_service import LessonService
from app.utils.decorators import login_required, teacher_required, student_required
from werkzeug.datastructures import FileStorage
import logging
import os
from io import BytesIO

logger = logging.getLogger(__name__)
bp = Blueprint('lesson_routes', __name__)

@bp.route('/create_lesson', methods=['POST'])
@teacher_required
def create_lesson():
    """Create a new lesson (teacher only)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Get form data for lesson configuration
        lesson_title = request.form.get('lessonTitle', '')
        learning_objective = request.form.get('learningObjective', '')
        focus_area = request.form.get('focusArea', '')
        grade_level = request.form.get('gradeLevel', '')
        additional_notes = request.form.get('additionalNotes', '')
        
        # Validate required fields
        if not lesson_title or not learning_objective or not focus_area or not grade_level:
            return jsonify({'error': 'All required fields must be filled'}), 400
        
        # Check file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'File type not supported. Please upload PDF, DOC, DOCX, or TXT files.'}), 400
        
        # Get API key from session
        api_key = session.get('groq_api_key')
        if not api_key:
            return jsonify({'error': 'API key not configured. Please set your API key first.'}), 400
        
        # Generate lesson using LessonService
        lesson_service = LessonService(api_key=api_key)
        lesson_details = {
            'title': lesson_title,
            'learning_objective': learning_objective,
            'focus_area': focus_area,
            'grade_level': grade_level,
            'additional_notes': additional_notes
        }
        
        result = lesson_service.process_file(file, lesson_details)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'details': result.get('details', '')
            }), 500
        
        # Store lesson in database
        lesson_id = LessonModel.create_lesson(
            teacher_id=session['user_id'],
            title=lesson_title,
            summary=result['lesson'].get('summary', ''),
            learning_objectives=learning_objective,
            focus_area=focus_area,
            grade_level=grade_level,
            content=result['lesson'].get('content', result['lesson'].get('summary', '')),
            file_name=file.filename
        )
        
        return jsonify({
            'success': True,
            'lesson_id': lesson_id,
            'lesson': result['lesson'],
            'message': 'Lesson created successfully!'
        })
        
    except Exception as e:
        logger.error(f"Lesson creation error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to create lesson: {str(e)}'}), 500

@bp.route('/my_lessons', methods=['GET'])
@teacher_required
def get_my_lessons():
    """Get all lessons created by the current teacher"""
    try:
        lessons = LessonModel.get_lessons_by_teacher(session['user_id'])
        return jsonify({
            'success': True,
            'lessons': lessons
        })
    except Exception as e:
        logger.error(f"Error getting teacher lessons: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get lessons: {str(e)}'}), 500

@bp.route('/browse_lessons', methods=['GET'])
@student_required
def browse_lessons():
    """Browse available lessons for students"""
    try:
        grade_level = request.args.get('grade_level')
        focus_area = request.args.get('focus_area')
        
        lessons = LessonModel.get_public_lessons(grade_level=grade_level, focus_area=focus_area)
        return jsonify({
            'success': True,
            'lessons': lessons
        })
    except Exception as e:
        logger.error(f"Error browsing lessons: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to browse lessons: {str(e)}'}), 500

@bp.route('/search_lessons', methods=['GET'])
@student_required
def search_lessons():
    """Search lessons for students"""
    try:
        search_term = request.args.get('q', '')
        grade_level = request.args.get('grade_level')
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        lessons = LessonModel.search_lessons(search_term, grade_level=grade_level)
        return jsonify({
            'success': True,
            'lessons': lessons
        })
    except Exception as e:
        logger.error(f"Error searching lessons: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to search lessons: {str(e)}'}), 500

@bp.route('/lesson/<int:lesson_id>', methods=['GET'])
@login_required
def get_lesson(lesson_id):
    """Get a specific lesson by ID"""
    try:
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Check if user can access this lesson
        user_model = UserModel(session['user_id'])
        if lesson['teacher_id'] != session['user_id'] and not lesson['is_public']:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'lesson': lesson
        })
    except Exception as e:
        logger.error(f"Error getting lesson: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get lesson: {str(e)}'}), 500

@bp.route('/lesson/<int:lesson_id>', methods=['PUT'])
@teacher_required
def update_lesson(lesson_id):
    """Update a lesson (teacher only, and only their own lessons)"""
    try:
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Check if the lesson belongs to the current teacher
        if lesson['teacher_id'] != session['user_id']:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        lesson_model = LessonModel(lesson_id)
        
        success = lesson_model.update_lesson(
            title=data.get('title'),
            summary=data.get('summary'),
            learning_objectives=data.get('learning_objectives'),
            focus_area=data.get('focus_area'),
            grade_level=data.get('grade_level'),
            content=data.get('content'),
            is_public=data.get('is_public')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Lesson updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update lesson'}), 500
            
    except Exception as e:
        logger.error(f"Error updating lesson: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to update lesson: {str(e)}'}), 500

@bp.route('/lesson/<int:lesson_id>', methods=['DELETE'])
@teacher_required
def delete_lesson(lesson_id):
    """Delete a lesson (teacher only, and only their own lessons)"""
    try:
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Check if the lesson belongs to the current teacher
        if lesson['teacher_id'] != session['user_id']:
            return jsonify({'error': 'Access denied'}), 403
        
        lesson_model = LessonModel(lesson_id)
        success = lesson_model.delete_lesson()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Lesson deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete lesson'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting lesson: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to delete lesson: {str(e)}'}), 500

@bp.route('/download_lesson/<int:lesson_id>', methods=['GET'])
@login_required
def download_lesson(lesson_id):
    """Download a lesson as DOCX file"""
    try:
        lesson = LessonModel.get_lesson_by_id(lesson_id)
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Check if user can access this lesson
        user_model = UserModel(session['user_id'])
        if lesson['teacher_id'] != session['user_id'] and not lesson['is_public']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Create lesson structure for DOCX generation
        lesson_data = {
            'title': lesson['title'],
            'summary': lesson['summary'] or '',
            'learning_objectives': [lesson['learning_objectives']] if lesson['learning_objectives'] else [],
            'sections': [{'heading': 'Lesson Content', 'content': lesson['content']}],
            'key_concepts': [],
            'activities': [],
            'quiz': []
        }
        
        # Generate DOCX
        lesson_service = LessonService()
        docx_bytes = lesson_service._create_docx(lesson_data)
        
        # Create filename
        filename = lesson['title'].replace(' ', '_') + '.docx'
        
        # Create BytesIO object
        docx_buffer = BytesIO(docx_bytes)
        docx_buffer.seek(0)
        
        return send_file(
            docx_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to download lesson: {str(e)}'}), 500 

@bp.route('/ask_question', methods=['POST'])
@student_required
def ask_lesson_question():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    question = data.get('question')
    if not lesson_id or not question:
        return jsonify({'error': 'lesson_id and question are required'}), 400
    api_key = session.get('groq_api_key')
    service = LessonService(api_key=api_key)
    result = service.answer_lesson_question(lesson_id, question, api_key)
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    return jsonify({'answer': result['answer']})

@bp.route('/faqs/<int:lesson_id>', methods=['GET'])
@teacher_required
def get_lesson_faqs(lesson_id):
    service = LessonService()
    faqs = service.get_lesson_faqs(lesson_id)
    return jsonify({'faqs': faqs}) 