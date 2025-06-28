# from flask import Blueprint, request, jsonify, current_app, session
# from werkzeug.utils import secure_filename
# import os
# import logging
# from app.services import LessonService
# from app.models import UserModel, VectorStoreModel
# from app.services import ChatService
# from app.utils.db import get_db

# logger = logging.getLogger(__name__)
# bp = Blueprint('files', __name__)

# def allowed_file(filename):
#     """Check if the file has an allowed extension"""
#     ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @bp.route('/upload', methods=['POST'])
# def upload_lesson():
#     logger.info("Upload endpoint hit")
#     if 'user_id' not in session:
#         logger.warning("User not authenticated")
#         return jsonify({'error': 'Not authenticated'}), 401

#     if 'file' not in request.files:
#         logger.warning("No file part in request")
#         logger.debug(f"Request files: {request.files}")
#         return jsonify({'error': 'No file provided'}), 400

#     file = request.files['file']
#     logger.info(f"File received: {file.filename}")
#     if not file or file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400

#     if not allowed_file(file.filename):
#         return jsonify({'error': 'File type not allowed. Please upload PDF, DOC, DOCX, or TXT.'}), 400

#     try:
#         # Use the API key from session if available
#         api_key = session.get('groq_api_key')
#         file_service = LessonService(api_key=api_key)

#         # Process the file and generate lesson plan
#         lesson = file_service.process_file(file)

#         if 'error' in lesson:
#             return jsonify({'error': lesson['error'], 'details': lesson.get('details')}), 400

#         return jsonify({
#             'message': 'Lesson generated successfully',
#             'lesson': lesson
#         })

#     except Exception as e:
#         logger.error(f"Lesson generation error: {str(e)}")
#         return jsonify({'error': 'Failed to generate lesson plan'}), 500


# @bp.route('/update_api_key', methods=['POST'])
# def update_api_key():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401

#     try:
#         data = request.get_json(silent=True) or {}
#         new_api_key = data.get('api_key', '').strip()

#         if not new_api_key:
#             return jsonify({'error': 'API key is required'}), 400

#         # Test the API key by making a simple request first
#         try:
#             chat_service = ChatService(session['user_id'], new_api_key)
#             chat_service.chat_model.generate_response("test")
#         except Exception as e:
#             logger.error(f"Invalid API key: {str(e)}")
#             return jsonify({'error': 'Invalid API key'}), 400

#         # If API key is valid, update in database
#         user_model = UserModel(session['user_id'])
#         user_model.update_api_key(new_api_key)

#         # Update session with new API key
#         session.pop('groq_api_key', None)  # Remove old key
#         session['groq_api_key'] = new_api_key  # Set new key
#         session.modified = True  # Mark session as modified

#         # Verify the update by checking the database directly
#         db = get_db()
#         updated_user = db.execute(
#             'SELECT groq_api_key FROM users WHERE id = ?',
#             (session['user_id'],)
#         ).fetchone()

#         if not updated_user or updated_user['groq_api_key'] != new_api_key:
#             logger.error("Failed to verify API key update in database")
#             return jsonify({'error': 'Failed to verify API key update'}), 500

#         return jsonify({
#             'success': True,
#             'message': 'API key updated successfully'
#         })

#     except Exception as e:
#         logger.error(f"API key update error: {str(e)}")
#         return jsonify({'error': 'Failed to update API key'}), 500









# # from flask import Blueprint, request, jsonify, current_app, session
# # from werkzeug.utils import secure_filename
# # from flask import send_file
# # from io import BytesIO
# # import os
# # import logging

# # from app.models import VectorStoreModel, UserModel
# # from app.services.lesson_service import LessonService
# # from app.utils.constants import MAX_FILE_SIZE
# # from langchain_core.documents import Document

# # logger = logging.getLogger(__name__)
# # bp = Blueprint('files', __name__)













# @bp.route('/api/upload', methods=['POST'])
# def upload_file():
#     try:
#         # Check authentication
#         if 'user_id' not in session:
#             logger.warning("Unauthorized upload attempt")
#             return jsonify({'error': 'Not authenticated'}), 401

#         # Check files
#         if 'files' not in request.files:
#             logger.warning("No files in request")
#             return jsonify({'error': 'No files provided'}), 400

#         files = request.files.getlist('files')
#         if not files or all(file.filename == '' for file in files):
#             logger.warning("Empty file list")
#             return jsonify({'error': 'No selected files'}), 400

#         # Validate files
#         for file in files:
#             if not file.filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
#                 logger.warning(f"Unsupported file type: {file.filename}")
#                 return jsonify({'error': 'Only PDF, Word, and text files are supported'}), 400

#         # Process first file (you could extend this to handle multiple files)
#         first_file = files[0]
        
#         # Initialize LessonService with API key from session if available
#         api_key = session.get('groq_api_key')
#         lesson_service = LessonService(api_key=api_key)
        
#         # Process the file
#         result = lesson_service.process_file(first_file)
        
#         if 'error' in result:
#             logger.error(f"Lesson generation failed: {result['error']}")
#             return jsonify({'error': result['error'], 'details': result.get('details')}), 500
        
#         # Return the lesson data
#         return jsonify({
#             'success': True,
#             'lesson': result['lesson'],
#             'filename': result['filename']
#         })

#     except Exception as e:
#         logger.error(f"Upload failed: {str(e)}", exc_info=True)
#         return jsonify({'error': f'Server error: {str(e)}'}), 500
    

# @bp.route('/api/download_lesson', methods=['GET'])
# def download_lesson():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401
        
#     # You would need to store the docx_bytes temporarily or in a database
#     # This is just a basic example
#     docx_bytes = session.get('last_generated_docx')
#     if not docx_bytes:
#         return jsonify({'error': 'No lesson available to download'}), 404
        
#     return send_file(
#         BytesIO(docx_bytes),
#         as_attachment=True,
#         download_name='generated_lesson.docx',
#         mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
#     )



# @bp.route('/update_api_key', methods=['POST'])
# def update_api_key():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401

#     try:
#         data = request.json
#         new_api_key = data.get('api_key')
        
#         if not new_api_key:
#             return jsonify({'error': 'API key is required'}), 400

#         user_model = UserModel(session['user_id'])
#         user_model.update_api_key(new_api_key)
#         session['groq_api_key'] = new_api_key

#         return jsonify({
#             'success': True,
#             'message': 'API key updated successfully'
#         })

#     except Exception as e:
#         logger.error(f"API key update error: {str(e)}")
#         return jsonify({'error': 'Failed to update API key'}), 500
























# from flask import Blueprint, request, jsonify, current_app, session
# from app.models import VectorStoreModel
# # from app.services.file_service import FileService
# from app.services.lesson_service import LessonService
# from werkzeug.utils import secure_filename
# import os
# import logging

# from app.models import UserModel

# logger = logging.getLogger(__name__)
# bp = Blueprint('files', __name__)

# def process_single_file(file, file_service, upload_folder):
#     """Helper function to process a single file"""
#     if not file or not file.filename:
#         return None
    
#     if not file_service.allowed_file(file.filename):
#         return None

#     # Secure the filename and create full path
#     filename = secure_filename(file.filename)
#     temp_path = os.path.join(upload_folder, filename)
    
#     try:
#         # Save the file
#         file.save(temp_path)
        
#         # Process file and get chunks
#         chunks = file_service.process_file(temp_path)
#         return chunks
    
#     except Exception as e:
#         logger.error(f"Error processing file {filename}: {str(e)}")
#         return None
    
#     finally:
#         # Clean up temporary file
#         if os.path.exists(temp_path):
#             try:
#                 os.remove(temp_path)
#             except Exception as e:
#                 logger.error(f"Error removing temporary file {temp_path}: {str(e)}")

# # from app.services.file_service import FileService
# from app.services.lesson_service import LessonService
# from app.utils.constants import MAX_FILE_SIZE
# @bp.route('/upload', methods=['POST'])
# def upload_file():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401

#     try:
#         if 'files' not in request.files:
#             return jsonify({'error': 'No files provided'}), 400

#         files = request.files.getlist('files')
#         if not files:
#             return jsonify({'error': 'No selected files'}), 400

#         file_service = LessonService()
#         vector_store = VectorStoreModel(session['user_id'])
#         all_chunks = []

#         for file in files:
#             if file and file.filename:
#                 try:
#                     # Process file and get chunks
#                     chunks = file_service.process_file(file)
#                     all_chunks.extend(chunks)
#                 except ValueError as ve:
#                     logger.warning(f"Validation error for file {file.filename}: {str(ve)}")
#                     return jsonify({
#                         'error': f"Error with file {file.filename}: {str(ve)}. Maximum file size is {MAX_FILE_SIZE/(1024*1024)}MB"
#                     }), 400
#                 except Exception as e:
#                     logger.error(f"Error processing file {file.filename}: {str(e)}")
#                     return jsonify({'error': f'Error processing {file.filename}'}), 500

#         if not all_chunks:
#             return jsonify({'error': 'No valid content found in files'}), 400

#         # Update vector store
#         try:
#             vector_store.create_vectorstore(all_chunks)
#             return jsonify({'message': 'Files processed successfully'})
#         except Exception as e:
#             logger.error(f"Error updating vector store: {str(e)}")
#             return jsonify({'error': 'Error processing documents'}), 500

#     except Exception as e:
#         logger.error(f"File upload error: {str(e)}")
    
    
# @bp.route('/update_api_key', methods=['POST'])
# def update_api_key():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401

#     try:
#         data = request.json
#         new_api_key = data.get('api_key')
        
#         if not new_api_key:
#             return jsonify({'error': 'API key is required'}), 400

#         user_model = UserModel(session['user_id'])
#         user_model.update_api_key(new_api_key)
#         session['groq_api_key'] = new_api_key

#         return jsonify({
#             'success': True,
#             'message': 'API key updated successfully'
#         })

#     except Exception as e:
#         logger.error(f"API key update error: {str(e)}")
#         return jsonify({'error': 'Failed to update API key'}), 500





from flask import Blueprint, request, jsonify, current_app, session, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
import os
import logging
import tempfile

from app.models import VectorStoreModel, UserModel
from app.services.lesson_service import LessonService
from app.utils.constants import MAX_FILE_SIZE

logger = logging.getLogger(__name__)
bp = Blueprint('files', __name__)

@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and lesson generation"""
    if 'user_id' not in session:
        logger.warning("Unauthorized upload attempt")
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Check if files are present
        if 'files' not in request.files:
            logger.warning("No files in request")
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            logger.warning("Empty file list")
            return jsonify({'error': 'No selected files'}), 400

        # For now, process only the first file (you can extend this later)
        file = files[0]
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
            logger.warning(f"Unsupported file type: {file.filename}")
            return jsonify({'error': 'Only PDF, Word, and text files are supported'}), 400

        # Initialize LessonService with API key from session
        api_key = session.get('groq_api_key')
        if not api_key:
            return jsonify({'error': 'API key not found. Please set your API key first.'}), 400
            
        lesson_service = LessonService(api_key=api_key)
        
        # Process the file and generate lesson
        result = lesson_service.process_file(file)
        
        if 'error' in result:
            logger.error(f"Lesson generation failed: {result['error']}")
            return jsonify({
                'error': result['error'], 
                'details': result.get('details', '')
            }), 500
        
        # Store the generated DOCX bytes in session for download
        session['last_generated_docx'] = result['docx_bytes']
        session['last_generated_filename'] = result['filename']
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': 'Lesson generated successfully',
            'lesson': result['lesson'],
            'filename': result['filename'],
            'download_ready': True
        })

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500
@bp.route('/generate_lesson', methods=['POST'])
def generate_lesson():
    """Endpoint for lesson generation that returns file directly"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the uploaded file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'File type not supported. Please upload PDF, DOC, DOCX, or TXT files.'}), 400
        
        # Get API key from session
        api_key = session.get('groq_api_key')
        if not api_key:
            return jsonify({'error': 'API key not configured. Please set your API key first.'}), 400
        
        # Initialize lesson service
        lesson_service = LessonService(api_key=api_key)
        
        # Process file and generate lesson
        result = lesson_service.process_file(file)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'details': result.get('details', '')
            }), 500
        
        # Create BytesIO object from the generated DOCX bytes
        docx_buffer = BytesIO(result['docx_bytes'])
        docx_buffer.seek(0)
        
        # Return both JSON metadata and file in the response
        response = send_file(
            docx_buffer,
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response.headers['X-Lesson-Title'] = result['lesson'].get('title', '')
        response.headers['X-Lesson-Summary'] = result['lesson'].get('summary', '')
        response.headers['X-Success'] = 'true'
        return response
        
    except Exception as e:
        logger.error(f"Lesson generation error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to generate lesson: {str(e)}'}), 500
    
@bp.route('/download_lesson', methods=['GET'])
def download_lesson():
    """Download the generated lesson as DOCX file"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the stored DOCX bytes from session
        docx_bytes = session.get('last_generated_docx')
        filename = session.get('last_generated_filename', 'generated_lesson.docx')
        
        if not docx_bytes:
            return jsonify({'error': 'No lesson available to download. Please generate a lesson first.'}), 404
        
        # Create BytesIO object from stored bytes
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

@bp.route('/update_api_key', methods=['POST'])
def update_api_key():
    """Update the user's API key"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.get_json(silent=True) or {}
        new_api_key = data.get('api_key', '').strip()
        
        if not new_api_key:
            return jsonify({'error': 'API key is required'}), 400

        # Test the API key first
        try:
            test_service = LessonService(api_key=new_api_key)
            # You might want to add a simple test here
        except Exception as e:
            logger.error(f"Invalid API key: {str(e)}")
            return jsonify({'error': 'Invalid API key provided'}), 400

        # Update in database
        user_model = UserModel(session['user_id'])
        user_model.update_api_key(new_api_key)
        
        # Update session
        session['groq_api_key'] = new_api_key
        session.modified = True

        return jsonify({
            'success': True,
            'message': 'API key updated successfully'
        })

    except Exception as e:
        logger.error(f"API key update error: {str(e)}")
        return jsonify({'error': 'Failed to update API key'}), 500