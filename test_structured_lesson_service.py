#!/usr/bin/env python3
"""
Test script to verify the new structured lesson service works correctly
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all imports work correctly"""
    try:
        from app.services.lesson_service import LessonService
        from app.services.lesson import TeacherLessonService, StudentLessonService
        from app.services.lesson.models import LessonPlan, LessonResponse, DirectAnswer
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_service_initialization():
    """Test that services can be initialized"""
    try:
        # Mock API key for testing
        api_key = "test_key"
        
        # Test main service
        main_service = LessonService(api_key)
        print("✅ Main LessonService initialized")
        
        # Test individual services
        teacher_service = TeacherLessonService(api_key)
        student_service = StudentLessonService(api_key)
        print("✅ Individual services initialized")
        
        # Test that main service has the sub-services
        assert hasattr(main_service, 'teacher_service')
        assert hasattr(main_service, 'student_service')
        print("✅ Main service has sub-services")
        
        return True
    except Exception as e:
        print(f"❌ Service initialization error: {e}")
        return False

def test_delegation():
    """Test that delegation works correctly"""
    try:
        api_key = "test_key"
        main_service = LessonService(api_key)
        
        # Test that methods are properly delegated
        assert hasattr(main_service, 'process_file')
        assert hasattr(main_service, 'answer_lesson_question')
        assert hasattr(main_service, 'create_ppt')
        assert hasattr(main_service, 'get_lesson_faqs')
        print("✅ All delegation methods present")
        
        return True
    except Exception as e:
        print(f"❌ Delegation test error: {e}")
        return False

def test_models():
    """Test that Pydantic models work correctly"""
    try:
        from app.services.lesson.models import Section, CreativeActivity, LessonPlan
        
        # Test Section model
        section = Section(heading="Test Section", content="Test content")
        assert section.heading == "Test Section"
        assert section.content == "Test content"
        print("✅ Section model works")
        
        # Test CreativeActivity model
        activity = CreativeActivity(
            name="Test Activity",
            description="Test description",
            duration="15 minutes",
            learning_purpose="Test purpose"
        )
        assert activity.name == "Test Activity"
        print("✅ CreativeActivity model works")
        
        # Test LessonPlan model
        lesson = LessonPlan(
            title="Test Lesson",
            summary="Test summary",
            learning_objectives=["Objective 1", "Objective 2"],
            background_prerequisites=["Prereq 1"],
            sections=[section],
            key_concepts=["Concept 1"],
            creative_activities=[activity],
            stem_equations=[],
            assessment_quiz=[],
            teacher_notes=["Note 1"]
        )
        assert lesson.title == "Test Lesson"
        print("✅ LessonPlan model works")
        
        return True
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing structured lesson service...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_service_initialization,
        test_delegation,
        test_models
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
        print("🎉 All tests passed! The structured lesson service is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



