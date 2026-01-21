# Developer Quick Start Guide - IqbalAI 1.0

This guide will help you get started with development on the IqbalAI project.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+ (or SQLite for local dev)
- Git
- Virtual environment tool (venv)
- Code editor (VS Code recommended)

## Quick Setup (5 minutes)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd iqbalAI_1.0

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in root directory:

```env
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///instance/chatbot.db
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
OPENAI_API_KEY=your-openai-key
LLM_PROVIDER=openai
```

### 3. Initialize Database

```bash
# Database will be auto-created on first run
python run.py
```

### 4. Access Application

- Open browser: `http://localhost:5000`
- Default admin login:
  - Username: `admin`
  - Password: `admin123`

---

## Project Structure Overview

```
app/
├── routes/          # HTTP endpoints
├── models/          # Database models
├── services/        # Business logic
├── utils/           # Helper functions
└── rbac/            # Access control

templates/           # HTML templates
static/              # CSS, JS, images
```

---

## Common Development Tasks

### Adding a New Route

1. **Create route in `app/routes/`:**

```python
from flask import Blueprint, request, jsonify
from app.utils.auth import login_required

bp = Blueprint('my_feature', __name__)

@bp.route('/api/my-feature', methods=['GET'])
@login_required
def my_feature():
    return jsonify({"message": "Hello"})
```

2. **Register in `app/__init__.py`:**

```python
from app.routes.my_feature import bp as my_feature_bp
app.register_blueprint(my_feature_bp, url_prefix='/api')
```

### Adding a New Database Model

1. **Define model in `app/models/database_models.py`:**

```python
class MyModel(db.Model):
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

2. **Import in `app/models/__init__.py`**

3. **Database will auto-create on restart** (for SQLite)

### Adding a New Service

1. **Create service in `app/services/`:**

```python
class MyService:
    @staticmethod
    def do_something():
        # Business logic here
        return result
```

2. **Use in routes:**

```python
from app.services.my_service import MyService

@bp.route('/api/endpoint')
def endpoint():
    result = MyService.do_something()
    return jsonify(result)
```

### Adding RBAC Protection

```python
from app.rbac.decorators import role_required, admin_only
from app.rbac.roles import Role

# Admin only
@bp.route('/admin/endpoint')
@admin_only
def admin_endpoint():
    pass

# Multiple roles
@bp.route('/endpoint')
@role_required([Role.TEACHER, Role.ADMIN])
def teacher_endpoint():
    pass
```

---

## Development Workflow

### Running the Application

**Development mode:**
```bash
python run.py
```

**With auto-reload:**
```bash
flask run --reload
```

**Production mode (Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

### Database Operations

**Access database shell:**
```bash
# SQLite
sqlite3 instance/chatbot.db

# PostgreSQL
psql -U username -d database_name
```

**Common queries:**
```sql
-- View all users
SELECT * FROM users;

-- View conversations
SELECT * FROM conversations;

-- View messages
SELECT * FROM messages LIMIT 10;
```

### Logging

Logs are written to `logs/app.log`:

```bash
# View logs
tail -f logs/app.log

# Search for errors
grep ERROR logs/app.log
```

---

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for functions/classes
- Maximum line length: 100 characters

### Example Function

```python
def process_user_data(user_id: int, data: dict) -> dict:
    """
    Process user data and return result.
    
    Args:
        user_id: User identifier
        data: User data dictionary
        
    Returns:
        Processed data dictionary
        
    Raises:
        ValueError: If user_id is invalid
    """
    if not user_id or user_id < 1:
        raise ValueError("Invalid user_id")
    
    # Process data
    result = {}
    return result
```

### Import Organization

```python
# Standard library
import os
from datetime import datetime

# Third-party
from flask import Flask, request
from sqlalchemy import Column

# Local imports
from app.models import User
from app.services import ChatService
```

---

## Debugging Tips

### Enable Debug Mode

In `run.py`:
```python
if __name__ == '__main__':
    app.run(debug=True)
```

### Use Flask Debug Toolbar

```bash
pip install flask-debugtoolbar
```

### Print Debugging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

### Database Debugging

Enable SQL query logging in `config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'echo': True  # Log all SQL queries
}
```

---

## Common Issues & Solutions

### Issue: Module not found

**Solution:**
```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Database connection error

**Solution:**
- Check `.env` file has correct `DATABASE_URL`
- Verify database server is running
- Check credentials

### Issue: Import errors

**Solution:**
- Ensure you're in project root directory
- Check `__init__.py` files exist in packages
- Verify Python path includes project root

### Issue: Port already in use

**Solution:**
```bash
# Find process using port 5000
# Windows:
netstat -ano | findstr :5000
# Linux/Mac:
lsof -i :5000

# Kill process or use different port
flask run --port 5001
```

---

## Testing

### Writing Tests

Create test file in `tests/`:

```python
import pytest
from app import create_app
from app.utils.db import get_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_login(client):
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'password'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
```

### Running Tests

```bash
# All tests
pytest

# Specific test
pytest tests/test_auth.py::test_login

# With verbose output
pytest -v

# Stop on first failure
pytest -x
```

---

## Git Workflow

### Branch Naming

- `feature/feature-name`: New features
- `bugfix/bug-name`: Bug fixes
- `hotfix/issue-name`: Urgent fixes
- `refactor/component-name`: Code refactoring

### Commit Messages

```
feat: Add user profile page
fix: Resolve login session issue
docs: Update API documentation
refactor: Simplify chat service
test: Add tests for auth routes
```

### Pull Request Process

1. Create feature branch
2. Make changes and commit
3. Push to remote
4. Create pull request
5. Code review
6. Merge after approval

---

## Useful Commands

### Database

```bash
# Reset database (SQLite)
rm instance/chatbot.db
python run.py  # Recreates database

# Backup database
cp instance/chatbot.db instance/chatbot.db.backup
```

### Dependencies

```bash
# Update requirements.txt
pip freeze > requirements.txt

# Install new package
pip install package-name
pip freeze > requirements.txt
```

### Environment

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check virtual environment
which python  # Linux/Mac
where python  # Windows
```

---

## IDE Setup

### VS Code

**Recommended extensions:**
- Python
- Pylance
- Flask Snippets
- SQLite Viewer

**Settings (`.vscode/settings.json`):**
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true
}
```

### PyCharm

1. Open project
2. Configure Python interpreter (select venv)
3. Enable Flask support
4. Configure database connection

---

## Next Steps

1. Read `PROJECT_DOCUMENTATION.md` for detailed information
2. Review `API_REFERENCE.md` for API endpoints
3. Explore existing code in `app/routes/` and `app/services/`
4. Check `app/rbac/README.md` for access control
5. Review test files for examples

---

## Getting Help

- Check documentation files
- Review existing code examples
- Check application logs
- Ask team members
- Create issue in repository

---

**Happy Coding! 🚀**



