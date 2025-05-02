

# app/services/file_service.py
from typing import List, BinaryIO, Union, ContextManager
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import tempfile
import logging
import time
from contextlib import contextmanager
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PDFPlumberLoader, Docx2txtLoader
)
from app.utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)

class FileService:
    """Service class for handling file processing"""
    
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # seconds
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def check_file_size(self, file: Union[BinaryIO, FileStorage]) -> bool:
        """
        Check if file size is within the allowed limit
        
        Args:
            file: The file object to check
            
        Returns:
            bool: True if file size is within limit, False otherwise
        """
        try:
            # For FileStorage objects
            if isinstance(file, FileStorage):
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                return size <= MAX_FILE_SIZE
            
            # For regular file objects
            elif hasattr(file, 'seek') and hasattr(file, 'tell'):
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                return size <= MAX_FILE_SIZE
            
            # For file paths
            elif isinstance(file, str) and os.path.exists(file):
                return os.path.getsize(file) <= MAX_FILE_SIZE
                
            return False
        except Exception as e:
            logger.error(f"Error checking file size: {str(e)}")
            return False

    def _safe_delete(self, filepath: str) -> None:
        """
        Safely delete a file with retries for Windows systems.
        
        Args:
            filepath: Path to the file to delete
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
                break
            except PermissionError:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    continue
                logger.warning(f"Could not delete temporary file {filepath} after {self.MAX_RETRIES} attempts")
            except Exception as e:
                logger.error(f"Error deleting file {filepath}: {str(e)}")
                break

    @contextmanager
    def _create_temp_file(self, file: Union[BinaryIO, FileStorage], extension: str) -> ContextManager[str]: # type: ignore
        """
        Create a temporary file from uploaded content with proper Windows handling.
        
        Args:
            file: The file object to process
            extension: The file extension including the dot (e.g., '.pdf')
            
        Yields:
            str: Path to the temporary file
        """
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
        temp_path = temp.name
        temp.close()  # Close immediately to avoid Windows file handle issues
        
        try:
            if isinstance(file, FileStorage):
                file.save(temp_path)
            else:
                file.seek(0)
                with open(temp_path, 'wb') as f:
                    f.write(file.read())
            yield temp_path
        finally:
            self._safe_delete(temp_path)

    def _load_documents(self, file_path: str, extension: str) -> List[Document]:
        """
        Load documents based on file extension with proper resource management.
        
        Args:
            file_path: Path to the file
            extension: The file extension (e.g., '.pdf')
            
        Returns:
            List[Document]: List of loaded documents
        """
        try:
            if extension == '.pdf':
                loader = PDFPlumberLoader(file_path)
                documents = loader.load()
                # Add page numbers starting from 1
                for i, doc in enumerate(documents):
                    doc.metadata = {'page': i + 1}
                    
            elif extension in ['.doc', '.docx']:
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
                # For Word docs, assign sequential page numbers
                for i, doc in enumerate(documents):
                    doc.metadata = {'page': i + 1}
                    
            else:  # .txt files
                loader = TextLoader(file_path)
                documents = loader.load()
                # For text files, assign sequential page numbers
                for i, doc in enumerate(documents):
                    doc.metadata = {'page': i + 1}
            
            # Ensure any file handles are closed
            if hasattr(loader, 'close'):
                loader.close()
                
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise

    def process_file(self, file: Union[BinaryIO, FileStorage, str]) -> List[Document]:
        """
        Process a file and return chunks.
        
        Args:
            file: Can be a FileStorage object (from Flask uploads),
                 a BinaryIO object, or a string path
        
        Returns:
            List[Document]: List of processed document chunks with page information
        """
        try:
            # Handle different file input types
            if isinstance(file, str):
                filename = os.path.basename(file)
                file_path = file
            elif isinstance(file, FileStorage):
                filename = secure_filename(file.filename)
                file_path = None
            elif hasattr(file, 'name'):
                filename = secure_filename(os.path.basename(file.name))
                file_path = None
            else:
                raise ValueError("Unsupported file type. Expected FileStorage, file object, or string path.")

            # Validate filename
            if not filename:
                raise ValueError("No filename available")

            # Check file size
            if not self.check_file_size(file):
                raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE/(1024*1024)}MB")

            file_extension = os.path.splitext(filename)[1].lower()
            
            # Validate file extension
            if not self.allowed_file(filename):
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Process the file
            if file_path:
                documents = self._load_documents(file_path, file_extension)
            else:
                with self._create_temp_file(file, file_extension) as temp_path:
                    documents = self._load_documents(temp_path, file_extension)

            # Split into chunks while preserving page information
            chunks = []
            for doc in documents:
                doc_chunks = self.text_splitter.split_documents([doc])
                # Ensure each chunk retains the page number and other metadata
                for chunk in doc_chunks:
                    chunk.metadata.update(doc.metadata)
                chunks.extend(doc_chunks)

            logger.info(f"Successfully processed {filename} into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error processing file {filename if 'filename' in locals() else 'unknown'}: {str(e)}")
            raise