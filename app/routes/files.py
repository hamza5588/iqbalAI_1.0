from flask import Blueprint, request, jsonify, current_app, session
from app.models import VectorStoreModel
from app.services.file_service import FileService
from werkzeug.utils import secure_filename
import os
import logging

from app.models import UserModel

logger = logging.getLogger(__name__)
bp = Blueprint('files', __name__)

def process_single_file(file, file_service, upload_folder):
    """Helper function to process a single file"""
    if not file or not file.filename:
        return None
    
    if not file_service.allowed_file(file.filename):
        return None

    # Secure the filename and create full path
    filename = secure_filename(file.filename)
    temp_path = os.path.join(upload_folder, filename)
    
    try:
        # Save the file
        file.save(temp_path)
        
        # Process file and get chunks
        chunks = file_service.process_file(temp_path)
        return chunks
    
    except Exception as e:
        logger.error(f"Error processing file {filename}: {str(e)}")
        return None
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_path}: {str(e)}")

from app.services.file_service import FileService
from app.utils.constants import MAX_FILE_SIZE
@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No selected files'}), 400

        file_service = FileService()
        vector_store = VectorStoreModel(session['user_id'])
        all_chunks = []

        for file in files:
            if file and file.filename:
                try:
                    # Process file and get chunks
                    chunks = file_service.process_file(file)
                    all_chunks.extend(chunks)
                except ValueError as ve:
                    logger.warning(f"Validation error for file {file.filename}: {str(ve)}")
                    return jsonify({
                        'error': f"Error with file {file.filename}: {str(ve)}. Maximum file size is {MAX_FILE_SIZE/(1024*1024)}MB"
                    }), 400
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {str(e)}")
                    return jsonify({'error': f'Error processing {file.filename}'}), 500

        if not all_chunks:
            return jsonify({'error': 'No valid content found in files'}), 400

        # Update vector store
        try:
            vector_store.create_vectorstore(all_chunks)
            return jsonify({'message': 'Files processed successfully'})
        except Exception as e:
            logger.error(f"Error updating vector store: {str(e)}")
            return jsonify({'error': 'Error processing documents'}), 500

    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({'error': 'File upload failed'}), 500
# @bp.route('/upload', methods=['POST'])
# def upload_file():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Not authenticated'}), 401

#     try:
#         if 'files' not in request.files:
#             return jsonify({'error': 'No files provided'}), 400

#         files = request.files.getlist('files')
#         if not files or all(not file.filename for file in files):
#             return jsonify({'error': 'No selected files'}), 400

#         file_service = FileService()
#         vector_store = VectorStoreModel()
#         all_chunks = []

#         for file in files:
#             if file and file.filename:  # Extra check for valid file
#                 try:
#                     # Process file and get chunks
#                     chunks = file_service.process_file(file)
#                     all_chunks.extend(chunks)
#                 except ValueError as ve:
#                     # Handle validation errors separately
#                     logger.warning(f"Validation error for file {file.filename}: {str(ve)}")
#                     return jsonify({'error': str(ve)}), 400
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
#         return jsonify({'error': 'File upload failed'}), 500

@bp.route('/update_api_key', methods=['POST'])
def update_api_key():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        data = request.json
        new_api_key = data.get('api_key')
        
        if not new_api_key:
            return jsonify({'error': 'API key is required'}), 400

        user_model = UserModel(session['user_id'])
        user_model.update_api_key(new_api_key)
        session['groq_api_key'] = new_api_key

        return jsonify({
            'success': True,
            'message': 'API key updated successfully'
        })

    except Exception as e:
        logger.error(f"API key update error: {str(e)}")
        return jsonify({'error': 'Failed to update API key'}), 500