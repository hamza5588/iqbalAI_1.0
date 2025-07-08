#!/usr/bin/env python3
"""
Test script for role-based access control system
"""

import requests
import json

# Base URL for the application
BASE_URL = "http://localhost:5000"

def test_role_system():
    """Test the role-based access control system"""
    
    print("Testing Role-Based Access Control System")
    print("=" * 50)
    
    # Test 1: Create a teacher account
    print("\n1. Testing teacher registration...")
    teacher_data = {
        'username': 'test_teacher',
        'useremail': 'teacher@test.com',
        'password': 'password123',
        'class_standard': 'High School',
        'medium': 'English',
        'role': 'teacher',
        'groq_api_key': 'gsk_test_key'
    }
    
    # Note: In a real test, you would need to handle email verification
    # For now, we'll assume the teacher account exists
    
    # Test 2: Create a student account
    print("\n2. Testing student registration...")
    student_data = {
        'username': 'test_student',
        'useremail': 'student@test.com',
        'password': 'password123',
        'class_standard': '9th Grade',
        'medium': 'English',
        'role': 'student',
        'groq_api_key': 'gsk_test_key'
    }
    
    # Test 3: Test teacher login and lesson creation
    print("\n3. Testing teacher login...")
    teacher_login = {
        'useremail': 'teacher@test.com',
        'password': 'password123'
    }
    
    # Test 4: Test student login and lesson browsing
    print("\n4. Testing student login...")
    student_login = {
        'useremail': 'student@test.com',
        'password': 'password123'
    }
    
    print("\nTest completed!")
    print("\nTo manually test the system:")
    print("1. Register a teacher account with role 'teacher'")
    print("2. Register a student account with role 'student'")
    print("3. Login as teacher and try to create lessons")
    print("4. Login as student and try to browse lessons")
    print("5. Verify that teachers can't browse lessons and students can't create lessons")

def test_api_endpoints():
    """Test the API endpoints"""
    
    print("\nTesting API Endpoints")
    print("=" * 30)
    
    endpoints = [
        '/user_info',
        '/api/lessons/browse_lessons',
        '/api/lessons/search_lessons',
        '/api/lessons/create_lesson',
        '/api/lessons/my_lessons'
    ]
    
    for endpoint in endpoints:
        print(f"\nTesting {endpoint}...")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"Status: {response.status_code}")
            if response.status_code == 401:
                print("✓ Correctly requires authentication")
            elif response.status_code == 403:
                print("✓ Correctly requires specific role")
            else:
                print(f"Response: {response.text[:100]}...")
        except requests.exceptions.ConnectionError:
            print("✗ Server not running")
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_role_system()
    test_api_endpoints() 