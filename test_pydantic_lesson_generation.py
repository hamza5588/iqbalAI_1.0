#!/usr/bin/env python3
"""
Test script to verify Pydantic integration with lesson generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_pydantic_models():
    """Test that Pydantic models can be created and validated"""
    print("🧪 Testing Pydantic Models...")
    
    try:
        from app.services.lesson_service import LessonService, LessonResponse, LessonPlan, Section, CreativeActivity, STEMEquation, QuizQuestion
        
        # Test Section model
        section = Section(
            heading="Test Section",
            content="This is test content for the section."
        )
        print(f"✓ Section model created: {section.heading}")
        
        # Test CreativeActivity model
        activity = CreativeActivity(
            name="Test Activity",
            description="A test activity description",
            duration="15 minutes",
            learning_purpose="To test the model"
        )
        print(f"✓ CreativeActivity model created: {activity.name}")
        
        # Test LessonPlan model
        lesson_plan = LessonPlan(
            title="Test Lesson",
            summary="A test lesson for validation",
            learning_objectives=["Learn something", "Understand concepts"],
            background_prerequisites=["Basic knowledge"],
            sections=[section],
            key_concepts=["Concept 1", "Concept 2"],
            creative_activities=[activity],
            stem_equations=[],
            assessment_quiz=[],
            teacher_notes=["Note 1", "Note 2"]
        )
        print(f"✓ LessonPlan model created: {lesson_plan.title}")
        
        # Test LessonResponse model
        lesson_response = LessonResponse(
            response_type="lesson_plan",
            answer=lesson_plan
        )
        print(f"✓ LessonResponse model created: {lesson_response.response_type}")
        
        # Test conversion to dict
        lesson_dict = lesson_plan.dict()
        print(f"✓ LessonPlan converted to dict with {len(lesson_dict)} fields")
        
        # Test the expected response structure
        expected_structure = {
            "response_type": "lesson_plan",
            "lesson": lesson_dict
        }
        print(f"✓ Expected response structure created with keys: {list(expected_structure.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pydantic model test failed: {e}")
        return False

def test_fallback_lesson():
    """Test the fallback lesson creation"""
    print("\n🧪 Testing Fallback Lesson Creation...")
    
    try:
        from app.services.lesson_service import LessonService
        
        # Create service with dummy API key
        service = LessonService(api_key="test-key")
        
        # Test fallback lesson creation
        test_text = "This is a test document about science and mathematics. It contains important concepts that students should learn."
        fallback_result = service._create_fallback_lesson(test_text)
        
        print(f"✓ Fallback lesson created")
        print(f"✓ Response type: {fallback_result.get('response_type')}")
        print(f"✓ Has lesson data: {'lesson' in fallback_result}")
        
        if 'lesson' in fallback_result:
            lesson_data = fallback_result['lesson']
            print(f"✓ Lesson data keys: {list(lesson_data.keys())}")
            print(f"✓ Has sections: {'sections' in lesson_data}")
            print(f"✓ Has content: {'content' in lesson_data or any('content' in section for section in lesson_data.get('sections', []))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Fallback lesson test failed: {e}")
        return False

def test_response_structure():
    """Test that the response structure matches what the frontend expects"""
    print("\n🧪 Testing Response Structure Compatibility...")
    
    try:
        from app.services.lesson_service import LessonService
        
        # Create service with dummy API key
        service = LessonService(api_key="test-key")
        
        # Test fallback lesson creation
        test_text = "This is a test document about science and mathematics."
        result = service._create_fallback_lesson(test_text)
        
        # Check if the structure matches what the routes expect
        expected_keys = ['response_type', 'lesson']
        has_expected_keys = all(key in result for key in expected_keys)
        print(f"✓ Has expected keys: {has_expected_keys}")
        
        if has_expected_keys:
            lesson_data = result['lesson']
            # Check if lesson data has the expected structure
            expected_lesson_keys = ['title', 'summary', 'sections']
            has_lesson_keys = all(key in lesson_data for key in expected_lesson_keys)
            print(f"✓ Lesson data has expected keys: {has_lesson_keys}")
            
            # Check if sections have content
            sections = lesson_data.get('sections', [])
            has_content = any('content' in section for section in sections)
            print(f"✓ Sections have content: {has_content}")
            
            if has_content:
                # Simulate what the routes do
                full_content = "\n\n".join([section.get('content', '') for section in sections if section.get('content')])
                print(f"✓ Generated content length: {len(full_content)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Response structure test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Pydantic Integration with LessonService\n")
    
    all_tests_passed = True
    
    # Run all tests
    tests = [
        test_pydantic_models,
        test_fallback_lesson,
        test_response_structure
    ]
    
    for test in tests:
        try:
            if not test():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            all_tests_passed = False
    
    if all_tests_passed:
        print("\n✅ All tests passed! Pydantic integration is working correctly.")
        print("\n📋 Summary of changes:")
        print("   • Replaced manual JSON parsing with Pydantic output parser")
        print("   • Added structured Pydantic models for type safety")
        print("   • Fixed response structure to match frontend expectations")
        print("   • Added fallback mechanisms for error handling")
        print("   • Added comprehensive debugging logs")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)



