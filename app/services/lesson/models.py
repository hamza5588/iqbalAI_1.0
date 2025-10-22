"""
Pydantic models for structured lesson output
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Section(BaseModel):
    heading: str = Field(description="The heading/title of the section")
    content: str = Field(description="The content/body of the section")


class CreativeActivity(BaseModel):
    name: str = Field(description="Name of the creative activity")
    description: str = Field(description="Detailed description of the activity")
    duration: str = Field(description="Duration of the activity (e.g., '15-20 minutes')")
    learning_purpose: str = Field(description="What students will gain from this activity")


class STEMEquation(BaseModel):
    equation: str = Field(description="The mathematical equation")
    term_explanations: List[str] = Field(description="Explanations of each term in the equation")
    mathematical_operations: str = Field(description="How operations transform the terms")
    complete_equation_significance: str = Field(description="What the complete equation reveals")


class QuizQuestion(BaseModel):
    question: str = Field(description="The quiz question")
    options: List[str] = Field(description="List of answer options (A, B, C, D)")
    answer: str = Field(description="Correct answer (A, B, C, or D)")
    explanation: str = Field(description="Explanation for the correct answer")


class LessonPlan(BaseModel):
    title: str = Field(description="Clear and descriptive lesson title")
    summary: str = Field(description="Brief 2-3 sentence summary of what this lesson covers")
    learning_objectives: List[str] = Field(description="Specific learning objectives")
    background_prerequisites: List[str] = Field(description="Essential background knowledge students need")
    sections: List[Section] = Field(description="Main lesson sections with headings and content")
    key_concepts: List[str] = Field(description="Important concepts covered in the lesson")
    creative_activities: List[CreativeActivity] = Field(description="Engaging activities for students")
    stem_equations: List[STEMEquation] = Field(description="Relevant equations and their explanations")
    assessment_quiz: List[QuizQuestion] = Field(description="Quiz questions to test understanding")
    teacher_notes: List[str] = Field(description="Suggestions and notes for teachers")


class DirectAnswer(BaseModel):
    user_question: str = Field(description="The question asked by the user")
    answer: str = Field(description="A detailed and accurate explanation or answer to the question")


class LessonResponse(BaseModel):
    response_type: str = Field(description="Type of response: 'lesson_plan' or 'direct_answer'")
    answer: Optional[LessonPlan] = Field(default=None, description="Structured lesson plan if response_type is 'lesson_plan'")
    user_question: Optional[str] = Field(default=None, description="Original user question if response_type is 'direct_answer'")
    direct_answer: Optional[str] = Field(default=None, description="Direct answer if response_type is 'direct_answer'")



