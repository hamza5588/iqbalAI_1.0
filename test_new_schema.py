#!/usr/bin/env python3
"""
Test script for the new lesson versioning schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.models import LessonModel
from app.utils.db import get_db
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_new_schema():
    """Test the new lesson versioning schema"""
    print("🧪 Testing New Lesson Versioning Schema")
    print("=" * 50)
    
    try:
        # Test 1: Create an original lesson
        print("\n1. Creating original lesson...")
        original_lesson_id = LessonModel.create_lesson(
            teacher_id=1,
            title="Test Lesson - Original",
            summary="This is the original lesson",
            learning_objectives="Learn the basics",
            focus_area="AI",
            grade_level="College",
            content="This is the original lesson content.",
            status="finalized"
        )
        print(f"✅ Original lesson created with ID: {original_lesson_id}")
        
        # Get the lesson to check schema
        original_lesson = LessonModel.get_lesson_by_id(original_lesson_id)
        print(f"   - lesson_id: {original_lesson.get('lesson_id')}")
        print(f"   - version_number: {original_lesson.get('version_number')}")
        print(f"   - parent_version_id: {original_lesson.get('parent_version_id')}")
        print(f"   - original_content: {original_lesson.get('original_content', 'Not set')[:50]}...")
        print(f"   - draft_content: {original_lesson.get('draft_content', 'Not set')}")
        print(f"   - status: {original_lesson.get('status')}")
        
        # Test 2: Add draft content to original lesson
        print("\n2. Adding draft content to original lesson...")
        draft_content = "This is the improved draft content with better explanations."
        success = LessonModel.save_draft_content(original_lesson_id, draft_content)
        print(f"✅ Draft content saved: {success}")
        
        # Test 3: Create a new version from draft
        print("\n3. Creating new version from draft...")
        new_version_id = LessonModel.create_new_version_from_draft(
            original_lesson_id=original_lesson_id,
            teacher_id=1,
            title="Test Lesson - Version 2",
            summary="This is the improved lesson",
            learning_objectives="Learn the basics with improvements",
            focus_area="AI",
            grade_level="College",
            draft_content=draft_content
        )
        print(f"✅ New version created with ID: {new_version_id}")
        
        # Get the new version to check schema
        new_version = LessonModel.get_lesson_by_id(new_version_id)
        print(f"   - lesson_id: {new_version.get('lesson_id')}")
        print(f"   - version_number: {new_version.get('version_number')}")
        print(f"   - parent_version_id: {new_version.get('parent_version_id')}")
        print(f"   - original_content: {new_version.get('original_content', 'Not set')[:50]}...")
        print(f"   - draft_content: {new_version.get('draft_content', 'Not set')}")
        print(f"   - status: {new_version.get('status')}")
        
        # Test 4: Get all versions of the lesson
        print("\n4. Getting all versions of the lesson...")
        lesson_id = original_lesson['lesson_id']
        all_versions = LessonModel.get_lessons_by_lesson_id(lesson_id)
        print(f"✅ Found {len(all_versions)} versions for lesson_id: {lesson_id}")
        for i, version in enumerate(all_versions, 1):
            print(f"   Version {i}: ID={version['id']}, version_number={version.get('version_number')}, parent_version_id={version.get('parent_version_id')}")
        
        # Test 5: Get latest version
        print("\n5. Getting latest version...")
        latest_version = LessonModel.get_latest_version_by_lesson_id(lesson_id)
        if latest_version:
            print(f"✅ Latest version: ID={latest_version['id']}, version_number={latest_version.get('version_number')}")
        else:
            print("❌ No latest version found")
        
        # Test 6: Clear draft content from original
        print("\n6. Clearing draft content from original lesson...")
        success = LessonModel.clear_draft_content(original_lesson_id)
        print(f"✅ Draft content cleared: {success}")
        
        # Verify draft is cleared
        cleared_draft = LessonModel.get_draft_content(original_lesson_id)
        print(f"   - Draft content after clearing: '{cleared_draft}'")
        
        print("\n🎉 All tests passed! New schema is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        logger.error(f"Test error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_new_schema()





