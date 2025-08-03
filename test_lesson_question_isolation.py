#!/usr/bin/env python3
"""
Test script to verify that lesson questions are properly isolated between different lessons.
This script tests the backend functionality to ensure questions are stored with the correct lesson_id.
"""

import sqlite3
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.models import LessonFAQ

def test_lesson_question_isolation():
    """Test that questions are properly isolated between lessons"""
    
    print("Testing lesson question isolation...")
    
    # Test data
    lesson_1_id = 1
    lesson_2_id = 2
    question_1 = "What is climate?"
    question_2 = "What is physics?"
    
    # Clear any existing test data
    conn = sqlite3.connect('instance/chatbot.db')
    c = conn.cursor()
    c.execute('DELETE FROM lesson_faq WHERE lesson_id IN (?, ?)', (lesson_1_id, lesson_2_id))
    conn.commit()
    conn.close()
    
    # Log questions for different lessons
    print(f"Logging question for lesson {lesson_1_id}: {question_1}")
    LessonFAQ.log_question(lesson_1_id, question_1)
    
    print(f"Logging question for lesson {lesson_2_id}: {question_2}")
    LessonFAQ.log_question(lesson_2_id, question_2)
    
    # Log the same question again for lesson 1 to test counting
    print(f"Logging same question again for lesson {lesson_1_id}: {question_1}")
    LessonFAQ.log_question(lesson_1_id, question_1)
    
    # Retrieve questions for each lesson
    faqs_lesson_1 = LessonFAQ.get_top_faqs(lesson_1_id)
    faqs_lesson_2 = LessonFAQ.get_top_faqs(lesson_2_id)
    
    print(f"\nQuestions for lesson {lesson_1_id}:")
    for faq in faqs_lesson_1:
        print(f"  - {faq['question']} (asked {faq['count']} times)")
    
    print(f"\nQuestions for lesson {lesson_2_id}:")
    for faq in faqs_lesson_2:
        print(f"  - {faq['question']} (asked {faq['count']} times)")
    
    # Verify isolation
    lesson_1_questions = [faq['question'] for faq in faqs_lesson_1]
    lesson_2_questions = [faq['question'] for faq in faqs_lesson_2]
    
    # Check that questions are properly isolated
    assert question_1 in lesson_1_questions, f"Question '{question_1}' should be in lesson {lesson_1_id}"
    assert question_2 in lesson_2_questions, f"Question '{question_2}' should be in lesson {lesson_2_id}"
    assert question_1 not in lesson_2_questions, f"Question '{question_1}' should NOT be in lesson {lesson_2_id}"
    assert question_2 not in lesson_1_questions, f"Question '{question_2}' should NOT be in lesson {lesson_1_id}"
    
    # Check that counting works correctly
    lesson_1_faq = next((faq for faq in faqs_lesson_1 if faq['question'] == question_1), None)
    assert lesson_1_faq is not None, f"Question '{question_1}' should be found in lesson {lesson_1_id}"
    assert lesson_1_faq['count'] == 2, f"Question '{question_1}' should be asked 2 times, got {lesson_1_faq['count']}"
    
    lesson_2_faq = next((faq for faq in faqs_lesson_2 if faq['question'] == question_2), None)
    assert lesson_2_faq is not None, f"Question '{question_2}' should be found in lesson {lesson_2_id}"
    assert lesson_2_faq['count'] == 1, f"Question '{question_2}' should be asked 1 time, got {lesson_2_faq['count']}"
    
    print("\n✅ All tests passed! Lesson questions are properly isolated.")
    print("✅ Questions are stored with the correct lesson_id.")
    print("✅ Question counting works correctly.")
    
    return True

if __name__ == "__main__":
    try:
        test_lesson_question_isolation()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 