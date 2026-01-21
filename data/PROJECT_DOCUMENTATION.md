# IqbalAI 1.0 - Complete Project Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Technology Stack](#technology-stack)
6. [Setup and Installation](#setup-and-installation)
7. [Configuration](#configuration)
8. [Database Schema](#database-schema)
9. [API Documentation](#api-documentation)
10. [Authentication & Authorization](#authentication--authorization)
11. [Security Features](#security-features)
12. [Deployment](#deployment)
13. [Development Guidelines](#development-guidelines)
14. [Testing](#testing)
15. [Troubleshooting](#troubleshooting)
16. [Contributing](#contributing)

---

## Project Overview

**IqbalAI 1.0** is an AI-powered educational platform designed to provide intelligent tutoring and learning assistance. The application leverages advanced language models to deliver personalized educational experiences through conversational interfaces, document processing, and interactive lesson management.

### Key Objectives
- Provide AI-powered tutoring with personalized learning experiences
- Support multiple learning formats (text, voice, documents)
- Enable teachers to create and manage educational content
- Offer subscription-based access with tiered features
- Maintain secure, scalable, and maintainable architecture

### Target Users
- **Students**: Access lessons, chat with AI tutor, upload documents for analysis
- **Teachers**: Create lessons, upload educational materials, manage content
- **Administrators**: Manage users, system settings, global prompts, coupons

---

## Architecture

### System Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │
         │ HTTP/HTTPS
         │
┌────────▼────────┐
│   Flask App     │
│  (Application)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│  DB   │ │  LLM  │
│(PostgreSQL)│ │Providers│
└───────┘ └───────┘
```

### Application Architecture

The application follows a **Model-View-Controller (MVC)** pattern with clear separation of concerns:

- **Models**: Data models and database interactions (`app/models/`)
- **Views**: HTML templates (`templates/`)
- **Controllers**: Route handlers (`app/routes/`)
- **Services**: Business logic layer (`app/services/`)
- **Utils**: Utility functions and helpers (`app/utils/`)

### Key Components

1. **Flask Application** (`app/__init__.py`)
   - Application factory pattern
   - Blueprint registration
   - CORS configuration
   - Database initialization

2. **Route Handlers** (`app/routes/`)
   - Authentication routes
   - Chat routes
   - Admin routes
   - API endpoints
   - File upload routes
   - Subscription routes

3. **Services Layer** (`app/services/`)
   - Chat service
   - Lesson service
   - RAG (Retrieval Augmented Generation) service
   - Prompt service

4. **Database Layer** (`app/models/`)
   - SQLAlchemy models
   - Database utilities
   - Connection management

5. **RBAC System** (`app/rbac/`)
   - Role-based access control
   - Permission management
   - Template helpers

---

## Features

### Core Features

#### 1. **AI-Powered Chat Interface**
- Real-time conversational AI tutoring
- Multi-turn conversations with context retention
- Support for text and voice input/output
- Conversation history management
- File upload and analysis integration

#### 2. **User Authentication & Management**
- User registration with email verification
- Secure login/logout
- Password reset functionality
- Session management
- Role-based access (Student, Teacher, Admin)

#### 3. **Document Processing**
- Upload and process multiple file formats:
  - PDF documents
  - Word documents (DOCX)
  - Text files
  - PowerPoint presentations (PPTX)
  - Excel spreadsheets
- Document analysis and RAG integration
- Vector store for semantic search

#### 4. **Lesson Management**
- Teachers can create, edit, and delete lessons
- Students can access assigned lessons
- Lesson content with rich text support
- Integration with chat interface

#### 5. **Subscription Management**
- Three-tier subscription system:
  - **Free**: Basic features
  - **Pro**: Enhanced features
  - **Pro Plus**: Premium features
- Stripe integration for payments
- Coupon code support
- Subscription status tracking

#### 6. **Admin Dashboard**
- User management
- Global prompt management
- Coupon creation and management
- Lesson oversight
- Document management
- System statistics and analytics

#### 7. **RAG (Retrieval Augmented Generation)**
- Document embedding and vectorization
- Semantic search capabilities
- Context-aware responses
- Multi-document support

#### 8. **Multi-LLM Provider Support**
- **OpenAI**: GPT models
- **Groq**: Fast inference models
- **vLLM**: Self-hosted models
- Configurable provider switching

---

## Project Structure

```
iqbalAI_1.0/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration settings
│   │
│   ├── routes/                  # Route handlers (Controllers)
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication routes
│   │   ├── chat.py             # Chat interface routes
│   │   ├── admin_routes.py     # Admin dashboard routes
│   │   ├── api_key.py          # API key management
│   │   ├── files.py            # File upload routes
│   │   ├── chatbot_routes.py   # Chatbot API routes
│   │   ├── lesson_routes.py    # Lesson management routes
│   │   ├── rag_routes.py       # RAG API routes
│   │   ├── subscription.py     # Subscription management
│   │   └── survey.py           # Survey routes
│   │
│   ├── models/                  # Data models
│   │   ├── __init__.py
│   │   ├── database_models.py  # SQLAlchemy models
│   │   ├── conversation.py     # Conversation models
│   │   ├── message.py          # Message models
│   │   └── models.py           # Additional models
│   │
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── chat_service.py     # Chat business logic
│   │   ├── chatbot_service.py  # Chatbot service
│   │   ├── lesson_service.py   # Lesson management
│   │   ├── prompt_service.py   # Prompt management
│   │   └── lesson/             # Lesson-specific services
│   │       ├── base_service.py
│   │       ├── models.py
│   │       ├── rag_service.py
│   │       ├── student_service.py
│   │       └── teacher_service.py
│   │
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   ├── db.py               # Database utilities
│   │   ├── auth.py             # Authentication utilities
│   │   ├── decorators.py       # Custom decorators
│   │   ├── encryption.py       # Encryption utilities
│   │   ├── llm_factory.py     # LLM provider factory
│   │   ├── llm_models.py       # LLM model definitions
│   │   ├── rag_service.py      # RAG utilities
│   │   ├── logger.py           # Logging configuration
│   │   ├── constants.py        # Application constants
│   │   └── admin_init.py       # Admin initialization
│   │
│   ├── rbac/                    # Role-Based Access Control
│   │   ├── __init__.py
│   │   ├── roles.py            # Role definitions
│   │   ├── permissions.py      # Permission system
│   │   ├── decorators.py       # RBAC decorators
│   │   ├── utils.py            # RBAC utilities
│   │   └── template_helpers.py # Template helpers
│   │
│   └── static/                  # Static files (CSS, JS, images)
│       ├── css/
│       ├── js/
│       └── images/
│
├── templates/                    # HTML templates
│   ├── admin/                   # Admin templates
│   │   └── dashboard.html      # Admin dashboard
│   ├── chat.html               # Main chat interface
│   ├── chatbot.html            # Chatbot interface
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── settings.html           # Settings/subscription page
│   ├── forgot_password.html    # Password reset request
│   ├── reset_password.html     # Password reset form
│   └── email_sent.html         # Email confirmation
│
├── instance/                    # Instance-specific files
│   └── chatbot.db              # SQLite database (if used)
│
├── uploaded_files/              # User uploaded files
├── vector_stores/               # Vector store files
│
├── logs/                        # Application logs
├── docs/                        # Documentation
│
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose config
├── nginx.conf                   # Nginx configuration
├── .env                         # Environment variables (not in repo)
├── .gitignore                   # Git ignore rules
└── README.md                    # Project readme
```

---

## Technology Stack

### Backend
- **Flask 3.x**: Web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL/SQLite**: Database systems
- **Flask-Mail**: Email functionality
- **Flask-CORS**: Cross-origin resource sharing

### AI/ML
- **LangChain**: LLM framework
- **LangChain-OpenAI**: OpenAI integration
- **LangChain-Groq**: Groq integration
- **FAISS**: Vector similarity search
- **Sentence Transformers**: Text embeddings

### Frontend
- **HTML5/CSS3**: Markup and styling
- **JavaScript**: Client-side interactivity
- **Tailwind CSS**: Utility-first CSS framework
- **Font Awesome**: Icons

### Payment Processing
- **Stripe**: Payment gateway integration

### File Processing
- **PyPDF2/PyMuPDF**: PDF processing
- **python-docx**: Word document processing
- **python-pptx**: PowerPoint processing
- **pandas**: Data processing

### Other Libraries
- **python-dotenv**: Environment variable management
- **cryptography**: Encryption utilities
- **gTTS**: Text-to-speech
- **langdetect**: Language detection

---

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ (or SQLite for development)
- pip (Python package manager)
- Git (for version control)

### Installation Steps

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd iqbalAI_1.0
```

#### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
SERVER_URL=http://localhost:5000

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
# OR for SQLite:
# DATABASE_URL=sqlite:///instance/chatbot.db

# Email Configuration
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password

# LLM Provider Configuration
LLM_PROVIDER=openai  # Options: openai, groq, vllm

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# Groq Configuration
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile

# vLLM Configuration
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-webhook-secret
STRIPE_PRO_PRODUCT_ID=your-pro-product-id
STRIPE_PRO_PLUS_PRODUCT_ID=your-pro-plus-product-id


#### 5. Database Setup

**For PostgreSQL:**
```bash
# Create database
createdb chatbot_db

# The application will create tables automatically on first run
```

**For SQLite:**
```bash
# SQLite database will be created automatically
mkdir -p instance
```

#### 6. Initialize Database

The database is automatically initialized when the application starts. A default admin account is created:
- **Username**: admin
- **Password**: admin123 (change immediately in production!)

#### 7. Run the Application

**Development:**
```bash
python run.py
```

**Production (with Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

The application will be available at `http://localhost:5000`

---

## Configuration

### Application Configuration (`app/config.py`)

The configuration class contains all application settings:

#### Database Configuration
- `DATABASE_URL`: Database connection string
- `SQLALCHEMY_DATABASE_URI`: SQLAlchemy database URI
- `SQLALCHEMY_TRACK_MODIFICATIONS`: Disable modification tracking

#### Email Configuration
- `MAIL_SERVER`: SMTP server address
- `MAIL_PORT`: SMTP port (465 for SSL, 587 for TLS)
- `MAIL_USE_TLS`: Enable TLS
- `MAIL_USE_SSL`: Enable SSL
- `MAIL_USERNAME`: Email username
- `MAIL_PASSWORD`: Email password
- `MAIL_DEFAULT_SENDER`: Default sender email

#### LLM Provider Configuration
- `LLM_PROVIDER`: Primary LLM provider ('openai', 'groq', 'vllm')
- Provider-specific settings for each LLM service

#### Stripe Configuration
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Webhook secret for verification
- Product IDs for subscription tiers

#### Security Configuration
- `SECRET_KEY`: Flask secret key for sessions
- `SESSION_COOKIE_SECURE`: Secure cookies (HTTPS only)
- `SESSION_COOKIE_HTTPONLY`: HTTP-only cookies
- `SESSION_COOKIE_SAMESITE`: SameSite cookie policy

### Environment Variables

All sensitive configuration should be stored in `.env` file and loaded using `python-dotenv`.

---

## Database Schema

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'student',  -- 'student', 'teacher', 'admin'
    subscription_tier VARCHAR(20) DEFAULT 'free',  -- 'free', 'pro', 'pro_plus'
    subscription_status VARCHAR(20),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Conversations Table
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Messages Table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

#### Lessons Table
```sql
CREATE TABLE lessons (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);
```

#### Coupons Table
```sql
CREATE TABLE coupons (
    id INTEGER PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_type VARCHAR(20) NOT NULL,  -- 'percentage', 'fixed'
    discount_value DECIMAL(10,2) NOT NULL,
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Coupon Redemptions Table
```sql
CREATE TABLE coupon_redemptions (
    id INTEGER PRIMARY KEY,
    coupon_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Prompts Table
```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    prompt_text TEXT NOT NULL,
    is_global BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Uploaded Files Table
```sql
CREATE TABLE uploaded_files (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    conversation_id INTEGER,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

---

## API Documentation

### Authentication Endpoints

#### POST `/auth/register`
Register a new user.

**Request Body:**
```json
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

#### POST `/auth/login`
User login.

**Request Body:**
```json
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

#### POST `/auth/logout`
Logout current user.

**Response:**
```json
{
    "message": "Logged out successfully",
    "status": "success"
}
```

### Chat Endpoints

#### GET `/`
Render main chat interface (requires authentication).

#### POST `/api/chat`
Send a message to the AI tutor.

**Request Body:**
```json
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

#### GET `/api/conversations`
Get user's conversations.

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

#### POST `/api/conversations`
Create a new conversation.

**Request Body:**
```json
{
    "title": "New Discussion"
}
```

#### DELETE `/api/conversations/<id>`
Delete a conversation.

### File Upload Endpoints

#### POST `/api/files/upload`
Upload a file for analysis.

**Request:** Multipart form data
- `file`: File to upload
- `conversation_id`: (Optional) Conversation ID

**Response:**
```json
{
    "file_id": 789,
    "filename": "document.pdf",
    "message": "File uploaded successfully"
}
```

### Lesson Endpoints

#### GET `/api/lessons`
Get available lessons (role-based).

**Response:**
```json
{
    "lessons": [
        {
            "id": 1,
            "title": "Introduction to Physics",
            "content": "Lesson content...",
            "teacher": "teacher_name",
            "created_at": "2024-01-15T10:30:00"
        }
    ]
}
```

#### POST `/api/lessons` (Teacher/Admin only)
Create a new lesson.

**Request Body:**
```json
{
    "title": "Lesson Title",
    "content": "Lesson content...",
    "is_public": false
}
```

### Subscription Endpoints

#### GET `/subscription/settings`
Get subscription settings page.

#### GET `/subscription/api/plans`
Get available subscription plans.

**Response:**
```json
{
    "plans": [
        {
            "tier": "pro",
            "name": "Pro Plan",
            "price": 9.99,
            "features": ["Feature 1", "Feature 2"]
        }
    ]
}
```

#### POST `/subscription/api/create-checkout-session`
Create Stripe checkout session.

**Request Body:**
```json
{
    "tier": "pro",
    "coupon_code": "DISCOUNT10"
}
```

### Admin Endpoints

#### GET `/admin/dashboard`
Admin dashboard (Admin only).

#### GET `/admin/api/users`
Get all users (Admin only).

#### POST `/admin/api/users/<id>/role`
Update user role (Admin only).

**Request Body:**
```json
{
    "role": "teacher"
}
```

#### GET `/admin/api/prompts`
Get global prompts (Admin only).

#### POST `/admin/api/prompts`
Create/update global prompt (Admin only).

#### POST `/admin/api/coupons`
Create a coupon (Admin only).

**Request Body:**
```json
{
    "code": "DISCOUNT10",
    "discount_type": "percentage",
    "discount_value": 10,
    "max_uses": 100,
    "expires_at": "2024-12-31T23:59:59"
}
```

---

## Authentication & Authorization

### Authentication Flow

1. User registers with email and password
2. Email verification sent to user
3. User verifies email and logs in
4. Session created with user ID and role
5. Session stored in secure HTTP-only cookie

### Authorization (RBAC)

The application uses a Role-Based Access Control (RBAC) system with three roles:

#### Student Role
- View public lessons
- Create and manage own conversations
- Upload files
- Access chat interface
- View own profile

#### Teacher Role
- All student permissions
- Create, edit, delete own lessons
- Upload PDF documents
- Manage own documents
- View own lesson analytics

#### Admin Role
- All teacher permissions
- View all users
- Manage user roles
- View all lessons
- Edit/delete any lesson
- Manage global prompts
- Create and manage coupons
- View system statistics
- Access admin dashboard

### Using RBAC in Code

#### In Routes
```python
from app.rbac.decorators import role_required, admin_only, teacher_required
from app.rbac.roles import Role

@bp.route('/admin/users')
@admin_only
def view_users():
    # Only admins can access
    pass

@bp.route('/lessons/create')
@teacher_required
def create_lesson():
    # Teachers and admins can access
    pass

@bp.route('/lessons/<id>')
@role_required([Role.STUDENT, Role.TEACHER, Role.ADMIN])
def view_lesson(id):
    # All roles can access
    pass
```

#### In Templates
```html
{% if is_admin() %}
    <a href="/admin/dashboard">Admin Dashboard</a>
{% endif %}

{% if can_create_lesson() %}
    <button>Create Lesson</button>
{% endif %}
```

---

## Security Features

### 1. Password Security
- Passwords are hashed using secure hashing algorithms
- Never stored in plain text
- Password reset requires email verification

### 2. Session Management
- Secure session cookies
- HTTP-only cookies (prevents XSS)
- SameSite cookie policy
- Session timeout (24 hours)
- Secure cookie flag in production

### 3. CORS Protection
- Configured CORS policies
- Allowed origins specified
- Credentials support enabled

### 4. Input Validation
- All user inputs validated
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (Jinja2 auto-escaping)
- File upload validation

### 5. File Upload Security
- File type validation
- File size limits (100MB)
- Secure file storage
- Path traversal prevention

### 6. API Security
- Authentication required for protected endpoints
- Role-based access control
- Rate limiting (can be added)
- Input sanitization

### 7. Database Security
- Parameterized queries (SQLAlchemy)
- Connection pooling
- Database credentials in environment variables

### 8. Email Security
- Email verification for registration
- Secure password reset flow
- Token-based verification

---

## Deployment

### Docker Deployment

#### 1. Build Docker Image

```bash
docker build -t iqbalai:latest .
```

#### 2. Using Docker Compose

```bash
docker-compose up -d
```

The `docker-compose.yml` includes:
- Flask application container
- PostgreSQL database container
- Nginx reverse proxy

#### 3. Environment Variables

Set environment variables in `.env` file or docker-compose.yml.

### Production Deployment Checklist

- [ ] Set `SECRET_KEY` to a strong random value
- [ ] Use PostgreSQL in production (not SQLite)
- [ ] Enable HTTPS (set `SESSION_COOKIE_SECURE = True`)
- [ ] Configure proper CORS origins
- [ ] Set up proper logging
- [ ] Configure email settings
- [ ] Set up Stripe webhooks
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerts
- [ ] Review and update all API keys
- [ ] Disable debug mode
- [ ] Set up proper firewall rules
- [ ] Configure Nginx for static files
- [ ] Set up SSL certificates

### Nginx Configuration

Example Nginx configuration for production:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/static;
        expires 30d;
    }
}
```

---

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

### Project Structure Guidelines

- **Routes**: Handle HTTP requests/responses only
- **Services**: Contain business logic
- **Models**: Define data structures
- **Utils**: Reusable utility functions
- **RBAC**: Access control logic

### Adding New Features

1. **Create Route Handler** (`app/routes/`)
   - Define endpoint
   - Add authentication/authorization
   - Call service layer

2. **Create Service** (`app/services/`)
   - Implement business logic
   - Interact with models
   - Handle errors

3. **Update Models** (`app/models/`)
   - Add database models if needed
   - Update schema

4. **Create Templates** (`templates/`)
   - Design UI
   - Integrate with backend

5. **Add Tests**
   - Unit tests for services
   - Integration tests for routes

### Database Migrations

When modifying database schema:

1. Update SQLAlchemy models
2. Create migration script (if using Flask-Migrate)
3. Test migration on development database
4. Apply to production with backup

### Error Handling

- Use try-except blocks appropriately
- Log errors with context
- Return user-friendly error messages
- Don't expose sensitive information

### Logging

Use the logging module for:
- Error tracking
- Debug information
- User activity (privacy-conscious)
- Performance metrics

Example:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("User logged in", extra={"user_id": user_id})
logger.error("Database error", exc_info=True)
```

---

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Test Structure

```
tests/
├── __init__.py
├── test_auth.py
├── test_chat.py
├── test_services.py
└── test_models.py
```

### Writing Tests

```python
import pytest
from app import create_app
from app.utils.db import get_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login(client):
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'password'
    })
    assert response.status_code == 200
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Problem**: Cannot connect to database

**Solutions**:
- Check `DATABASE_URL` in `.env`
- Verify database server is running
- Check network connectivity
- Verify credentials

#### 2. Email Not Sending

**Problem**: Email verification not received

**Solutions**:
- Check email configuration in `config.py`
- Verify SMTP credentials
- Check spam folder
- Test with email debug mode enabled

#### 3. LLM Provider Errors

**Problem**: AI responses not working

**Solutions**:
- Verify API keys are set
- Check provider status
- Review rate limits
- Check network connectivity
- Review logs for specific errors

#### 4. File Upload Issues

**Problem**: Files not uploading

**Solutions**:
- Check file size limits
- Verify file type is allowed
- Check disk space
- Review upload directory permissions

#### 5. Session Issues

**Problem**: User logged out unexpectedly

**Solutions**:
- Check session cookie settings
- Verify `SECRET_KEY` is set
- Check session timeout settings
- Review CORS configuration

### Debug Mode

Enable debug mode for development:

```python
# In run.py
if __name__ == '__main__':
    app.run(debug=True)
```

**Warning**: Never enable debug mode in production!

### Logging

Check application logs:

```bash
# View logs
tail -f logs/app.log

# Check for errors
grep ERROR logs/app.log
```

---

## Contributing

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Update documentation
6. Submit a pull request

### Code Review Process

- All code must be reviewed
- Tests must pass
- Documentation must be updated
- Follow coding standards

---

## Additional Resources

### Documentation Files

- `README.md`: Quick start guide
- `docs/User_Guide.md`: User documentation
- `app/rbac/README.md`: RBAC documentation
- `SUBSCRIPTION_SETUP.md`: Subscription setup guide
- `LLM_PROVIDER_IMPLEMENTATION.md`: LLM provider details
- `MEMORY_MANAGEMENT.md`: Memory management system documentation

### External Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [LangChain Documentation](https://python.langchain.com/)
- [Stripe API Documentation](https://stripe.com/docs/api)

---

## License

[Add license information here]

---

## Contact & Support

For issues, questions, or contributions:
- Create an issue in the repository
- Contact: [Add contact information]

---

**Last Updated**: January 2025
**Version**: 1.0

