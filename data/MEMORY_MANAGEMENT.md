# Memory Management in IqbalAI - Short-Term and Long-Term Memory

## Overview

IqbalAI implements a sophisticated two-tier memory system to manage conversation context efficiently:

1. **Short-Term Memory**: Active conversation context (recent messages)
2. **Long-Term Memory**: Persistent storage in database and vector stores

This document explains how the agent handles both types of memory.

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Memory System                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │ Short-Term       │      │ Long-Term         │        │
│  │ Memory           │      │ Memory            │        │
│  ├──────────────────┤      ├──────────────────┤        │
│  │ • Active Context │      │ • Database       │        │
│  │ • Recent Messages│      │ • Vector Store   │        │
│  │ • Token Window   │      │ • Conversations  │        │
│  │ • Summaries      │      │ • Documents      │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Short-Term Memory

### Definition

Short-term memory refers to the **active context window** that is sent to the LLM for each request. This includes recent messages and summaries of older messages.

### Implementation

**Location**: `app/services/chat_service.py`

**Key Constants** (from `app/utils/constants.py`):
```python
MAX_MESSAGE_WINDOW = 20      # Maximum messages in active context
MAX_CONTEXT_TOKENS = 4000    # Maximum tokens in context
SUMMARY_THRESHOLD = 30        # Messages before summarization
```

### How It Works

#### 1. **Sliding Window Approach**

The system maintains a sliding window of the most recent messages:

```python
def _manage_context_window(self, history: List[Dict]) -> Tuple[List[Dict], str]:
    """Manage the context window by implementing a sliding window and summarization."""
    if len(history) <= MAX_MESSAGE_WINDOW:
        return history, ""
        
    # If we have more messages than the window size, summarize older ones
    if len(history) > SUMMARY_THRESHOLD:
        summary = self._summarize_history(history)
        recent_messages = history[-MAX_MESSAGE_WINDOW:]
        return recent_messages, summary
        
    # Otherwise, just keep the most recent messages
    return history[-MAX_MESSAGE_WINDOW:], ""
```

**Behavior**:
- **≤ 20 messages**: All messages included in context
- **21-30 messages**: Only last 20 messages included
- **> 30 messages**: Older messages summarized, last 20 messages included

#### 2. **Message Summarization**

When conversations exceed 30 messages, older messages are summarized:

```python
def _summarize_history(self, history: List[Dict]) -> str:
    """Summarize old messages in the conversation history."""
    # Get the most recent messages
    recent_messages = history[-MAX_MESSAGE_WINDOW:]
    
    # Create a summary of older messages
    older_messages = history[:-MAX_MESSAGE_WINDOW]
    if not older_messages:
        return ""
        
    summary_prompt = "Summarize the following conversation in a concise way, maintaining the context and key points:\n\n"
    for msg in older_messages:
        role = msg.get('role', 'user')
        content = msg.get('message', '')
        summary_prompt += f"{role}: {content}\n"
    
    # Use the chat model to generate a summary
    summary = self.chat_model.generate_response(
        input_text=summary_prompt,
        system_prompt="You are a helpful assistant that summarizes conversations concisely while maintaining context and key points.",
        chat_history=[]
    )
    
    return f"[Previous conversation summary: {summary}]\n\n"
```

**Summary Process**:
1. Older messages (beyond the last 20) are extracted
2. A summary prompt is created
3. The LLM generates a concise summary
4. Summary is prepended to the context as a system message

#### 3. **Context Formatting**

Messages are formatted for the LLM with proper role mapping:

```python
def format_chat_history(self, history: List[Dict]) -> List[Dict]:
    """Format chat history for the LLM with memory management."""
    # Apply memory management
    managed_history, summary = self._manage_context_window(history)
    
    formatted_history = []
    if summary:
        formatted_history.append({
            'role': 'system',
            'content': summary
        })
        
    for msg in managed_history:
        role = 'assistant' if msg.get('role') == 'bot' else msg.get('role', 'user')
        content = msg.get('message', '')
        
        if content and role:
            formatted_history.append({
                'role': role,
                'content': content
            })
            
    return formatted_history
```

**Format**:
- System message: Contains summary of older messages (if any)
- User messages: Role = 'user'
- Assistant messages: Role = 'assistant' (mapped from 'bot')

#### 4. **Token Counting**

The system uses `tiktoken` to count tokens:

```python
def _count_tokens(self, text: str) -> int:
    """Count the number of tokens in a text string."""
    return len(self._tokenizer.encode(text))
```

**Token Limit**: `MAX_CONTEXT_TOKENS = 4000`

---

## Long-Term Memory

### Definition

Long-term memory refers to **persistent storage** of all conversations, messages, and document embeddings in the database and vector stores.

### Components

#### 1. **Database Storage**

**Location**: `app/models/conversation.py`, `app/models/message.py`

**Storage**:
- **Conversations**: All conversation metadata (title, timestamps)
- **Messages**: All messages in all conversations
- **Users**: User information and preferences

**Database Tables**:
```sql
-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP
);
```

**Retrieval**:
```python
def get_chat_history(self, conversation_id: int) -> List[Dict]:
    """Get all messages for a conversation from database."""
    # Retrieves ALL messages, not just recent ones
    # Used as source for short-term memory management
```

#### 2. **Vector Store (RAG)**

**Location**: `app/models/vector_store.py`

**Purpose**: Stores document embeddings for semantic search and retrieval.

**Storage**:
- Document chunks with embeddings
- Metadata (page numbers, file names, etc.)
- User-specific vector stores

**Retrieval**:
```python
def get_document_context(self, message: str) -> str:
    """Get relevant context from uploaded documents."""
    # Searches vector store for relevant document chunks
    # Returns context based on semantic similarity
    relevant_docs = self.vector_store.search_similar(message, k=2)
```

**Features**:
- Semantic search across uploaded documents
- Page-specific retrieval
- Caching for performance (3-minute TTL)

#### 3. **Document Context Cache**

**Location**: `app/services/chat_service.py`

**Purpose**: Temporary cache for document context to improve performance.

```python
self._document_context_cache = {}  # Cache for document contexts
self._cache_ttl = 180  # 3 minutes cache TTL
```

**Cache Management**:
- Cache key: `{user_id}:{message}`
- TTL: 180 seconds (3 minutes)
- Automatic cleanup every 60 seconds

---

## Memory Flow

### Message Processing Flow

```
1. User sends message
   │
   ├─→ Check conversation_id
   │   │
   │   ├─→ New conversation: No history
   │   │
   │   └─→ Existing conversation:
   │       │
   │       └─→ Retrieve ALL messages from database (Long-Term)
   │           │
   │           └─→ Apply memory management (Short-Term)
   │               │
   │               ├─→ If > 30 messages: Summarize older messages
   │               │
   │               └─→ Keep last 20 messages
   │
2. Get document context (if available)
   │
   ├─→ Check cache first
   │
   └─→ Search vector store (Long-Term)
       │
       └─→ Cache result
   │
3. Format context for LLM
   │
   ├─→ System prompt + document context
   ├─→ Summary (if exists)
   └─→ Recent messages (last 20)
   │
4. Generate response
   │
5. Save to database (Long-Term)
   │
   └─→ Both user message and assistant response
```

### Example Scenario

**Conversation with 50 messages:**

1. **Long-Term Memory (Database)**:
   - Stores all 50 messages permanently

2. **Short-Term Memory (Context Window)**:
   - Messages 1-30: Summarized into a concise summary
   - Messages 31-50: Included in full (last 20 messages)
   - Summary prepended as system message
   - Total context: Summary + 20 recent messages

3. **Document Context (Vector Store)**:
   - If user asks about uploaded documents, relevant chunks retrieved
   - Added to system prompt

---

## Memory Management Strategies

### 1. **Sliding Window**

- **Purpose**: Keep context manageable
- **Size**: 20 messages
- **Benefit**: Prevents context overflow, maintains recent context

### 2. **Summarization**

- **Trigger**: When conversation exceeds 30 messages
- **Method**: LLM-generated summary
- **Benefit**: Preserves important context while reducing tokens

### 3. **Token Management**

- **Limit**: 4000 tokens maximum
- **Counting**: Using tiktoken library
- **Benefit**: Stays within LLM context limits

### 4. **Caching**

- **Document Context**: 3-minute cache
- **Purpose**: Reduce vector store queries
- **Benefit**: Faster response times

### 5. **Database Persistence**

- **All Messages**: Stored permanently
- **Conversations**: Stored with metadata
- **Benefit**: Full conversation history available

---

## Configuration

### Memory Constants

Located in `app/utils/constants.py`:

```python
# Short-term memory limits
MAX_MESSAGE_WINDOW = 20      # Maximum messages in active context
MAX_CONTEXT_TOKENS = 4000    # Maximum tokens in context
SUMMARY_THRESHOLD = 30       # Messages before summarization

# Long-term memory limits
MAX_CONVERSATIONS = 4        # Maximum conversations to display
```

### Adjusting Memory Settings

To change memory behavior, modify constants in `app/utils/constants.py`:

```python
# Increase active context window
MAX_MESSAGE_WINDOW = 30  # Keep last 30 messages

# Increase token limit
MAX_CONTEXT_TOKENS = 8000  # Allow more tokens

# Change summarization threshold
SUMMARY_THRESHOLD = 50  # Summarize after 50 messages
```

**Note**: Increasing these values will:
- Use more tokens per request
- Increase API costs
- May exceed LLM context limits
- Slow down response times

---

## Memory Lifecycle

### Short-Term Memory Lifecycle

1. **Creation**: When message is processed
2. **Active**: During LLM request
3. **Expiration**: After response is generated
4. **Refresh**: Updated with each new message

### Long-Term Memory Lifecycle

1. **Storage**: Immediately when message is saved
2. **Retention**: Permanent (until deleted)
3. **Retrieval**: On-demand when conversation is accessed
4. **Cleanup**: Manual deletion or automatic cleanup (if implemented)

---

## Performance Considerations

### Short-Term Memory

- **Token Counting**: Uses efficient tiktoken library
- **Summarization**: Only when needed (>30 messages)
- **Caching**: Document context cached for 3 minutes

### Long-Term Memory

- **Database Queries**: Optimized with indexes
- **Vector Search**: Efficient FAISS-based search
- **Cache**: Document context cached to reduce queries

---

## Best Practices

### For Developers

1. **Monitor Token Usage**: Track context size to avoid exceeding limits
2. **Optimize Summaries**: Ensure summaries are concise but informative
3. **Cache Management**: Balance cache TTL with memory usage
4. **Database Indexing**: Ensure proper indexes on conversation_id, user_id

### For Users

1. **Conversation Length**: Very long conversations will be summarized
2. **Document Upload**: Uploaded documents persist across conversations
3. **Conversation History**: All conversations are saved permanently
4. **Context Window**: Recent messages (last 20) are always available

---

## Troubleshooting

### Issue: Context Lost

**Problem**: Agent doesn't remember earlier messages

**Solution**: 
- Check if conversation exceeds 30 messages (summarization may lose details)
- Verify database is storing messages correctly
- Review summary quality

### Issue: Token Limit Exceeded

**Problem**: Requests fail due to token limits

**Solution**:
- Reduce `MAX_MESSAGE_WINDOW`
- Reduce `MAX_CONTEXT_TOKENS`
- Improve summarization quality
- Reduce document context size

### Issue: Slow Response Times

**Problem**: Responses take too long

**Solution**:
- Check cache hit rate for document context
- Optimize database queries
- Reduce vector store search results (k parameter)
- Consider increasing cache TTL

---

## Future Enhancements

Potential improvements to memory management:

1. **Hierarchical Summarization**: Multi-level summaries for very long conversations
2. **Selective Memory**: Remember important facts separately
3. **Memory Compression**: More efficient summarization techniques
4. **Context Prioritization**: Weight important messages higher
5. **Cross-Conversation Memory**: Remember user preferences across conversations

---

## Summary

IqbalAI uses a **two-tier memory system**:

- **Short-Term**: Active context window (20 messages) with summarization for older messages
- **Long-Term**: Database storage (all messages) and vector stores (document embeddings)

This approach balances:
- **Context retention**: Important information preserved
- **Performance**: Efficient token usage and response times
- **Scalability**: Handles long conversations gracefully

The system automatically manages memory, ensuring optimal performance while maintaining conversation context.

---

**Last Updated**: January 2025
**Version**: 1.0


