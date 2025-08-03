#!/usr/bin/env python3
"""
Test script to verify that lesson chat history is properly saved and retrieved.
This script tests the new lesson chat history functionality.
"""

import sqlite3
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.models import LessonChatHistory

def test_lesson_chat_history():
    """Test that lesson chat history is properly saved and retrieved"""
    
    print("Testing lesson chat history functionality...")
    
    # Ensure the table exists
    LessonChatHistory.create_table()
    
    # Test data
    lesson_id = 1
    user_id = 1
    question_1 = "What is climate?"
    answer_1 = "Climate refers to the long-term patterns of temperature, humidity, wind, and precipitation in a particular region."
    question_2 = "How does climate differ from weather?"
    answer_2 = "Weather describes short-term atmospheric conditions, while climate represents the average weather conditions over a period of 30 years or more."
    
    # Clear any existing test data
    conn = sqlite3.connect('instance/chatbot.db')
    c = conn.cursor()
    c.execute('DELETE FROM lesson_chat_history WHERE lesson_id = ? AND user_id = ?', (lesson_id, user_id))
    conn.commit()
    conn.close()
    
    # Test saving Q&A pairs
    print(f"Saving Q&A pair 1 for lesson {lesson_id}, user {user_id}")
    chat_id_1 = LessonChatHistory.save_qa(lesson_id, user_id, question_1, answer_1)
    print(f"Saved with ID: {chat_id_1}")
    
    print(f"Saving Q&A pair 2 for lesson {lesson_id}, user {user_id}")
    chat_id_2 = LessonChatHistory.save_qa(lesson_id, user_id, question_2, answer_2)
    print(f"Saved with ID: {chat_id_2}")
    
    # Test retrieving chat history
    print(f"\nRetrieving chat history for lesson {lesson_id}, user {user_id}")
    history = LessonChatHistory.get_lesson_chat_history(lesson_id, user_id)
    
    print(f"Found {len(history)} Q&A pairs:")
    for i, item in enumerate(history, 1):
        print(f"  {i}. Q: {item['question']}")
        print(f"     A: {item['answer']}")
        print(f"     Time: {item['created_at']}")
        print()
    
    # Verify the data
    assert len(history) == 2, f"Expected 2 Q&A pairs, got {len(history)}"
    assert history[0]['question'] == question_1, f"First question should be '{question_1}'"
    assert history[0]['answer'] == answer_1, f"First answer should be '{answer_1}'"
    assert history[1]['question'] == question_2, f"Second question should be '{question_2}'"
    assert history[1]['answer'] == answer_2, f"Second answer should be '{answer_2}'"
    
    # Test clearing chat history
    print(f"Clearing chat history for lesson {lesson_id}, user {user_id}")
    LessonChatHistory.clear_lesson_chat_history(lesson_id, user_id)
    
    # Verify history is cleared
    history_after_clear = LessonChatHistory.get_lesson_chat_history(lesson_id, user_id)
    assert len(history_after_clear) == 0, f"History should be empty after clearing, got {len(history_after_clear)} items"
    
    print("\n✅ All tests passed! Lesson chat history functionality is working correctly.")
    print("✅ Q&A pairs are properly saved to the database.")
    print("✅ Chat history is correctly retrieved.")
    print("✅ Chat history can be cleared.")
    
    return True

if __name__ == "__main__":
    try:
        test_lesson_chat_history()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 