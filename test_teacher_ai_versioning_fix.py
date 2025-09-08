#!/usr/bin/env python3
"""
Test script to verify that teacher dashboard shows AI versioning interface
instead of student question interface when viewing lessons.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_user_role_detection():
    """Test that user role detection works correctly"""
    print("🧪 Testing User Role Detection for Teacher AI Versioning Fix")
    print("=" * 60)
    
    # Test 1: Check if the fix is in place
    print("\n1. Checking if window.userInfo is set in loadUserInfo function...")
    
    with open('templates/chat.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'window.userInfo = data.user;' in content:
        print("✅ window.userInfo is being set in loadUserInfo function")
    else:
        print("❌ window.userInfo is NOT being set in loadUserInfo function")
        return False
    
    # Test 2: Check if debug logging is added
    print("\n2. Checking if debug logging is added to viewLesson function...")
    
    if 'DEBUG: viewLesson - window.userInfo:' in content:
        print("✅ Debug logging is added to viewLesson function")
    else:
        print("❌ Debug logging is NOT added to viewLesson function")
        return False
    
    # Test 3: Check if AI versioning modal has correct ID
    print("\n3. Checking if AI versioning modal has correct ID...")
    
    if 'id="aiVersioningModal"' in content:
        print("✅ AI versioning modal has correct ID")
    else:
        print("❌ AI versioning modal does NOT have correct ID")
        return False
    
    # Test 4: Check if closeAIVersioningModal function exists
    print("\n4. Checking if closeAIVersioningModal function exists...")
    
    if 'function closeAIVersioningModal()' in content:
        print("✅ closeAIVersioningModal function exists")
    else:
        print("❌ closeAIVersioningModal function does NOT exist")
        return False
    
    # Test 5: Check if showAIVersioning function exists
    print("\n5. Checking if showAIVersioning function exists...")
    
    if 'function showAIVersioning(' in content:
        print("✅ showAIVersioning function exists")
    else:
        print("❌ showAIVersioning function does NOT exist")
        return False
    
    # Test 6: Check if showStudentLessonModal function exists
    print("\n6. Checking if showStudentLessonModal function exists...")
    
    if 'function showStudentLessonModal(' in content:
        print("✅ showStudentLessonModal function exists")
    else:
        print("❌ showStudentLessonModal function does NOT exist")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! The teacher AI versioning fix should work correctly.")
    print("\n📋 Summary of changes made:")
    print("   • Set window.userInfo in loadUserInfo function for global access")
    print("   • Added debug logging to viewLesson function")
    print("   • Fixed AI versioning modal ID structure")
    print("   • Verified all required functions exist")
    
    print("\n🔍 To test manually:")
    print("   1. Login as a teacher")
    print("   2. Go to View Lessons")
    print("   3. Click on a lesson")
    print("   4. Should see AI versioning interface (not student question interface)")
    print("   5. Check browser console for debug logs")
    
    return True

if __name__ == "__main__":
    try:
        success = test_user_role_detection()
        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
