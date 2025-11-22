# Database Migration to Database-Agnostic Architecture

## Overview

The application has been migrated from SQLite-only to a database-agnostic architecture that supports:
- **SQLite** (default, for development)
- **MySQL** (for production)
- **PostgreSQL** (for production)

## Key Changes

### 1. Configuration (`app/config.py`)
- Added `DATABASE_URL` environment variable support
- Database URL formats:
  - SQLite: `sqlite:///instance/chatbot.db` or `sqlite:////absolute/path/to/chatbot.db`
  - MySQL: `mysql+pymysql://user:password@localhost/dbname`
  - PostgreSQL: `postgresql://user:password@localhost/dbname` or `postgresql+psycopg2://user:password@localhost/dbname`
- Falls back to SQLite if `DATABASE_URL` is not set

### 2. Database Models (`app/models/database_models.py`)
- Created SQLAlchemy ORM models for all database tables:
  - User, Lesson, Conversation, ChatHistory
  - SurveyResponse, UserPrompt, UserDocument
  - UserTokenUsage, TokenResetHistory
  - LessonFAQ, LessonChatHistory

### 3. Database Utilities (`app/utils/db.py`)
- Replaced raw SQLite connections with SQLAlchemy session management
- `get_db()` now returns SQLAlchemy session (works the same way)
- Added SQLite-specific optimizations (WAL mode, foreign keys, etc.)
- Updated token usage functions to use SQLAlchemy ORM

### 4. Model Classes (`app/models/models.py`)
- Converted all model classes to use SQLAlchemy ORM:
  - UserModel - uses SQLAlchemy queries
  - LessonModel - uses SQLAlchemy ORM
  - ConversationModel - uses SQLAlchemy ORM
  - SurveyModel - uses SQLAlchemy ORM
  - LessonFAQ - uses SQLAlchemy ORM (no more direct SQLite connections)
  - LessonChatHistory - uses SQLAlchemy ORM (no more direct SQLite connections)

### 5. Requirements (`requirements.txt`)
- Added `psycopg2-binary` for PostgreSQL support
- Added `PyMySQL` for MySQL support
- SQLAlchemy was already included

## Usage

### Environment Variable Setup

Set the `DATABASE_URL` environment variable in your `.env` file:

**For SQLite (default):**
```env
DATABASE_URL=sqlite:///instance/chatbot.db
```

**For MySQL:**
```env
DATABASE_URL=mysql+pymysql://username:password@localhost/database_name
```

**For PostgreSQL:**
```env
DATABASE_URL=postgresql://username:password@localhost/database_name
```

Or:
```env
DATABASE_URL=postgresql+psycopg2://username:password@localhost/database_name
```

### Running the Application

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your `DATABASE_URL` in `.env` file (optional, defaults to SQLite)

3. Run the application - tables will be created automatically on first run

## Migration Notes

- All existing SQLite databases will continue to work
- When switching to MySQL/PostgreSQL, you may need to:
  - Create the database manually
  - Adjust data types if needed (SQLAlchemy handles most conversions)
  - Export and import data if migrating existing data

## Database Drivers

- **SQLite**: Built-in, no additional driver needed
- **PostgreSQL**: `psycopg2-binary` (already added to requirements.txt)
- **MySQL**: `PyMySQL` (already added to requirements.txt)

## Benefits

1. **Flexibility**: Easy to switch between databases via environment variable
2. **Production Ready**: Use MySQL or PostgreSQL in production
3. **Development Friendly**: Continue using SQLite for local development
4. **Type Safety**: SQLAlchemy ORM provides better type checking
5. **Maintainability**: Database-agnostic queries are easier to maintain

## Testing

To test with different databases:
1. Set `DATABASE_URL` environment variable
2. Restart the application
3. The app will automatically connect to the specified database
4. Tables will be created if they don't exist

## Notes

- Some complex queries may still use raw SQL with SQLAlchemy's `text()` function, which is database-agnostic
- Foreign key constraints are enabled for all databases
- Indexes are automatically created as defined in the models

