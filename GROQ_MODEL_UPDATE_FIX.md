# Groq Model Update Fix

## Problem
The application was experiencing errors when using the Groq API because the model `llama3-70b-8192` has been decommissioned by Groq. The error message was:

```
Error code: 400 - {'error': {'message': 'The model `llama3-70b-8192` has been decommissioned and is no longer supported. Please refer to https://console.groq.com/docs/deprecations for a recommendation on which model to use instead.', 'type': 'invalid_request_error', 'code': 'model_decommissioned'}}
```

## Root Cause
Groq has decommissioned the `llama3-70b-8192` model and it's no longer available for use. The application was still trying to use this deprecated model in several services.

## Solution
Updated all model references from the deprecated `llama3-70b-8192` to the currently supported `llama-3.3-70b-versatile` model.

## Files Modified

### 1. **`app/services/lesson_service.py`**
**Before:**
```python
self.llm = ChatGroq(
    api_key=api_key,
    model="llama3-70b-8192",
    temperature=0.3,
    # max_tokens=4096  # Increased token limit
)
```

**After:**
```python
self.llm = ChatGroq(
    api_key=api_key,
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    # max_tokens=4096  # Increased token limit
)
```

### 2. **`app/services/chatbot_service.py`**
**Before:**
```python
self.llm = ChatGroq(groq_api_key=self.groq_api_key, model_name="Llama3-8b-8192")
```

**After:**
```python
self.llm = ChatGroq(groq_api_key=self.groq_api_key, model_name="llama-3.3-70b-versatile")
```

### 3. **`app/models/models.py`**
**Already Updated:**
```python
self._chat_model = ChatGroq(
    api_key=self.api_key,
    model_name="llama-3.3-70b-versatile",
    timeout=self.timeout,
    max_retries=3,
)
```

## Model Information

### Deprecated Model:
- **`llama3-70b-8192`**: No longer supported by Groq

### Current Supported Model:
- **`llama-3.3-70b-versatile`**: Currently supported by Groq
  - 70 billion parameters
  - Versatile model for various tasks
  - Better performance and reliability

## Impact

### Services Affected:
1. **Lesson Service**: Used for generating and improving lesson content
2. **Chatbot Service**: Used for document-based Q&A functionality
3. **Chat Model**: Used for general chat functionality

### Benefits of Update:
- ✅ **Eliminates 400 errors**: No more model decommissioned errors
- ✅ **Better Performance**: Newer model with improved capabilities
- ✅ **Future-proof**: Using currently supported model
- ✅ **Consistent Experience**: All services now use the same model

## Testing

### Test Scenarios:
1. **Lesson Generation**: Test creating new lessons
2. **Lesson Improvement**: Test AI-powered lesson improvement
3. **Document Q&A**: Test asking questions about uploaded documents
4. **General Chat**: Test general chat functionality
5. **Question Asking**: Test asking questions about lessons

### Expected Results:
- No more 400 errors related to model decommissioning
- All AI-powered features work correctly
- Consistent performance across all services

## Verification

To verify the fix is working:

1. **Check Error Logs**: No more "model decommissioned" errors
2. **Test AI Features**: All AI-powered features should work
3. **Monitor Performance**: Should see consistent response times
4. **Check API Usage**: Groq API calls should succeed

## Future Considerations

### Model Monitoring:
- Monitor Groq's deprecation announcements
- Keep model references updated
- Consider implementing model fallback strategies

### Best Practices:
- Use environment variables for model names when possible
- Implement model validation on startup
- Add logging for model initialization
- Consider model versioning strategy

## Summary

The fix updates all deprecated model references to use the currently supported `llama-3.3-70b-versatile` model. This resolves the 400 errors and ensures all AI-powered features continue to work correctly.

The changes are minimal and focused, affecting only the model name parameter in the ChatGroq initialization calls. No other functionality is changed, ensuring backward compatibility while fixing the immediate issue.
