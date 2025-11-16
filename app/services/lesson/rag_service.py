"""
RAG (Retrieval-Augmented Generation) service for lesson content
"""
import logging
import tempfile
import os
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Disable tqdm threading to prevent "cannot start new thread" errors
os.environ['TQDM_DISABLE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for semantic content retrieval and generation
    """
    
    def __init__(self):
        """Initialize RAG service with embeddings and text splitter"""
        # Configure embeddings to disable threading and progress bars
        # Environment variables TQDM_DISABLE and TOKENIZERS_PARALLELISM are set at app startup
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={
                'device': 'cpu',
                'trust_remote_code': False
            },
            encode_kwargs={
                'normalize_embeddings': False
            }
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.documents = []
        self.vector_store = None
        self.use_rag = False
        logger.info("RAG service initialized")

    def process_document(self, documents: List[Document], filename: str) -> Dict[str, Any]:
        """
        Process documents and create vector store
        
        Args:
            documents: List of documents to process
            filename: Name of the file being processed
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing {len(documents)} documents for RAG")
            
            # Check if document is large enough for RAG
            total_text = "\n".join([doc.page_content for doc in documents])
            if len(total_text) < 400:  # Small documents don't need RAG
                logger.info("Document is small, RAG not needed")
                return {
                    'use_rag': False,
                    'message': 'Document is small, using direct processing'
                }
            
            # Split documents into chunks
            # all_chunks = []
            # for doc in documents:
            #     chunks = self.text_splitter.split_documents([doc])
            #     all_chunks.extend(chunks)
            # 


            
            from langchain_core.documents import Document

            all_chunks = []
            for doc_text in documents:
                if isinstance(doc_text, str):
                    doc = Document(page_content=doc_text)
                else:
                    doc = doc_text
                chunks = self.text_splitter.split_documents([doc])
                all_chunks.extend(chunks)
            
            logger.info(f"Created {len(all_chunks)} chunks from documents")
            
            # Create embeddings and vector store
            self.documents = all_chunks
            self.vector_store = FAISS.from_documents(all_chunks, self.embeddings)
            #saved the vector

            self.vector_store.save_local("vector_store.faiss")

            
           
            logger.info("Vector store saved successfully")
            self.use_rag = True
            
            logger.info("Vector store created successfully")
            return {
                'use_rag': True,
                'chunks_count': len(all_chunks),
                'message': 'Vector store created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error processing documents for RAG: {str(e)}")
            return {
                'use_rag': False,
                'error': f'Failed to process documents: {str(e)}'
            }

    def retrieve_relevant_chunks(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve relevant chunks based on query
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            if not self.vector_store:
                logger.warning("No vector store available")
                return []
            
            # Perform similarity search
            relevant_docs = self.vector_store.similarity_search(query, k=k)
            logger.info(f"Retrieved {len(relevant_docs)} relevant chunks for query")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {str(e)}")
            return []
    


    def create_rag_prompt(self, user_prompt: str, relevant_chunks: List[Document], 
                     lesson_details: Optional[Dict[str, str]] = None,
                     tables_data: List[Dict] = None,
                     images_data: List[Dict] = None) -> str:
        """
        Create RAG prompt with retrieved context, enhanced with tables and images data
    
        Args:
            user_prompt: User's prompt
            relevant_chunks: Retrieved relevant chunks
            lesson_details: Additional lesson details
            tables_data: Extracted tables data
            images_data: Extracted images data with summaries
        
        Returns:
            Formatted RAG prompt with enhanced context
        """
        try:
         # Combine relevant chunks
            context = "\n\n".join([chunk.page_content for chunk in relevant_chunks])
        
            # Build tables context section
            tables_context = ""
            if tables_data and isinstance(tables_data, list) and len(tables_data) > 0:
                tables_context = "\n\n=== DOCUMENT TABLES DATA ===\n"
                tables_context += f"Total tables extracted: {len(tables_data)}\n"
            
                for i, table in enumerate(tables_data[:5]):  # Limit to first 5 tables
                    if isinstance(table, dict):
                        tables_context += f"\n--- Table {i+1} (Page {table.get('page', 'N/A')}) ---\n"
                        tables_context += f"Structure: {table.get('shape', 'N/A')} rows x columns\n"
                    
                        # Add column headers
                        if table.get('columns'):
                            tables_context += f"Columns: {', '.join(str(col) for col in table['columns'])}\n"
                    
                        # Add sample data (first 3 rows)
                        if table.get('data') and len(table['data']) > 0:
                            tables_context += "Sample Data:\n"
                            for row_idx, row in enumerate(table['data'][:3]):
                                row_str = " | ".join(str(cell)[:50] for cell in row)  # Limit cell length
                                tables_context += f"Row {row_idx+1}: {row_str}\n"
                        
                            if len(table['data']) > 3:
                                tables_context += f"... and {len(table['data']) - 3} more rows\n"
        
            # Build images context section
            images_context = ""
            if images_data and isinstance(images_data, list) and len(images_data) > 0:
                images_context = "\n\n=== DOCUMENT IMAGES WITH AI SUMMARIES ===\n"
                images_context += f"Total images extracted: {len(images_data)}\n"
            
                for i, image in enumerate(images_data[:5]):  # Limit to first 5 images
                    if isinstance(image, dict):
                        images_context += f"\n--- Image {i+1} (Page {image.get('page_number', 'N/A')}) ---\n"
                        if image.get('width') and image.get('height'):
                            images_context += f"Dimensions: {image['width']}x{image['height']} pixels\n"
                    
                        # Add AI-generated summary
                        summary = image.get('summary', 'No summary available')
                        if summary and not summary.startswith("Error generating summary"):
                            images_context += f"AI Description: {summary}\n"
                        else:
                            images_context += "AI Description: Visual content from document\n"
        
            # Build enhanced instructions for using tables and images
            enhanced_instructions = ""
            if tables_data or images_data:
                enhanced_instructions = """
            
                CRITICAL INSTRUCTION - INCORPORATE DOCUMENT ELEMENTS:
                You MUST use the available tables and images data to create a comprehensive lesson:
            
                FOR TABLES:
                - Create data analysis exercises using the table structures and sample data
                - Reference specific tables when teaching quantitative concepts
                - Generate practice questions based on the table column structures
                - Explain how to interpret the tabular data
            
                FOR IMAGES:
                - Reference the AI-generated image descriptions in your explanations
                - Create visual learning activities based on the image content
                - Suggest how to use these images for student engagement
                - Connect visual elements with conceptual understanding
            
                INTEGRATION REQUIREMENT:
                Your lesson MUST actively incorporate at least 2-3 references to specific tables or images.
                Create activities that directly use the extracted data and visual content.
                """
        
            # Build the complete enhanced prompt
            prompt = f"""
            Prof Potter's Role: Prof. Potter assists the Faculty in generating structured, logical, and engaging class-lessons for students.

            Identify the Subject and Topic.

            Determine Prerequisites:

            Identify background material or prior lessons students must understand.

            Offer to review and revise prerequisite lessons.

            Develop the Class Lesson:

            Build lessons as a series of short, simple lectures.

            Ensure each lecture is self-explanatory.

            Combine all lectures (plus prerequisites) into the full class-lesson.

            Logical Flow:

            Begin from the simplest concepts and build complexity step by step.

            Maintain logical continuity—no disjointed statements.

            Faculty Interaction:

            Ask questions for clarity.

            Occasionally explain what part of the lesson is being developed next.

            Incorporate Faculty suggestions when valid.

            Creativity & Feedback:

            Praise Faculty for creative teaching methods or unique perspectives.

            ========== DOCUMENT CONTEXT ==========
            Document Text Content:
            {context}
            {tables_context}
            {images_context}
            ======================================

            User Request:
            {user_prompt}
            {enhanced_instructions}

            REMEMBER: You have access to structured tables data and AI-analyzed images. 
            Use this rich multimodal content to create exceptionally comprehensive and engaging lessons!
            """

            logger.info(f"Created enhanced RAG prompt with:")
            logger.info(f"- Text context: {len(context)} characters")
            logger.info(f"- Tables: {len(tables_data) if tables_data else 0} tables")
            logger.info(f"- Images: {len(images_data) if images_data else 0} images")
        
            return prompt
        
        except Exception as e:
            logger.error(f"Error creating enhanced RAG prompt: {str(e)}")
            # Fallback to basic prompt
            return f"""Please create a comprehensive lesson plan based on the user's request.

    User Request: {user_prompt}

    Available additional context: Tables and images data from the document (processing error occurred).
    Please incorporate any available visual and tabular data into your lesson."""