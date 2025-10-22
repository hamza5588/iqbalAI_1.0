# Lesson Service Structure

This directory contains the organized lesson service functionality, split into separate modules for better maintainability and clarity.

## Structure

```
app/services/lesson/
├── __init__.py              # Package initialization and exports
├── models.py                # Pydantic models for structured output
├── base_service.py          # Common functionality shared between services
├── teacher_service.py       # Teacher-focused lesson operations
├── student_service.py       # Student-focused lesson operations
└── README.md               # This documentation
```

## Services

### TeacherLessonService
Handles teacher-focused operations:
- **File Processing**: Upload and process PDF, DOC, DOCX, TXT files
- **Lesson Generation**: Create comprehensive lesson plans using AI
- **Document Creation**: Generate DOCX and PPTX files
- **Content Editing**: Edit lessons with AI assistance
- **Content Improvement**: Enhance lesson content based on prompts

### StudentLessonService
Handles student-focused operations:
- **Question Answering**: Answer student questions about lessons
- **FAQ Management**: Generate and manage frequently asked questions
- **Content Summarization**: Create student-friendly summaries
- **Key Points Extraction**: Extract important learning points
- **Semantic Question Matching**: Canonicalize similar questions

### BaseLessonService
Contains shared functionality:
- **Document Loading**: Support for multiple file formats
- **Section Extraction**: Extract specific sections from documents
- **JSON Parsing**: Robust JSON parsing with fallbacks
- **Fallback Generation**: Create basic lessons when AI fails

## Models

### Pydantic Models
- `Section`: Individual lesson sections with heading and content
- `CreativeActivity`: Engaging activities for students
- `STEMEquation`: Mathematical equations with explanations
- `QuizQuestion`: Assessment questions with options and explanations
- `LessonPlan`: Complete structured lesson plan
- `DirectAnswer`: Simple question-answer pairs
- `LessonResponse`: Wrapper for different response types

## Usage

### Teacher Operations
```python
from app.services.lesson import TeacherLessonService

teacher_service = TeacherLessonService(api_key)
result = teacher_service.process_file(file, lesson_details)
docx_bytes = teacher_service.create_docx(lesson_data)
ppt_bytes = teacher_service.create_ppt(lesson_data)
```

### Student Operations
```python
from app.services.lesson import StudentLessonService

student_service = StudentLessonService(api_key)
answer = student_service.answer_lesson_question(lesson_id, question)
faqs = student_service.get_lesson_faqs(lesson_id)
summary = student_service.get_lesson_summary(lesson_id)
```

### Main Service (Backward Compatibility)
```python
from app.services.lesson_service import LessonService

# This automatically delegates to appropriate services
lesson_service = LessonService(api_key)
result = lesson_service.process_file(file, lesson_details)  # Teacher operation
answer = lesson_service.answer_lesson_question(lesson_id, question)  # Student operation
```

## Benefits

1. **Separation of Concerns**: Teacher and student functionality are clearly separated
2. **Maintainability**: Each service has a focused responsibility
3. **Reusability**: Services can be used independently
4. **Testability**: Each service can be tested in isolation
5. **Backward Compatibility**: Existing code continues to work
6. **Type Safety**: Pydantic models ensure structured output
7. **Error Handling**: Robust fallbacks and error management

## Migration

The main `LessonService` class now acts as a facade that delegates to the appropriate specialized service. This ensures backward compatibility while providing the benefits of the new structure.

Existing code using `LessonService` will continue to work without changes, but new code can directly use the specialized services for better organization.



