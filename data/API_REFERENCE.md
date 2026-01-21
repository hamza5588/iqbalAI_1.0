# IqbalAI 1.0 - API Reference Guide

## Base URL
- **Development**: `http://localhost:5000`
- **Production**: `https://iqbalai.com`

## Authentication

Most endpoints require authentication via session cookies. Include credentials in requests.

---

## Authentication Endpoints

### Register User
```http
POST /auth/register
Content-Type: application/json

{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password",
    "class_standard": "10th",
    "medium": "English"
}
```

**Response:**
```json
{
    "message": "Registration successful. Please check your email for verification.",
    "status": "success"
}
```

---

### Login
```http
POST /auth/login
Content-Type: application/json

{
    "email": "john@example.com",
    "password": "secure_password"
}
```

**Response:**
```json
{
    "message": "Login successful",
    "status": "success",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "role": "student"
    }
}
```

---

### Logout
```http
POST /auth/logout
```

**Response:**
```json
{
    "message": "Logged out successfully",
    "status": "success"
}
```

---

### Forgot Password
```http
POST /auth/forgot-password
Content-Type: application/json

{
    "email": "john@example.com"
}
```

**Response:**
```json
{
    "message": "Password reset email sent",
    "status": "success"
}
```

---

### Reset Password
```http
POST /auth/reset-password
Content-Type: application/json

{
    "token": "reset_token_from_email",
    "password": "new_password"
}
```

---

## Chat Endpoints

### Send Message
```http
POST /api/chat
Content-Type: application/json

{
    "message": "Explain Newton's laws",
    "conversation_id": 123,
    "use_rag": true
}
```

**Response:**
```json
{
    "response": "Newton's laws of motion are three physical laws...",
    "conversation_id": 123,
    "message_id": 456
}
```

---

### Get Conversations
```http
GET /api/conversations
```

**Response:**
```json
{
    "conversations": [
        {
            "id": 123,
            "title": "Physics Discussion",
            "created_at": "2024-01-15T10:30:00",
            "message_count": 15
        }
    ]
}
```

---

### Create Conversation
```http
POST /api/conversations
Content-Type: application/json

{
    "title": "New Discussion"
}
```

**Response:**
```json
{
    "conversation_id": 124,
    "title": "New Discussion",
    "message": "Conversation created successfully"
}
```

---

### Get Conversation Messages
```http
GET /api/conversations/<conversation_id>/messages
```

**Response:**
```json
{
    "messages": [
        {
            "id": 1,
            "role": "user",
            "content": "Hello",
            "created_at": "2024-01-15T10:30:00"
        },
        {
            "id": 2,
            "role": "assistant",
            "content": "Hi! How can I help you?",
            "created_at": "2024-01-15T10:30:05"
        }
    ]
}
```

---

### Delete Conversation
```http
DELETE /api/conversations/<conversation_id>
```

**Response:**
```json
{
    "message": "Conversation deleted successfully",
    "status": "success"
}
```

---

## File Upload Endpoints

### Upload File
```http
POST /api/files/upload
Content-Type: multipart/form-data

file: [binary file data]
conversation_id: 123 (optional)
```

**Response:**
```json
{
    "file_id": 789,
    "filename": "document.pdf",
    "message": "File uploaded successfully",
    "file_type": "application/pdf",
    "file_size": 1024000
}
```

**Supported Formats:**
- PDF (.pdf)
- Word (.docx)
- Text (.txt)
- PowerPoint (.pptx)
- Excel (.xlsx)

**Max File Size:** 100MB

---

### Get Uploaded Files
```http
GET /api/files
```

**Response:**
```json
{
    "files": [
        {
            "id": 789,
            "filename": "document.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
            "uploaded_at": "2024-01-15T10:30:00"
        }
    ]
}
```

---

### Delete File
```http
DELETE /api/files/<file_id>
```

---

## Lesson Endpoints

### Get Lessons
```http
GET /api/lessons
```

**Response:**
```json
{
    "lessons": [
        {
            "id": 1,
            "title": "Introduction to Physics",
            "content": "Lesson content...",
            "teacher_id": 5,
            "teacher_name": "teacher_name",
            "is_public": true,
            "created_at": "2024-01-15T10:30:00"
        }
    ]
}
```

---

### Get Lesson by ID
```http
GET /api/lessons/<lesson_id>
```

---

### Create Lesson (Teacher/Admin only)
```http
POST /api/lessons
Content-Type: application/json

{
    "title": "Lesson Title",
    "content": "Lesson content...",
    "is_public": false
}
```

**Response:**
```json
{
    "lesson_id": 2,
    "message": "Lesson created successfully"
}
```

---

### Update Lesson (Teacher/Admin only)
```http
PUT /api/lessons/<lesson_id>
Content-Type: application/json

{
    "title": "Updated Title",
    "content": "Updated content...",
    "is_public": true
}
```

---

### Delete Lesson (Teacher/Admin only)
```http
DELETE /api/lessons/<lesson_id>
```

---

## RAG (Retrieval Augmented Generation) Endpoints

### Upload Document for RAG
```http
POST /api/rag/upload
Content-Type: multipart/form-data

file: [binary file data]
```

**Response:**
```json
{
    "message": "Document processed and indexed successfully",
    "document_id": "doc_123"
}
```

---

### Search Documents
```http
POST /api/rag/search
Content-Type: application/json

{
    "query": "What is quantum physics?",
    "top_k": 5
}
```

**Response:**
```json
{
    "results": [
        {
            "content": "Relevant document excerpt...",
            "score": 0.95,
            "source": "document.pdf"
        }
    ]
}
```

---

## Subscription Endpoints

### Get Subscription Plans
```http
GET /subscription/api/plans
```

**Response:**
```json
{
    "plans": [
        {
            "tier": "free",
            "name": "Free Plan",
            "price": 0,
            "features": ["Basic chat", "Limited conversations"]
        },
        {
            "tier": "pro",
            "name": "Pro Plan",
            "price": 9.99,
            "features": ["Unlimited chat", "File uploads", "Priority support"]
        },
        {
            "tier": "pro_plus",
            "name": "Pro Plus Plan",
            "price": 19.99,
            "features": ["All Pro features", "Advanced RAG", "Custom prompts"]
        }
    ],
    "current_tier": "free"
}
```

---

### Get Current Subscription
```http
GET /subscription/api/current
```

**Response:**
```json
{
    "tier": "pro",
    "status": "active",
    "stripe_customer_id": "cus_xxx",
    "stripe_subscription_id": "sub_xxx",
    "current_period_end": "2024-02-15T10:30:00"
}
```

---

### Create Checkout Session
```http
POST /subscription/api/create-checkout-session
Content-Type: application/json

{
    "tier": "pro",
    "coupon_code": "DISCOUNT10" (optional)
}
```

**Response:**
```json
{
    "session_id": "cs_test_xxx",
    "url": "https://checkout.stripe.com/pay/cs_test_xxx"
}
```

---

### Stripe Webhook
```http
POST /subscription/api/webhook
Content-Type: application/json
Stripe-Signature: [signature]

{
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "customer": "cus_xxx",
            "subscription": "sub_xxx"
        }
    }
}
```

---

## Admin Endpoints

All admin endpoints require admin role.

### Get Dashboard Stats
```http
GET /admin/api/stats
```

**Response:**
```json
{
    "total_users": 150,
    "total_teachers": 25,
    "total_students": 125,
    "total_conversations": 5000,
    "total_lessons": 100,
    "active_subscriptions": 50
}
```

---

### Get All Users
```http
GET /admin/api/users
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `role`: Filter by role (student, teacher, admin)
- `search`: Search by username or email

**Response:**
```json
{
    "users": [
        {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "role": "student",
            "subscription_tier": "free",
            "created_at": "2024-01-15T10:30:00"
        }
    ],
    "total": 150,
    "page": 1,
    "per_page": 20
}
```

---

### Update User Role
```http
POST /admin/api/users/<user_id>/role
Content-Type: application/json

{
    "role": "teacher"
}
```

---

### Get Global Prompts
```http
GET /admin/api/prompts
```

**Response:**
```json
{
    "prompts": [
        {
            "id": 1,
            "prompt_text": "You are a helpful tutor...",
            "is_global": true,
            "created_at": "2024-01-15T10:30:00"
        }
    ]
}
```

---

### Create/Update Global Prompt
```http
POST /admin/api/prompts
Content-Type: application/json

{
    "prompt_text": "You are a helpful tutor...",
    "is_global": true
}
```

---

### Get Coupons
```http
GET /admin/api/coupons
```

**Response:**
```json
{
    "coupons": [
        {
            "id": 1,
            "code": "DISCOUNT10",
            "discount_type": "percentage",
            "discount_value": 10,
            "max_uses": 100,
            "used_count": 25,
            "expires_at": "2024-12-31T23:59:59",
            "created_at": "2024-01-15T10:30:00"
        }
    ]
}
```

---

### Create Coupon
```http
POST /admin/api/coupons
Content-Type: application/json

{
    "code": "DISCOUNT10",
    "discount_type": "percentage",
    "discount_value": 10,
    "max_uses": 100,
    "expires_at": "2024-12-31T23:59:59"
}
```

**Response:**
```json
{
    "coupon_id": 2,
    "message": "Coupon created successfully"
}
```

---

### Delete Coupon
```http
DELETE /admin/api/coupons/<coupon_id>
```

---

## API Key Management

### Get API Keys
```http
GET /api-key/keys
```

**Response:**
```json
{
    "keys": [
        {
            "provider": "openai",
            "is_set": true,
            "masked_key": "sk-...xxxx"
        },
        {
            "provider": "groq",
            "is_set": false
        }
    ]
}
```

---

### Set API Key
```http
POST /api-key/set
Content-Type: application/json

{
    "provider": "openai",
    "api_key": "sk-xxxxx"
}
```

---

### Delete API Key
```http
DELETE /api-key/delete
Content-Type: application/json

{
    "provider": "openai"
}
```

---

## Survey Endpoints

### Submit Survey
```http
POST /api/survey
Content-Type: application/json

{
    "rating": 5,
    "feedback": "Great experience!",
    "suggestions": "Add more features"
}
```

---

### Get Survey Status
```http
GET /api/survey/status
```

**Response:**
```json
{
    "has_submitted": true,
    "submitted_at": "2024-01-15T10:30:00"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
    "error": "Error message",
    "status": "error",
    "code": 400
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Currently, rate limiting is not implemented but can be added using Flask-Limiter.

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

**Response Format:**
```json
{
    "items": [...],
    "total": 150,
    "page": 1,
    "per_page": 20,
    "pages": 8
}
```

---

## WebSocket Support

Currently, the application uses HTTP polling for real-time updates. WebSocket support can be added for improved real-time communication.

---

## Versioning

Current API version: **v1**

Future versions will be accessible via URL prefix: `/api/v2/`

---

**Last Updated**: January 2025

