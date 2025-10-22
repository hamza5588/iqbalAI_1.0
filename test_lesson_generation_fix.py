#!/usr/bin/env python3
"""
Test script to verify the lesson generation fix works correctly
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_lesson_service_structure():
    """Test that the lesson service structure is working"""
    try:
        from app.services.lesson_service import LessonService
        from app.services.lesson.teacher_service import TeacherLessonService
        from app.services.lesson.student_service import StudentLessonService
        
        print("✅ All lesson service imports successful")
        
        # Test service initialization
        api_key = "test_key"
        main_service = LessonService(api_key)
        teacher_service = TeacherLessonService(api_key)
        student_service = StudentLessonService(api_key)
        
        print("✅ All services initialized successfully")
        
        # Test that main service has sub-services
        assert hasattr(main_service, 'teacher_service')
        assert hasattr(main_service, 'student_service')
        print("✅ Main service has sub-services")
        
        return True
        
    except Exception as e:
        print(f"❌ Service structure test failed: {e}")
        return False

def test_intent_detection():
    """Test the intent detection logic"""
    try:
        from app.services.lesson.teacher_service import TeacherLessonService
        
        api_key = "test_key"
        service = TeacherLessonService(api_key)
        
        # Test lesson plan detection
        lesson_phrases = [
            "generate lesson from this content",
            "create a lesson plan",
            "make a teaching plan"
        ]
        
        for phrase in lesson_phrases:
            result = service._user_wants_lesson_plan(phrase)
            if not result:
                print(f"❌ Failed to detect lesson intent for: '{phrase}'")
                return False
        
        # Test direct answer detection
        question_phrases = [
            "what is photosynthesis",
            "how does this work",
            "explain the concept"
        ]
        
        for phrase in question_phrases:
            result = service._user_wants_lesson_plan(phrase)
            if result:
                print(f"❌ Incorrectly detected lesson intent for question: '{phrase}'")
                return False
        
        print("✅ Intent detection working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Intent detection test failed: {e}")
        return False

def test_route_imports():
    """Test that the route file can import the lesson service"""
    try:
        from app.routes.lesson_routes import bp
        print("✅ Lesson routes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Route import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing lesson generation fix...")
    print("=" * 50)
    
    tests = [
        test_lesson_service_structure,
        test_intent_detection,
        test_route_imports
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
        print("🎉 All tests passed! The lesson generation fix should work correctly.")
        print("\nKey improvements made:")
        print("1. ✅ Simplified teacher service with clear intent detection")
        print("2. ✅ Fixed route response structure handling")
        print("3. ✅ Better content formatting for both lesson plans and direct answers")
        print("4. ✅ Maintained backward compatibility")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)