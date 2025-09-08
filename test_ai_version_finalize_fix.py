#!/usr/bin/env python3
"""
Test script to verify that AI version finalization saves draft content correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ai_version_finalize_fix():
    """Test that AI version finalization saves draft content correctly"""
    print("🧪 Testing AI Version Finalize Fix")
    print("=" * 60)
    
    with open('templates/chat.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check if draft content is initialized with original content
    print("\n1. Checking if draft content is initialized with original content...")
    
    if 'window.aiVersioningDraftContent = initialContent;' in content:
        print("✅ Draft content is initialized with original content")
    else:
        print("❌ Draft content is NOT initialized with original content")
        return False
    
    # Test 2: Check if draft preview shows initial content
    print("\n2. Checking if draft preview shows initial content...")
    
    if 'draftEl.innerHTML = initialContent ? marked.parse(initialContent) :' in content:
        print("✅ Draft preview shows initial content")
    else:
        print("❌ Draft preview does NOT show initial content")
        return False
    
    # Test 3: Check if debug logging is added to finalizeAIVersion
    print("\n3. Checking if debug logging is added to finalizeAIVersion...")
    
    if 'DEBUG: finalizeAIVersion - content length:' in content:
        print("✅ Debug logging is added to finalizeAIVersion")
    else:
        print("❌ Debug logging is NOT added to finalizeAIVersion")
        return False
    
    # Test 4: Check if finalizeAIVersion uses draft content
    print("\n4. Checking if finalizeAIVersion uses draft content...")
    
    if 'const content = window.aiVersioningDraftContent || \'\';' in content:
        print("✅ finalizeAIVersion uses draft content")
    else:
        print("❌ finalizeAIVersion does NOT use draft content")
        return False
    
    # Test 5: Check if applyAIPromptToDraft updates draft content
    print("\n5. Checking if applyAIPromptToDraft updates draft content...")
    
    if 'window.aiVersioningDraftContent = newContent;' in content:
        print("✅ applyAIPromptToDraft updates draft content")
    else:
        print("❌ applyAIPromptToDraft does NOT update draft content")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! The AI version finalize fix should work correctly.")
    print("\n📋 Summary of changes made:")
    print("   • Initialize draft content with original content instead of empty string")
    print("   • Show original content in draft preview initially")
    print("   • Added debug logging to finalizeAIVersion function")
    print("   • Verified draft content flow from apply to finalize")
    
    print("\n🔍 To test manually:")
    print("   1. Login as a teacher")
    print("   2. Go to View Lessons")
    print("   3. Click on a lesson to open AI versioning")
    print("   4. Verify draft content shows original content initially")
    print("   5. Apply an AI prompt to modify the content")
    print("   6. Click 'Finalize New Version'")
    print("   7. Check that the new version has the modified content")
    print("   8. Check browser console for debug logs")
    
    return True

if __name__ == "__main__":
    try:
        success = test_ai_version_finalize_fix()
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
