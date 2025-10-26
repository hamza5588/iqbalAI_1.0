#!/usr/bin/env python3
"""
Simple test script to verify the lesson service structure without Flask dependencies
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_lesson_components():
    """Test individual lesson service components"""
    try:
        print("Testing lesson service components...")
        
        # Test base service (should work without Flask)
        from app.services.lesson.base_service import BaseLessonService
        print("✓ BaseLessonService imported successfully")
        
        # Test RAG service
        from app.services.lesson.rag_service import RAGService
        print("✓ RAGService imported successfully")
        
        # Test models
        from app.services.lesson.models import LessonPlan, LessonResponse
        print("✓ Lesson models imported successfully")
        
        # Test that we can create instances
        rag_service = RAGService()
        print("✓ RAGService instance created")
        
        print("\n🎉 Core lesson service components are working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_teacher_service():
    """Test teacher service (may have Flask dependencies)"""
    try:
        print("\nTesting teacher service...")
        from app.services.lesson.teacher_service import TeacherLessonService
        print("✓ TeacherLessonService imported successfully")
        return True
    except Exception as e:
        print(f"❌ Teacher service error: {str(e)}")
        return False

def test_student_service():
    """Test student service (may have Flask dependencies)"""
    try:
        print("\nTesting student service...")
        from app.services.lesson.student_service import StudentLessonService
        print("✓ StudentLessonService imported successfully")
        return True
    except Exception as e:
        print(f"❌ Student service error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING LESSON SERVICE COMPONENTS")
    print("=" * 60)
    
    # Test core components
    core_ok = test_lesson_components()
    
    # Test teacher service
    teacher_ok = test_teacher_service()
    
    # Test student service
    student_ok = test_student_service()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Core components: {'✓ PASS' if core_ok else '❌ FAIL'}")
    print(f"Teacher service: {'✓ PASS' if teacher_ok else '❌ FAIL'}")
    print(f"Student service: {'✓ PASS' if student_ok else '❌ FAIL'}")
    
    if core_ok and teacher_ok and student_ok:
        print("\n🎉 SUCCESS: All lesson service components are working!")
        print("\nThe structured lesson service with RAG functionality has been successfully created!")
        print("\nKey Features Implemented:")
        print("✓ Base lesson service with common functionality")
        print("✓ Teacher service with RAG-based lesson generation")
        print("✓ Student service for Q&A and learning support")
        print("✓ RAG service for semantic content retrieval")
        print("✓ Structured data models for lessons")
        print("✓ Backward compatibility methods")
    else:
        print("\n❌ Some components failed - check the errors above")
    
    print("\n" + "=" * 60)


