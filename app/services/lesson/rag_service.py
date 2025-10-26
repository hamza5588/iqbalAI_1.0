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

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for semantic content retrieval and generation
    """
    
    def __init__(self):
        """Initialize RAG service with embeddings and text splitter"""
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
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
            if len(total_text) < 5000:  # Small documents don't need RAG
                logger.info("Document is small, RAG not needed")
                return {
                    'use_rag': False,
                    'message': 'Document is small, using direct processing'
                }
            
            # Split documents into chunks
            all_chunks = []
            for doc in documents:
                chunks = self.text_splitter.split_documents([doc])
                all_chunks.extend(chunks)
            
            logger.info(f"Created {len(all_chunks)} chunks from documents")
            
            # Create embeddings and vector store
            self.documents = all_chunks
            self.vector_store = FAISS.from_documents(all_chunks, self.embeddings)
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

    def create_rag_prompt(self, user_prompt: str, relevant_chunks: List[Document], lesson_details: Optional[Dict[str, str]] = None) -> str:
        """
        Create RAG prompt with retrieved context
        
        Args:
            user_prompt: User's prompt
            relevant_chunks: Retrieved relevant chunks
            lesson_details: Additional lesson details
            
        Returns:
            Formatted RAG prompt
        """
        try:
            # Combine relevant chunks
            context = "\n\n".join([chunk.page_content for chunk in relevant_chunks])
            
            # Create base prompt
            prompt = f"""You are an expert teacher. Based on the following context from the document, please address the user's request.

Document Context:
{context}

User Request:
{user_prompt}"""

            # Add lesson details if provided
            if lesson_details:
                if lesson_details.get('grade_level'):
                    prompt += f"\n\nGrade Level: {lesson_details['grade_level']}"
                if lesson_details.get('focus_area'):
                    prompt += f"\nFocus Area: {lesson_details['focus_area']}"
                if lesson_details.get('lesson_title'):
                    prompt += f"\nLesson Title: {lesson_details['lesson_title']}"

            # Add instruction based on user intent
            if any(keyword in user_prompt.lower() for keyword in ['lesson', 'plan', 'generate', 'create', 'make']):
                prompt += """

Please create a comprehensive lesson plan that includes:
- Clear title and summary
- Learning objectives
- Background prerequisites
- Structured sections with detailed content
- Creative activities for students
- Assessment questions
- Teacher notes

Use the document context to inform your lesson plan and ensure it's appropriate for the specified grade level and focus area."""
            else:
                prompt += """

Please provide a detailed, comprehensive answer that directly addresses the user's question. Use information from the document context to support your answer. Be thorough and educational."""

            logger.info(f"Created RAG prompt with {len(context)} characters of context")
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating RAG prompt: {str(e)}")
            return f"Please answer the following question: {user_prompt}"
