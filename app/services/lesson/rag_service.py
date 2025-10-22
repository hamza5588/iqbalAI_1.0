"""
RAG (Retrieval-Augmented Generation) service for handling large documents
"""
import os
import logging
import tempfile
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path

import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

# Set up RAG service logging
rag_logger = logging.getLogger('rag_service')
rag_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

rag_handler = logging.FileHandler('logs/lesson.log')
rag_handler.setLevel(logging.INFO)

# Create formatter for RAG logs
rag_formatter = logging.Formatter(
    '%(asctime)s - RAG_SERVICE - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
rag_handler.setFormatter(rag_formatter)
rag_logger.addHandler(rag_handler)


class RAGService:
    """
    RAG service for handling large documents by:
    1. Chunking text into smaller pieces
    2. Creating embeddings for each chunk
    3. Storing in FAISS vector database
    4. Retrieving relevant chunks for queries
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG service with embedding model
        
        Args:
            model_name: Sentence transformer model name
        """
        self.model_name = model_name
        self.embedding_model = None
        self.index = None
        self.documents = []
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_tokens = 8000  # Leave room for prompt and response
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        rag_logger.info(f"RAG Service initialized with model: {model_name}")
    
    def _get_embedding_model(self):
        """Lazy load embedding model"""
        if self.embedding_model is None:
            rag_logger.info(f"Loading embedding model: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)
            rag_logger.info("Embedding model loaded successfully")
        return self.embedding_model
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of token count (1 token ≈ 4 characters)
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def should_use_rag(self, text: str) -> bool:
        """
        Determine if RAG should be used based on text length
        
        Args:
            text: Input text
            
        Returns:
            True if RAG should be used
        """
        estimated_tokens = self._estimate_tokens(text)
        should_use = estimated_tokens > self.max_tokens
        
        rag_logger.info(f"Text length: {len(text)} characters, estimated tokens: {estimated_tokens}")
        rag_logger.info(f"Should use RAG: {should_use}")
        
        return should_use
    
    def process_document(self, documents: List[Document], filename: str) -> Dict[str, Any]:
        """
        Process documents and create vector database
        
        Args:
            documents: List of LangChain documents
            filename: Original filename
            
        Returns:
            Dictionary with processing results
        """
        rag_logger.info(f"=== RAG DOCUMENT PROCESSING STARTED ===")
        rag_logger.info(f"Filename: {filename}")
        rag_logger.info(f"Number of documents: {len(documents)}")
        
        try:
            # Combine all documents
            full_text = "\n".join([doc.page_content for doc in documents])
            rag_logger.info(f"Full text length: {len(full_text)} characters")
            
            # Check if RAG is needed
            if not self.should_use_rag(full_text):
                rag_logger.info("Document is small enough, RAG not needed")
                return {
                    "use_rag": False,
                    "full_text": full_text,
                    "chunks": [],
                    "index": None
                }
            
            # Split text into chunks
            rag_logger.info("Splitting text into chunks")
            chunks = self.text_splitter.split_text(full_text)
            rag_logger.info(f"Created {len(chunks)} chunks")
            
            # Create documents from chunks
            chunk_docs = [Document(page_content=chunk, metadata={"chunk_id": i, "filename": filename}) 
                         for i, chunk in enumerate(chunks)]
            
            # Generate embeddings
            rag_logger.info("Generating embeddings")
            embedding_model = self._get_embedding_model()
            embeddings = embedding_model.encode([doc.page_content for doc in chunk_docs])
            rag_logger.info(f"Generated embeddings shape: {embeddings.shape}")
            
            # Create FAISS index
            rag_logger.info("Creating FAISS index")
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings.astype('float32'))
            
            # Store documents
            self.documents = chunk_docs
            
            rag_logger.info("=== RAG DOCUMENT PROCESSING COMPLETED ===")
            
            return {
                "use_rag": True,
                "full_text": full_text,
                "chunks": chunks,
                "index": self.index,
                "documents": chunk_docs,
                "embeddings": embeddings
            }
            
        except Exception as e:
            rag_logger.error(f"Error processing document: {str(e)}")
            return {"error": f"Error processing document: {str(e)}"}
    
    def retrieve_relevant_chunks(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve most relevant chunks for a query
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of relevant documents
        """
        if self.index is None or not self.documents:
            rag_logger.warning("No index available for retrieval")
            return []
        
        try:
            rag_logger.info(f"Retrieving chunks for query: {query[:100]}...")
            
            # Generate query embedding
            embedding_model = self._get_embedding_model()
            query_embedding = embedding_model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search for similar chunks
            scores, indices = self.index.search(query_embedding.astype('float32'), k)
            
            # Get relevant documents
            relevant_docs = [self.documents[i] for i in indices[0] if i < len(self.documents)]
            
            rag_logger.info(f"Retrieved {len(relevant_docs)} relevant chunks")
            for i, doc in enumerate(relevant_docs):
                rag_logger.info(f"Chunk {i+1}: {doc.page_content[:100]}...")
            
            return relevant_docs
            
        except Exception as e:
            rag_logger.error(f"Error retrieving chunks: {str(e)}")
            return []
    
    def create_rag_prompt(self, query: str, relevant_chunks: List[Document], 
                         lesson_details: Optional[Dict[str, str]] = None) -> str:
        """
        Create a prompt with retrieved context for LLM
        
        Args:
            query: User query
            relevant_chunks: Retrieved relevant chunks
            lesson_details: Additional lesson details
            
        Returns:
            Formatted prompt with context
        """
        rag_logger.info("Creating RAG prompt")
        
        # Combine relevant chunks
        context = "\n\n".join([doc.page_content for doc in relevant_chunks])
        
        # Create base prompt
        if lesson_details and lesson_details.get('lesson_prompt'):
            user_prompt = lesson_details['lesson_prompt']
        else:
            user_prompt = query
        
        # Determine if user wants a lesson plan or direct answer
        wants_lesson_plan = self._user_wants_lesson_plan(user_prompt)
        
        if wants_lesson_plan:
            # Lesson plan prompt
            prompt_template = PromptTemplate(
                input_variables=["context", "user_prompt", "grade_level", "focus_area"],
                template="""Based on the following context from the uploaded document, create a comprehensive lesson plan.

Context:
{context}

User Request: {user_prompt}
Grade Level: {grade_level}
Focus Area: {focus_area}

Please create a structured lesson plan that includes:
1. Learning objectives
2. Key concepts and topics
3. Teaching activities
4. Assessment methods
5. Resources and materials

Format your response as a detailed lesson plan with clear sections and actionable steps."""
            )
            
            prompt = prompt_template.format(
                context=context,
                user_prompt=user_prompt,
                grade_level=lesson_details.get('grade_level', 'Not specified') if lesson_details else 'Not specified',
                focus_area=lesson_details.get('focus_area', 'Not specified') if lesson_details else 'Not specified'
            )
        else:
            # Direct answer prompt
            prompt_template = PromptTemplate(
                input_variables=["context", "user_prompt"],
                template="""Based on the following context from the uploaded document, please answer the user's question.

Context:
{context}

User Question: {user_prompt}

Please provide a comprehensive and accurate answer based on the provided context. If the context doesn't contain enough information to fully answer the question, please indicate what information is missing."""
            )
            
            prompt = prompt_template.format(
                context=context,
                user_prompt=user_prompt
            )
        
        rag_logger.info(f"Created RAG prompt, length: {len(prompt)} characters")
        return prompt
    
    def _user_wants_lesson_plan(self, prompt: str) -> bool:
        """
        Determine if user wants a lesson plan based on prompt content
        
        Args:
            prompt: User prompt
            
        Returns:
            True if user wants a lesson plan
        """
        lesson_keywords = [
            'lesson plan', 'lesson', 'teach', 'teaching', 'curriculum', 'syllabus',
            'learning objectives', 'activities', 'assessment', 'classroom', 'students',
            'educational', 'pedagogy', 'instruction', 'course', 'unit'
        ]
        
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in lesson_keywords)
    
    def save_index(self, filepath: str):
        """Save FAISS index to disk"""
        if self.index is not None:
            faiss.write_index(self.index, filepath)
            rag_logger.info(f"Index saved to: {filepath}")
    
    def load_index(self, filepath: str):
        """Load FAISS index from disk"""
        if os.path.exists(filepath):
            self.index = faiss.read_index(filepath)
            rag_logger.info(f"Index loaded from: {filepath}")
            return True
        return False

