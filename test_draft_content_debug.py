#!/usr/bin/env python3
"""
Test script to debug why new version gets original content instead of AI-produced draft content.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_draft_content_debug():
    """Test and debug the draft content issue"""
    print("🧪 Debugging Draft Content Issue")
    print("=" * 60)
    
    with open('templates/chat.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check if frontend is sending content in payload
    print("\n1. Checking if frontend sends content in payload...")
    
    if 'content: content,' in content:
        print("✅ Frontend sends content in payload")
    else:
        print("❌ Frontend does NOT send content in payload")
        return False
    
    # Test 2: Check if debug logging is added to frontend
    print("\n2. Checking if debug logging is added to frontend...")
    
    if 'DEBUG: finalizeAIVersion - payload being sent:' in content:
        print("✅ Debug logging is added to frontend")
    else:
        print("❌ Debug logging is NOT added to frontend")
        return False
    
    # Test 3: Check if backend has debug logging
    print("\n3. Checking if backend has debug logging...")
    
    with open('app/routes/lesson_routes.py', 'r', encoding='utf-8') as f:
        backend_content = f.read()
    
    if 'DEBUG: create_lesson_version - received data:' in backend_content:
        print("✅ Backend has debug logging")
    else:
        print("❌ Backend does NOT have debug logging")
        return False
    
    # Test 4: Check if models have debug logging
    print("\n4. Checking if models have debug logging...")
    
    with open('app/models/models.py', 'r', encoding='utf-8') as f:
        models_content = f.read()
    
    if 'DEBUG: create_new_version - content length:' in models_content:
        print("✅ Models have debug logging")
    else:
        print("❌ Models do NOT have debug logging")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All debug logging is in place!")
    print("\n📋 Debug workflow:")
    print("   1. ✅ Frontend logs the payload being sent")
    print("   2. ✅ Backend logs the received data")
    print("   3. ✅ Models log the content being saved")
    
    print("\n🔍 To debug the issue:")
    print("   1. Login as a teacher")
    print("   2. Go to View Lessons")
    print("   3. Click on a lesson to open AI versioning")
    print("   4. Apply an AI prompt to modify the content")
    print("   5. Click 'Finalize New Version'")
    print("   6. Check browser console for frontend debug logs")
    print("   7. Check server logs for backend debug logs")
    print("   8. Compare the content being sent vs received")
    
    print("\n🚨 Common issues to check:")
    print("   • Is the draft content actually populated after AI prompt?")
    print("   • Is the content field being sent in the request?")
    print("   • Is the backend receiving the content field?")
    print("   • Is the content being passed correctly to create_new_version?")
    
    return True

if __name__ == "__main__":
    try:
        success = test_draft_content_debug()
        if success:
            print("\n✅ Debug setup completed successfully!")
        else:
            print("\n❌ Debug setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Debug setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
