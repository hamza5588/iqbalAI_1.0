#!/usr/bin/env python3
"""
Test script to demonstrate the comprehensive lesson logging system
"""

import os
import sys
import logging
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_logging_system():
    """Test the lesson logging system"""
    print("=== TESTING LESSON LOGGING SYSTEM ===")
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Check if logs directory exists
    if not os.path.exists('logs'):
        print("Creating logs directory...")
        os.makedirs('logs')
    
    # Test the lesson logger
    print("\n1. Testing Lesson Generation Logger...")
    try:
        from app.routes.lesson_routes import lesson_logger
        lesson_logger.info("=== TEST LOGGING STARTED ===")
        lesson_logger.info("Testing lesson generation logging")
        lesson_logger.info("Session ID: test_session_123")
        lesson_logger.info("File uploaded: test_document.pdf")
        lesson_logger.info("Lesson Title: Test Lesson")
        lesson_logger.info("Lesson Prompt: Generate a lesson about photosynthesis")
        lesson_logger.info("Focus Area: Science")
        lesson_logger.info("Grade Level: Grade 5")
        lesson_logger.info("=== TEST LOGGING COMPLETED ===")
        print("✓ Lesson generation logging working")
    except Exception as e:
        print(f"✗ Lesson generation logging failed: {e}")
    
    # Test the teacher service logger
    print("\n2. Testing Teacher Service Logger...")
    try:
        from app.services.lesson.teacher_service import teacher_logger
        teacher_logger.info("=== TEACHER SERVICE TEST ===")
        teacher_logger.info("Testing teacher service logging")
        teacher_logger.info("File processing started")
        teacher_logger.info("Document loaded successfully: 5 pages/sections")
        teacher_logger.info("Text extracted successfully: 15000 characters")
        teacher_logger.info("AI lesson generation started")
        teacher_logger.info("LLM response received: lesson_plan")
        teacher_logger.info("Lesson plan generated successfully with 4 sections")
        teacher_logger.info("Learning objectives: 3")
        teacher_logger.info("Creative activities: 2")
        teacher_logger.info("Quiz questions: 5")
        teacher_logger.info("=== TEACHER SERVICE TEST COMPLETED ===")
        print("✓ Teacher service logging working")
    except Exception as e:
        print(f"✗ Teacher service logging failed: {e}")
    
    # Test the student service logger
    print("\n3. Testing Student Service Logger...")
    try:
        from app.services.lesson.student_service import student_logger
        student_logger.info("=== STUDENT SERVICE TEST ===")
        student_logger.info("Testing student service logging")
        student_logger.info("Lesson ID: 1")
        student_logger.info("Question: What is photosynthesis?")
        student_logger.info("Lesson loaded: 'Introduction to Climate' (ID: 1)")
        student_logger.info("Lesson content length: 500 characters")
        student_logger.info("Generating AI answer")
        student_logger.info("LLM answer generated - length: 250 characters")
        student_logger.info("Canonical question: What is photosynthesis?")
        student_logger.info("Logging question to FAQ")
        student_logger.info("=== STUDENT SERVICE TEST COMPLETED ===")
        print("✓ Student service logging working")
    except Exception as e:
        print(f"✗ Student service logging failed: {e}")
    
    # Check if log file was created
    print("\n4. Checking Log File...")
    log_file_path = 'logs/lesson.log'
    if os.path.exists(log_file_path):
        print(f"✓ Log file created: {log_file_path}")
        
        # Read and display last few lines
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
            print(f"✓ Log file contains {len(lines)} lines")
            print("\nLast 10 lines of log file:")
            for line in lines[-10:]:
                print(f"  {line.strip()}")
    else:
        print(f"✗ Log file not found: {log_file_path}")
    
    print(f"\n=== TEST COMPLETED AT {datetime.now().isoformat()} ===")

def show_log_structure():
    """Show the structure of the logging system"""
    print("\n=== LESSON LOGGING SYSTEM STRUCTURE ===")
    print("""
    📁 logs/
    └── lesson.log                    # Consolidated log file for all lesson activities
    
    🔧 Logging Components:
    
    1. LESSON GENERATION LOGGER (lesson_routes.py)
       - Session tracking
       - File upload details
       - User input validation
       - AI processing steps
       - Database operations
       - Response preparation
    
    2. TEACHER SERVICE LOGGER (teacher_service.py)
       - File processing steps
       - Document loading
       - Text extraction
       - AI lesson generation
       - DOCX generation
       - Error handling
    
    3. STUDENT SERVICE LOGGER (student_service.py)
       - Question processing
       - Lesson content loading
       - AI answer generation
       - Question canonicalization
       - FAQ logging
    
    📊 Log Format:
    YYYY-MM-DD HH:MM:SS - [SERVICE] - LEVEL - function:line - message
    
    📝 Example Log Entries:
    2024-01-15 14:30:15 - LESSON_GENERATION - INFO - create_lesson:42 - === LESSON GENERATION STARTED ===
    2024-01-15 14:30:15 - LESSON_GENERATION - INFO - create_lesson:64 - Session 123: File uploaded - document.pdf
    2024-01-15 14:30:16 - TEACHER_SERVICE - INFO - process_file:62 - === TEACHER FILE PROCESSING STARTED ===
    2024-01-15 14:30:17 - TEACHER_SERVICE - INFO - _generate_lesson_plan:231 - === LESSON PLAN GENERATION STARTED ===
    2024-01-15 14:30:20 - STUDENT_SERVICE - INFO - answer_lesson_question:49 - === STUDENT QUESTION PROCESSING STARTED ===
    """)

if __name__ == "__main__":
    test_logging_system()
    show_log_structure()





