#!/usr/bin/env python3
"""
Test script for survey functionality
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"  # Adjust if your server runs on a different port
TEST_USER_EMAIL = "test@example.com"  # Use an existing user email
TEST_PASSWORD = "testpassword"  # Use the correct password

def test_survey_functionality():
    """Test the complete survey functionality"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("=== Testing Survey Functionality ===\n")
    
    # Step 1: Login
    print("1. Logging in...")
    login_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_PASSWORD
    }
    
    login_response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return False
    
    print("Login successful!\n")
    
    # Step 2: Check initial survey status
    print("2. Checking initial survey status...")
    status_response = session.get(f"{BASE_URL}/api/check_survey_status")
    print(f"Status check response: {status_response.status_code}")
    print(f"Status data: {status_response.json()}\n")
    
    # Step 3: Submit a survey
    print("3. Submitting survey...")
    survey_data = {
        "rating": 8,
        "message": "This is a test survey submission"
    }
    
    submit_response = session.post(f"{BASE_URL}/api/survey", json=survey_data)
    print(f"Submit response: {submit_response.status_code}")
    print(f"Submit data: {submit_response.json()}\n")
    
    # Step 4: Check survey status after submission
    print("4. Checking survey status after submission...")
    status_response2 = session.get(f"{BASE_URL}/api/check_survey_status")
    print(f"Status check response: {status_response2.status_code}")
    print(f"Status data: {status_response2.json()}\n")
    
    # Step 5: Try to submit another survey (should fail)
    print("5. Attempting to submit another survey (should fail)...")
    survey_data2 = {
        "rating": 9,
        "message": "This should fail"
    }
    
    submit_response2 = session.post(f"{BASE_URL}/api/survey", json=survey_data2)
    print(f"Second submit response: {submit_response2.status_code}")
    print(f"Second submit data: {submit_response2.json()}\n")
    
    # Step 6: Get survey responses
    print("6. Getting survey responses...")
    responses_response = session.get(f"{BASE_URL}/api/survey/responses")
    print(f"Responses response: {responses_response.status_code}")
    print(f"Responses data: {responses_response.json()}\n")
    
    print("=== Test Complete ===")
    return True

if __name__ == "__main__":
    test_survey_functionality() 