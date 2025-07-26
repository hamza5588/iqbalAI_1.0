from flask import Blueprint, request, jsonify, session, send_file, after_this_request
from app.models.models import UserModel, LessonModel
from app.services.lesson_service import LessonService
from app.utils.decorators import login_required, teacher_required, student_required
from werkzeug.datastructures import FileStorage
import logging
import os
from io import BytesIO
import tempfile

logger = logging.getLogger(__name__)
bp = Blueprint('lesson_routes', __name__)

@bp.route('/create_lesson', methods=['POST'])
# @teacher_required
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
        
        # Aggregate all section contents into a single string for the content field
        sections = result['lesson'].get('sections', [])
        full_content = "\n\n".join([section.get('content', '') for section in sections if section.get('content')])
        
        # Store lesson in database
        lesson_id = LessonModel.create_lesson(
            teacher_id=session['user_id'],
            title=lesson_title,
            summary=result['lesson'].get('summary', ''),
            learning_objectives=learning_objective,
            focus_area=focus_area,
            grade_level=grade_level,
            content=full_content,
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
        
        # Get API key from session
        api_key = session.get('groq_api_key')
        if not api_key:
            return jsonify({'error': 'API key not configured. Please set your API key first.'}), 400
        
        # Generate DOCX
        lesson_service = LessonService(api_key=api_key)
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

@bp.route('/download_lesson_pdf/<int:lesson_id>', methods=['GET'])
@login_required
def download_lesson_pdf(lesson_id):
    lesson = LessonModel.get_lesson_by_id(lesson_id)
    if not lesson:
        return jsonify({'error': 'Lesson not found'}), 404

    # Generate DOCX first (reuse your existing logic)
    lesson_data = {
        'title': lesson['title'],
        'summary': lesson['summary'] or '',
        'learning_objectives': [lesson['learning_objectives']] if lesson['learning_objectives'] else [],
        'sections': [{'heading': 'Lesson Content', 'content': lesson['content']}],
        'key_concepts': [],
        'activities': [],
        'quiz': []
    }
    # Get API key from session
    api_key = session.get('groq_api_key')
    if not api_key:
        return jsonify({'error': 'API key not configured. Please set your API key first.'}), 400
    
    lesson_service = LessonService(api_key=api_key)
    docx_bytes = lesson_service._create_docx(lesson_data)

    # Save DOCX to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as docx_file:
        docx_file.write(docx_bytes)
        docx_path = docx_file.name

    pdf_path = docx_path.replace('.docx', '.pdf')
    try:
        import subprocess
        # Use LibreOffice to convert DOCX to PDF
        result = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', os.path.dirname(pdf_path), docx_path
        ], capture_output=True)
        if result.returncode != 0:
            raise Exception(f'LibreOffice conversion failed: {result.stderr.decode()}')
        # LibreOffice names the output file as <docx_basename>.pdf
        pdf_path = os.path.splitext(docx_path)[0] + '.pdf'

        @after_this_request
        def cleanup(response):
            try:
                os.remove(docx_path)
            except Exception:
                pass
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            return response

        return send_file(pdf_path, as_attachment=True, download_name=lesson['title'] + '.pdf', mimetype='application/pdf')
    except Exception as e:
        if os.path.exists(docx_path):
            os.remove(docx_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        logger.error(f"PDF generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF'}), 500

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
    result = service.answer_lesson_question(lesson_id, question)
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    return jsonify({'answer': result['answer']})

@bp.route('/faqs/<int:lesson_id>', methods=['GET'])
@teacher_required
def get_lesson_faqs(lesson_id):
    # Get API key from session
    api_key = session.get('groq_api_key')
    if not api_key:
        return jsonify({'error': 'API key not configured. Please set your API key first.'}), 400
    
    service = LessonService(api_key=api_key)
    faqs = service.get_lesson_faqs(lesson_id)
    return jsonify({'faqs': faqs}) 

@bp.route('/faq_dashboard', methods=['GET'])
@teacher_required
def faq_dashboard():
    try:
        user_id = session['user_id']
        # Get all lessons for this teacher
        lessons = LessonModel.get_lessons_by_teacher(user_id)
        lesson_ids = [lesson['id'] for lesson in lessons]
        top_questions = []
        total_questions = 0
        recent_questions = []
        import sqlite3
        from datetime import datetime, timedelta

        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        # For each lesson, get top questions
        for lesson in lessons:
            c.execute('SELECT question, count FROM lesson_faq WHERE lesson_id=? ORDER BY count DESC LIMIT 3', (lesson['id'],))
            faqs = [{'question': row[0], 'count': row[1]} for row in c.fetchall()]
            total_questions += sum(row['count'] for row in faqs)
            if faqs:
                top_questions.append({
                    'title': lesson['title'],
                    'subject': lesson.get('focus_area', ''),
                    'questions': faqs
                })
        # Get recent questions (last 24h) -- placeholder, as timestamps are not tracked
        # If you want real recent questions, you need to log timestamps in lesson_faq
        # For now, just return the most asked question per lesson
        for lesson in lessons:
            c.execute('SELECT question, count FROM lesson_faq WHERE lesson_id=? ORDER BY count DESC LIMIT 1', (lesson['id'],))
            row = c.fetchone()
            if row:
                recent_questions.append({
                    'question': row[0],
                    'student_name': '',  # Not tracked
                    'lesson_title': lesson['title'],
                    'time_ago': 'Recently'
                })
        conn.close()
        return jsonify({
            'total_questions': total_questions,
            'weekly_questions': total_questions,  # Placeholder
            'active_students': 0,  # Placeholder
            'top_questions': top_questions,
            'recent_questions': recent_questions
        })
    except Exception as e:
        logger.error(f"Error loading FAQ dashboard: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load FAQ dashboard'}), 500 

@bp.route('/export_faq_dashboard', methods=['GET'])
@teacher_required
def export_faq_dashboard():
    try:
        user_id = session['user_id']
        lessons = LessonModel.get_lessons_by_teacher(user_id)
        import sqlite3
        from io import BytesIO
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        conn = sqlite3.connect('instance/chatbot.db')
        c = conn.cursor()
        # Prepare data for export
        rows = []
        for lesson in lessons:
            c.execute('SELECT question, count FROM lesson_faq WHERE lesson_id=? ORDER BY count DESC', (lesson['id'],))
            faqs = c.fetchall()
            for faq in faqs:
                rows.append({
                    'lesson_title': lesson['title'],
                    'subject': lesson.get('focus_area', ''),
                    'question': faq[0],
                    'count': faq[1]
                })
        conn.close()

        # Create Word document
        doc = Document()
        doc.add_heading('FAQ Dashboard Export', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Lesson Title'
        hdr_cells[1].text = 'Subject'
        hdr_cells[2].text = 'Question'
        hdr_cells[3].text = 'Count'
        for cell in hdr_cells:
            for paragraph in cell.paragraphs:
                paragraph.runs[0].font.bold = True
                paragraph.runs[0].font.size = Pt(11)
        for row in rows:
            cells = table.add_row().cells
            cells[0].text = str(row['lesson_title'])
            cells[1].text = str(row['subject'])
            cells[2].text = str(row['question'])
            cells[3].text = str(row['count'])
        # Save to BytesIO
        doc_io = BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)
        from flask import make_response
        response = make_response(doc_io.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=faq_dashboard_export.docx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return response
    except Exception as e:
        logger.error(f"Error exporting FAQ dashboard: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to export FAQ dashboard'}), 500 