# Role-Based Access Control System

This document describes the implementation of role-based access control (RBAC) in the IqbalAI application, which provides different interfaces and capabilities for teachers and students.

## Overview

The system implements two distinct roles:
- **Teacher**: Can create, edit, and manage lessons
- **Student**: Can browse, view, and download lessons created by teachers

## Database Schema Changes

### Users Table
Added a `role` column to the users table:
```sql
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student' 
CHECK(role IN ('student', 'teacher'));
```

### Lessons Table
New table to store lessons created by teachers:
```sql
CREATE TABLE lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    learning_objectives TEXT,
    focus_area TEXT,
    grade_level TEXT,
    content TEXT NOT NULL,
    file_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## Models

### UserModel
Enhanced with role-based methods:
- `get_role()`: Get user's role
- `is_teacher()`: Check if user is a teacher
- `is_student()`: Check if user is a student

### LessonModel
New model for lesson management:
- `create_lesson()`: Create a new lesson
- `get_lessons_by_teacher()`: Get lessons by specific teacher
- `get_public_lessons()`: Get all public lessons
- `search_lessons()`: Search lessons by content
- `update_lesson()`: Update lesson details
- `delete_lesson()`: Delete a lesson

## Authentication & Authorization

### Decorators
New role-based decorators in `app/utils/decorators.py`:
- `@teacher_required`: Requires teacher role
- `@student_required`: Requires student role
- `@role_required(role)`: Requires specific role

### Session Management
User role is stored in session during login:
```python
session['role'] = user.get('role', 'student')
```

## API Endpoints

### Teacher Endpoints (Teacher Only)
- `POST /api/lessons/create_lesson`: Create a new lesson
- `GET /api/lessons/my_lessons`: Get teacher's own lessons
- `PUT /api/lessons/lesson/<id>`: Update a lesson
- `DELETE /api/lessons/lesson/<id>`: Delete a lesson

### Student Endpoints (Student Only)
- `GET /api/lessons/browse_lessons`: Browse available lessons
- `GET /api/lessons/search_lessons`: Search lessons
- `GET /api/lessons/lesson/<id>`: View specific lesson
- `GET /api/lessons/download_lesson/<id>`: Download lesson

### Common Endpoints
- `GET /user_info`: Get current user information
- `GET /api/lessons/lesson/<id>`: View lesson (if public or owner)

## Frontend Implementation

### Role-Based UI
The frontend dynamically shows/hides elements based on user role:

**For Teachers:**
- "Generate Lessons" button visible
- "Browse Lessons" button hidden
- Access to lesson creation interface

**For Students:**
- "Generate Lessons" button hidden
- "Browse Lessons" button visible
- Access to lesson browsing interface

### JavaScript Functions

#### Role Detection
```javascript
async function loadUserInfo() {
    const response = await fetch('/user_info');
    const data = await response.json();
    userRole = data.user.role;
    setupRoleBasedUI();
}
```

#### Lesson Browsing (Students)
- `loadAvailableLessons()`: Load lessons with filters
- `searchLessons()`: Search lessons by keyword
- `viewLesson()`: View lesson details in modal
- `downloadLessonFile()`: Download lesson as DOCX

#### Lesson Creation (Teachers)
- Enhanced `generateLesson()` function
- Uses new `/api/lessons/create_lesson` endpoint
- Stores lessons in database

## Registration Process

### Role Selection
Users must select their role during registration:
```html
<select name="role" required>
    <option value="">Select your role...</option>
    <option value="student">Student - I want to view lessons created by teachers</option>
    <option value="teacher">Teacher - I want to create and manage lessons</option>
</select>
```

## Security Features

### Access Control
- Role-based route protection
- Teacher can only access their own lessons for editing/deletion
- Students can only view public lessons
- API endpoints validate user roles

### Data Validation
- Required fields validation
- File type validation
- Role validation during registration

## Usage Examples

### Teacher Workflow
1. Register as a teacher
2. Login to the system
3. Click "Generate Lessons" in sidebar
4. Upload educational document
5. Configure lesson details
6. Generate and save lesson
7. View/manage created lessons

### Student Workflow
1. Register as a student
2. Login to the system
3. Click "Browse Lessons" in sidebar
4. Search/filter available lessons
5. View lesson details
6. Download lessons as needed

## Testing

Run the test script to verify the system:
```bash
python test_role_system.py
```

## Future Enhancements

1. **Lesson Categories**: Add subject-specific categories
2. **Rating System**: Allow students to rate lessons
3. **Comments**: Enable discussion on lessons
4. **Advanced Search**: Full-text search capabilities
5. **Lesson Sharing**: Private lesson sharing between teachers
6. **Analytics**: Track lesson usage and popularity

## Troubleshooting

### Common Issues

1. **Role not showing correctly**: Check session storage and user_info endpoint
2. **Access denied errors**: Verify user role in database
3. **Lessons not appearing**: Check if lessons are marked as public
4. **API errors**: Ensure proper authentication headers

### Debug Steps
1. Check browser console for JavaScript errors
2. Verify user role in session
3. Test API endpoints directly
4. Check database for lesson records

## API Documentation

### Authentication
All API endpoints require authentication via session cookies.

### Error Responses
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Success Responses
All successful responses include:
```json
{
    "success": true,
    "data": {...}
}
``` 