#!/usr/bin/env python3
"""
Test script to debug lesson content update issue
"""

import sqlite3
import json
from datetime import datetime

def test_lesson_update():
    """Test the lesson update functionality"""
    
    # Connect to the database
    db_path = 'instance/chatbot.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== Lesson Update Debug Test ===")
    
    # Get all lessons
    cursor.execute("SELECT id, title, content, updated_at FROM lessons ORDER BY id DESC LIMIT 5")
    lessons = cursor.fetchall()
    
    print(f"\nFound {len(lessons)} recent lessons:")
    for lesson in lessons:
        content_preview = lesson['content'][:100] + '...' if lesson['content'] and len(lesson['content']) > 100 else lesson['content']
        print(f"  ID: {lesson['id']}, Title: {lesson['title']}")
        print(f"    Content length: {len(lesson['content']) if lesson['content'] else 0}")
        print(f"    Content preview: {content_preview}")
        print(f"    Updated at: {lesson['updated_at']}")
        print()
    
    # Test updating a lesson
    if lessons:
        test_lesson_id = lessons[0]['id']
        print(f"Testing update on lesson ID: {test_lesson_id}")
        
        # Get current content
        cursor.execute("SELECT content FROM lessons WHERE id = ?", (test_lesson_id,))
        current_lesson = cursor.fetchone()
        current_content = current_lesson['content'] if current_lesson else ""
        
        print(f"Current content length: {len(current_content)}")
        
        # Create test content
        test_content = f"TEST UPDATE - {datetime.now().isoformat()}\n\n{current_content}"
        
        # Update the lesson
        cursor.execute("""
            UPDATE lessons 
            SET content = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (test_content, test_lesson_id))
        
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT content, updated_at FROM lessons WHERE id = ?", (test_lesson_id,))
        updated_lesson = cursor.fetchone()
        
        if updated_lesson:
            print(f"Update successful!")
            print(f"New content length: {len(updated_lesson['content'])}")
            print(f"Updated at: {updated_lesson['updated_at']}")
            print(f"Content starts with: {updated_lesson['content'][:100]}...")
        else:
            print("Update failed - lesson not found")
    
    conn.close()

if __name__ == "__main__":
    test_lesson_update()




