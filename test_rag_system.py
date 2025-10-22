#!/usr/bin/env python3
"""
Test script for RAG (Retrieval-Augmented Generation) system
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.lesson.rag_service import RAGService
from langchain_core.documents import Document

def test_rag_system():
    """Test the RAG system with sample content"""
    print("=== RAG System Test ===")
    
    # Create sample large document
    large_content = """
    # Introduction to Machine Learning
    
    Machine Learning (ML) is a subset of artificial intelligence (AI) that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience, without being explicitly programmed.
    
    ## Types of Machine Learning
    
    ### Supervised Learning
    Supervised learning is a type of machine learning where the algorithm learns from labeled training data. The goal is to learn a mapping from inputs to outputs based on example input-output pairs.
    
    Common supervised learning algorithms include:
    - Linear Regression
    - Logistic Regression
    - Decision Trees
    - Random Forest
    - Support Vector Machines (SVM)
    - Neural Networks
    
    ### Unsupervised Learning
    Unsupervised learning is a type of machine learning where the algorithm learns patterns from data without labeled examples. The goal is to find hidden patterns or groupings in the data.
    
    Common unsupervised learning algorithms include:
    - K-Means Clustering
    - Hierarchical Clustering
    - Principal Component Analysis (PCA)
    - DBSCAN
    - Gaussian Mixture Models
    
    ### Reinforcement Learning
    Reinforcement learning is a type of machine learning where an agent learns to make decisions by taking actions in an environment to maximize cumulative reward.
    
    ## Data Preprocessing
    
    Data preprocessing is a crucial step in machine learning that involves cleaning and transforming raw data into a format suitable for analysis.
    
    Common preprocessing steps include:
    1. Data Cleaning: Handling missing values, outliers, and inconsistencies
    2. Data Integration: Combining data from multiple sources
    3. Data Transformation: Normalizing, scaling, and encoding categorical variables
    4. Data Reduction: Dimensionality reduction and feature selection
    
    ## Model Evaluation
    
    Model evaluation is the process of assessing the performance of a machine learning model on unseen data.
    
    Common evaluation metrics include:
    - Accuracy: The proportion of correct predictions
    - Precision: The proportion of true positives among predicted positives
    - Recall: The proportion of true positives among actual positives
    - F1-Score: The harmonic mean of precision and recall
    - ROC-AUC: The area under the receiver operating characteristic curve
    
    ## Cross-Validation
    
    Cross-validation is a technique used to assess how well a model will generalize to an independent dataset.
    
    Common cross-validation techniques include:
    - K-Fold Cross-Validation
    - Stratified K-Fold Cross-Validation
    - Leave-One-Out Cross-Validation
    - Time Series Cross-Validation
    
    ## Feature Engineering
    
    Feature engineering is the process of creating new features or modifying existing ones to improve model performance.
    
    Common feature engineering techniques include:
    - Feature Scaling: Normalization and standardization
    - Feature Selection: Choosing the most relevant features
    - Feature Creation: Creating new features from existing ones
    - Feature Transformation: Applying mathematical transformations
    
    ## Hyperparameter Tuning
    
    Hyperparameter tuning is the process of finding the optimal hyperparameters for a machine learning model.
    
    Common hyperparameter tuning techniques include:
    - Grid Search: Exhaustive search over a specified parameter grid
    - Random Search: Random sampling of parameter combinations
    - Bayesian Optimization: Using Bayesian methods to find optimal parameters
    - Genetic Algorithms: Using evolutionary algorithms for optimization
    
    ## Model Deployment
    
    Model deployment is the process of making a trained machine learning model available for use in production environments.
    
    Common deployment considerations include:
    - Model Serialization: Saving and loading trained models
    - API Development: Creating interfaces for model inference
    - Monitoring: Tracking model performance in production
    - Scaling: Handling increased load and traffic
    
    ## Best Practices
    
    Some best practices for machine learning projects include:
    1. Start with simple models and gradually increase complexity
    2. Use cross-validation to assess model performance
    3. Pay attention to data quality and preprocessing
    4. Document your process and results
    5. Consider the business context and requirements
    6. Monitor model performance in production
    7. Keep models updated with new data
    
    ## Common Challenges
    
    Machine learning projects often face several challenges:
    - Data Quality: Poor quality or insufficient data
    - Overfitting: Model performs well on training data but poorly on test data
    - Underfitting: Model is too simple to capture underlying patterns
    - Bias and Fairness: Models may exhibit bias against certain groups
    - Interpretability: Understanding how models make decisions
    - Scalability: Handling large datasets and high-frequency updates
    
    ## Future Directions
    
    The field of machine learning continues to evolve with new techniques and applications:
    - Deep Learning: Neural networks with multiple layers
    - Transfer Learning: Using pre-trained models for new tasks
    - AutoML: Automated machine learning pipelines
    - Explainable AI: Making models more interpretable
    - Federated Learning: Training models across decentralized data
    - Edge Computing: Running models on edge devices
    
    ## Conclusion
    
    Machine learning is a powerful tool for solving complex problems and extracting insights from data. Success in machine learning requires a combination of technical skills, domain knowledge, and practical experience. By following best practices and staying updated with the latest developments, practitioners can build effective machine learning solutions that provide real value.
    """ * 3  # Make it even larger to trigger RAG
    
    print(f"Created large document with {len(large_content)} characters")
    
    # Initialize RAG service
    rag_service = RAGService()
    
    # Create document
    doc = Document(page_content=large_content, metadata={"title": "Machine Learning Guide"})
    
    # Test if RAG should be used
    should_use_rag = rag_service.should_use_rag(large_content)
    print(f"Should use RAG: {should_use_rag}")
    
    if should_use_rag:
        # Process document
        print("Processing document with RAG...")
        result = rag_service.process_document([doc], "ml_guide")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            return
        
        print(f"RAG processing completed. Created {len(result['chunks'])} chunks")
        
        # Test retrieval
        queries = [
            "What is supervised learning?",
            "Explain cross-validation",
            "What are the best practices for machine learning?",
            "How do you handle overfitting?"
        ]
        
        for query in queries:
            print(f"\n--- Query: {query} ---")
            relevant_chunks = rag_service.retrieve_relevant_chunks(query, k=2)
            print(f"Retrieved {len(relevant_chunks)} relevant chunks")
            
            for i, chunk in enumerate(relevant_chunks):
                print(f"Chunk {i+1}: {chunk.page_content[:200]}...")
        
        # Test RAG prompt creation
        print("\n--- Testing RAG Prompt Creation ---")
        test_query = "What is machine learning?"
        relevant_chunks = rag_service.retrieve_relevant_chunks(test_query, k=3)
        rag_prompt = rag_service.create_rag_prompt(test_query, relevant_chunks)
        print(f"RAG prompt length: {len(rag_prompt)} characters")
        print(f"RAG prompt preview: {rag_prompt[:500]}...")
        
    else:
        print("Document is too small for RAG, using direct processing")
    
    print("\n=== RAG System Test Completed ===")

if __name__ == "__main__":
    test_rag_system()





