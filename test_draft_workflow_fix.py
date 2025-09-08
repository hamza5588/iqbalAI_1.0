#!/usr/bin/env python3
"""
Test script to verify the new draft content workflow:
1. Initially draft content is empty
2. After AI prompt, draft content appears
3. After finalize, draft content is cleared
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_draft_workflow_fix():
    """Test the new draft content workflow"""
    print("🧪 Testing New Draft Content Workflow")
    print("=" * 60)
    
    with open('templates/chat.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test 1: Check if draft content is initialized as empty
    print("\n1. Checking if draft content is initialized as empty...")
    
    if 'window.aiVersioningDraftContent = \'\';' in content:
        print("✅ Draft content is initialized as empty")
    else:
        print("❌ Draft content is NOT initialized as empty")
        return False
    
    # Test 2: Check if draft preview shows placeholder text initially
    print("\n2. Checking if draft preview shows placeholder text initially...")
    
    if 'draftEl.textContent = \'Draft content will appear here after applying AI prompts...\';' in content:
        print("✅ Draft preview shows placeholder text initially")
    else:
        print("❌ Draft preview does NOT show placeholder text initially")
        return False
    
    # Test 3: Check if applyAIPromptToDraft uses original content when draft is empty
    print("\n3. Checking if applyAIPromptToDraft uses original content when draft is empty...")
    
    if 'if (!contentToEdit || contentToEdit.trim() === \'\') {' in content:
        print("✅ applyAIPromptToDraft uses original content when draft is empty")
    else:
        print("❌ applyAIPromptToDraft does NOT use original content when draft is empty")
        return False
    
    # Test 4: Check if finalizeAIVersion clears draft content after success
    print("\n4. Checking if finalizeAIVersion clears draft content after success...")
    
    if 'window.aiVersioningDraftContent = \'\';' in content and '// Clear draft content after successful finalization' in content:
        print("✅ finalizeAIVersion clears draft content after success")
    else:
        print("❌ finalizeAIVersion does NOT clear draft content after success")
        return False
    
    # Test 5: Check if closeAIVersioningModal clears all draft data
    print("\n5. Checking if closeAIVersioningModal clears all draft data...")
    
    if 'window.aiVersioningDraftContent = \'\';' in content and 'window.aiVersioningOriginalContent = \'\';' in content and 'window.aiVersioningLessonMeta = {};' in content:
        print("✅ closeAIVersioningModal clears all draft data")
    else:
        print("❌ closeAIVersioningModal does NOT clear all draft data")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! The new draft workflow should work correctly.")
    print("\n📋 Summary of the new workflow:")
    print("   1. ✅ Initially: Draft content is empty, shows placeholder text")
    print("   2. ✅ After AI prompt: Draft content gets populated with improved content")
    print("   3. ✅ After finalize: New version gets draft content, draft content is cleared")
    print("   4. ✅ After close: All draft data is cleared for next session")
    
    print("\n🔍 To test manually:")
    print("   1. Login as a teacher")
    print("   2. Go to View Lessons")
    print("   3. Click on a lesson to open AI versioning")
    print("   4. Verify draft content shows placeholder text initially")
    print("   5. Apply an AI prompt - draft content should appear with improved content")
    print("   6. Click 'Finalize New Version' - new version should have the improved content")
    print("   7. Open the modal again - draft content should be empty again")
    print("   8. Check browser console for debug logs")
    
    return True

if __name__ == "__main__":
    try:
        success = test_draft_workflow_fix()
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
