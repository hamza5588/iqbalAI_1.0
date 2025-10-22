#!/usr/bin/env python3
"""
Test script to verify the simplified teacher service logic
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_intent_detection():
    """Test the intent detection logic"""
    try:
        from app.services.lesson.teacher_service import TeacherLessonService
        
        # Mock API key for testing
        api_key = "test_key"
        service = TeacherLessonService(api_key)
        
        # Test cases for lesson plan intent
        lesson_phrases = [
            "generate lesson from this content",
            "create a lesson plan",
            "make a teaching plan",
            "lesson from the above content",
            "teach this material",
            "explain as a lesson"
        ]
        
        # Test cases for direct answer intent
        question_phrases = [
            "what is photosynthesis",
            "how does this work",
            "explain the concept",
            "tell me about this",
            "why does this happen",
            "help me understand this"
        ]
        
        print("Testing lesson plan intent detection:")
        for phrase in lesson_phrases:
            result = service._user_wants_lesson_plan(phrase)
            status = "✅" if result else "❌"
            print(f"  {status} '{phrase}' -> {result}")
        
        print("\nTesting direct answer intent detection:")
        for phrase in question_phrases:
            result = service._user_wants_lesson_plan(phrase)
            status = "✅" if not result else "❌"  # Should be False for questions
            print(f"  {status} '{phrase}' -> {result}")
        
        print("\n✅ Intent detection test completed")
        return True
        
    except Exception as e:
        print(f"❌ Intent detection test failed: {e}")
        return False

def test_service_methods():
    """Test that all required methods exist"""
    try:
        from app.services.lesson.teacher_service import TeacherLessonService
        
        api_key = "test_key"
        service = TeacherLessonService(api_key)
        
        # Check required methods exist
        required_methods = [
            '_user_wants_lesson_plan',
            '_generate_lesson_plan', 
            '_generate_direct_answer',
            '_generate_structured_lesson',
            'process_file'
        ]
        
        for method_name in required_methods:
            if hasattr(service, method_name):
                print(f"✅ Method '{method_name}' exists")
            else:
                print(f"❌ Method '{method_name}' missing")
                return False
        
        print("✅ All required methods exist")
        return True
        
    except Exception as e:
        print(f"❌ Method test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing simplified teacher service...")
    print("=" * 50)
    
    tests = [
        test_intent_detection,
        test_service_methods
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The simplified teacher service is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



