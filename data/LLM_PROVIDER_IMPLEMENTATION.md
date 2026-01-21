# LLM Provider Switching Implementation Summary

## Overview
This implementation adds Groq + OpenAI provider switching via Admin Panel, with optional user model selection. The system uses LangChain and extends the existing setup without rewriting the application.

## Architecture

### 1. Database Models
- **UserSettings** (`app/models/database_models.py`): Stores user-specific model preferences
  - `user_id`: Foreign key to users table
  - `selected_model`: User's selected model ID (if allowed)
  
- **SystemSettings** (existing): Extended to store:
  - `active_provider`: "GROQ" or "OPENAI"
  - `groq_api_key`: Encrypted Groq API key
  - `openai_api_key`: Encrypted OpenAI API key
  - `groq_default_model`: Default Groq model ID
  - `openai_default_model`: Default OpenAI model ID
  - `groq_allow_user_model_selection`: Boolean flag
  - `openai_allow_user_model_selection`: Boolean flag

### 2. LLM Factory (`app/utils/llm_factory.py`)
- **`get_chat_model(user_id, **kwargs)`**: Main entry point for creating LLM instances
  - Loads admin settings for active provider
  - Checks user settings if model selection is enabled
  - Returns appropriate LangChain chat model (ChatOpenAI or ChatGroq)
  - Handles API key decryption automatically
  
- **`create_llm(...)`**: Low-level factory (backward compatible)
  - Supports OpenAI, Groq, and vLLM
  - Used as fallback when get_chat_model fails

### 3. Model Configuration (`app/utils/llm_models.py`)
- Defines allowed models per provider:
  - **GROQ**: Qwen models (2.5-72B, 32B, 14B, 7B) + Llama models (3.3-70B, 3.1-70B, 3.1-8B, etc.)
  - **OPENAI**: GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-4, GPT-3.5-turbo
- Provides validation functions: `is_valid_model_for_provider()`, `get_default_model_for_provider()`

### 4. Encryption (`app/utils/encryption.py`)
- Uses Fernet symmetric encryption with PBKDF2 key derivation
- Key derived from `SECRET_KEY` in config
- Functions: `encrypt_api_key()`, `decrypt_api_key()`, `mask_api_key()`

### 5. Admin API Routes (`app/routes/admin_routes.py`)
- **GET `/admin/settings/llm`**: Get all LLM settings (admin only)
  - Returns masked API keys (never plaintext)
  - Includes available models for UI dropdowns
  
- **PUT `/admin/settings/llm`**: Update LLM settings (admin only)
  - Accepts: active_provider, API keys, default models, user selection flags
  - Encrypts API keys before storing
  
- **GET `/admin/settings/user-model`**: Get user's model selection (if allowed)
- **PUT `/admin/settings/user-model`**: Set user's model selection (if allowed)

### 6. RAG Service Updates (`app/utils/rag_service.py`)
- Updated `get_rag_llm()` to accept `user_id` parameter
- Updated `get_cached_llm()` to use `get_chat_model()` with user_id
- Updated `chat_node()` to use new factory with user context
- Maintains backward compatibility with fallback behavior

### 7. Admin UI (`templates/admin/dashboard.html`)
- Comprehensive LLM settings page in Settings section:
  - Active provider selection (OPENAI/GROQ)
  - API key inputs for both providers (password fields, masked display)
  - Default model dropdowns per provider
  - Toggles for allowing user model selection
  - Save button with validation

### 8. User UI (`templates/chat.html`)
- Model selection dropdown in Settings section (shown only if enabled by admin)
- Dynamically populated based on active provider
- Grouped by model family (Qwen/Llama for Groq)
- Auto-loads on page initialization

## Files Changed

1. **Database Models**
   - `app/models/database_models.py`: Added UserSettings model

2. **Utilities**
   - `app/utils/llm_factory.py`: Added get_chat_model() function
   - `app/utils/llm_models.py`: NEW - Model configuration
   - `app/utils/encryption.py`: NEW - API key encryption
   - `app/utils/rag_service.py`: Updated to use new factory
   - `app/utils/db.py`: Added UserSettings to init_db imports

3. **Routes**
   - `app/routes/admin_routes.py`: Added LLM settings endpoints

4. **Templates**
   - `templates/admin/dashboard.html`: Added LLM settings UI
   - `templates/chat.html`: Added user model selection UI

## Testing Checklist

### 1. Admin Panel Configuration
- [ ] Navigate to Admin Dashboard → Settings
- [ ] Select "GROQ" as active provider
- [ ] Enter Groq API key (gsk_...)
- [ ] Select default Groq model (e.g., "llama-3.3-70b-versatile")
- [ ] Enable "Allow users to select their own Groq model"
- [ ] Click "Save All Settings"
- [ ] Verify success message
- [ ] Verify API key status shows "✓ Key is set"

### 2. Provider Switching
- [ ] Switch active provider to "OPENAI"
- [ ] Enter OpenAI API key (sk-...)
- [ ] Select default OpenAI model (e.g., "gpt-4o-mini")
- [ ] Enable "Allow users to select their own OpenAI model"
- [ ] Save settings
- [ ] Verify chat uses OpenAI provider

### 3. User Model Selection (Groq)
- [ ] As admin, set active_provider = "GROQ"
- [ ] Enable "groq_allow_user_model_selection"
- [ ] As regular user, open chat interface
- [ ] Go to Settings
- [ ] Verify model selection dropdown appears
- [ ] Verify Qwen and Llama model groups are shown
- [ ] Select a Qwen model (e.g., "qwen2.5-14b-instruct")
- [ ] Click "Save Model Preference"
- [ ] Send a chat message
- [ ] Verify response uses selected Qwen model
- [ ] Switch to Llama model (e.g., "llama-3.3-70b-versatile")
- [ ] Verify chat uses Llama model

### 4. User Model Selection (OpenAI)
- [ ] As admin, set active_provider = "OPENAI"
- [ ] Enable "openai_allow_user_model_selection"
- [ ] As regular user, open Settings
- [ ] Verify OpenAI models are shown in dropdown
- [ ] Select "gpt-4o"
- [ ] Save and verify chat uses GPT-4o
- [ ] Switch to "gpt-3.5-turbo"
- [ ] Verify chat uses GPT-3.5 Turbo

### 5. Model Selection Disabled
- [ ] As admin, disable user model selection for active provider
- [ ] As user, verify model selection dropdown is hidden
- [ ] Verify chat uses admin's default model

### 6. Error Handling
- [ ] Set active_provider = "GROQ" without API key
- [ ] Verify clear error message when chat is used
- [ ] Set active_provider = "OPENAI" without API key
- [ ] Verify clear error message
- [ ] Try to set invalid model ID via API
- [ ] Verify validation error

### 7. Security
- [ ] Verify API keys are never returned in plaintext
- [ ] Verify API keys are masked in admin UI (shows "sk-****...")
- [ ] Verify encryption/decryption works correctly
- [ ] Verify user can only set models for active provider
- [ ] Verify user model selection validates against allowed list

### 8. Backward Compatibility
- [ ] Verify existing RAG chat still works
- [ ] Verify existing lesson services still work
- [ ] Verify fallback to environment variables works if settings not configured

## Migration Notes

1. **Database**: The `user_settings` table will be created automatically on next app startup via SQLAlchemy's `create_all()`.

2. **Initial Setup**: 
   - Admin must configure at least one provider's API key
   - Admin must set `active_provider` to either "GROQ" or "OPENAI"
   - Default models are set automatically if not configured

3. **Environment Variables**: 
   - System still supports `LLM_PROVIDER`, `OPENAI_API_KEY`, `GROQ_API_KEY` env vars as fallback
   - Admin panel settings take precedence over environment variables

## Security Considerations

- API keys are encrypted using Fernet (symmetric encryption)
- Encryption key derived from `SECRET_KEY` using PBKDF2
- API keys never sent to frontend in plaintext
- Only masked values (first 4 + last 4 chars) shown in admin UI
- User model selection validated server-side against allowed list
- RBAC enforced on all admin endpoints

## Future Enhancements

- Add support for more providers (Anthropic, Cohere, etc.)
- Add model-specific parameter tuning (temperature, max_tokens per model)
- Add usage tracking per provider/model
- Add cost estimation per provider
- Add provider health monitoring




