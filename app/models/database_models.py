"""SQLAlchemy database models for the application"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, 
    CheckConstraint, UniqueConstraint, Index, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    useremail = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='student',
                  server_default='student')
    class_standard = Column(String(100), nullable=False)
    medium = Column(String(100), nullable=False)
    groq_api_key = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    lessons = relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    survey_responses = relationship("SurveyResponse", back_populates="user", cascade="all, delete-orphan")
    user_prompts = relationship("UserPrompt", back_populates="user", cascade="all, delete-orphan")
    user_documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    token_usage = relationship("UserTokenUsage", back_populates="user", cascade="all, delete-orphan")
    token_reset_history = relationship("TokenResetHistory", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher')", name='check_user_role'),
    )


class Lesson(Base):
    """Lesson model"""
    __tablename__ = 'lessons'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    detailed_answer = Column(Text, nullable=True)
    learning_objectives = Column(Text, nullable=True)
    focus_area = Column(String(255), nullable=True)
    grade_level = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, 
                       server_default=func.now(), server_onupdate=func.now())
    is_public = Column(Boolean, default=True, server_default='1')
    has_child_version = Column(Boolean, default=False, server_default='0')
    parent_lesson_id = Column(Integer, ForeignKey('lessons.id', ondelete='CASCADE'), nullable=True)
    version = Column(Integer, default=1, server_default='1')
    
    # Versioning fields
    lesson_id = Column(String(100), nullable=True)  # Logical lesson identifier
    version_number = Column(Integer, default=1, server_default='1')
    parent_version_id = Column(Integer, ForeignKey('lessons.id', ondelete='CASCADE'), nullable=True)
    original_content = Column(Text, nullable=True)
    draft_content = Column(Text, nullable=True)
    status = Column(String(50), default='finalized', server_default='finalized')
    
    # Relationships
    teacher = relationship("User", back_populates="lessons")
    parent_lesson = relationship("Lesson", remote_side=[id], foreign_keys=[parent_lesson_id])
    parent_version = relationship("Lesson", remote_side=[id], foreign_keys=[parent_version_id])
    
    __table_args__ = (
        UniqueConstraint('lesson_id', 'version_number', name='idx_lesson_version_unique'),
        Index('idx_lessons_teacher_id', 'teacher_id'),
        Index('idx_lessons_grade_level', 'grade_level'),
        Index('idx_lessons_focus_area', 'focus_area'),
        Index('idx_lessons_is_public', 'is_public'),
    )


class Conversation(Base):
    """Conversation model"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, server_default='1')
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                       server_default=func.now(), server_onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    chat_history = relationship("ChatHistory", back_populates="conversation", 
                               cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_conversations_user_id', 'user_id'),
    )


class ChatHistory(Base):
    """Chat history model"""
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), 
                            nullable=False)
    message = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="chat_history")
    
    __table_args__ = (
        CheckConstraint("role IN ('user', 'bot')", name='check_chat_role'),
        Index('idx_chat_history_conversation_id', 'conversation_id'),
    )


class SurveyResponse(Base):
    """Survey response model"""
    __tablename__ = 'survey_responses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating = Column(Integer, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="survey_responses")
    
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 10", name='check_rating_range'),
    )


class UserPrompt(Base):
    """User prompt model"""
    __tablename__ = 'user_prompts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                       server_default=func.now(), server_onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_prompts")
    
    __table_args__ = (
        Index('idx_user_prompts_user_id', 'user_id'),
    )


class UserDocument(Base):
    """User document model"""
    __tablename__ = 'user_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    vector_db_ids = Column(Text, nullable=True)
    processed = Column(Boolean, default=False, server_default='0')
    uploaded_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_documents")
    
    __table_args__ = (
        Index('idx_user_documents_user_id', 'user_id'),
        Index('idx_user_documents_file_type', 'file_type'),
    )


class UserTokenUsage(Base):
    """User token usage model"""
    __tablename__ = 'user_token_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False, default=datetime.utcnow().date, 
                  server_default=func.current_date())
    tokens_used = Column(Integer, nullable=False, default=0, server_default='0')
    last_updated = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="token_usage")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_date'),
        Index('idx_user_token_usage_user_id', 'user_id'),
        Index('idx_user_token_usage_date', 'date'),
    )


class TokenResetHistory(Base):
    """Token reset history model"""
    __tablename__ = 'token_reset_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reset_time = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    tokens_used = Column(Integer, nullable=False)
    was_limit_reached = Column(Boolean, default=False, server_default='0')
    
    # Relationships
    user = relationship("User", back_populates="token_reset_history")


class LessonFAQ(Base):
    """Lesson FAQ model"""
    __tablename__ = 'lesson_faq'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, nullable=False)  # References lessons.id
    question = Column(Text, nullable=False)
    count = Column(Integer, default=1, server_default='1')
    canonical_question = Column(Text, nullable=True)


class LessonChatHistory(Base):
    """Lesson chat history model"""
    __tablename__ = 'lesson_chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, nullable=False)  # References lessons.id
    user_id = Column(Integer, nullable=False)  # References users.id
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    canonical_question = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

