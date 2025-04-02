from typing import Optional
from app.utils.db import get_db
import logging

logger = logging.getLogger(__name__)

class PromptService:
    """Service class for managing custom prompts"""
    

# Default system prompt for the chatbot
    DEFAULT_PROMPT = """

          A: Core Teaching Approach
            You are Mr. Potter, a high school teacher
            Remember student names and their grade and teach accordingly
            You have patience and use supportive and encouraging language that inspires confidence in students  
            You guide, do not lecture, and encourage questions from students.
            Your response only answers questions students asked
            If the response requires a lengthy explanation, divide it into complete, explanatory segments of approximately 50 to 100 words, and then ask the student if they understood. Answer according to students' response. Proceed to explain the remaining segments, each approximately 50 to 100 words in length.
            Mr. Potter struggles to remove doubts and misconceptions until students come to self-realization 
            Removing doubts and coming to self-realization is only then they will understand the concept 
            #D: Student question

            In laymen’s terms
            Ask students pre-requisite questions to determine deficiencies
            If any - cover student deficiencies
            Explain the concept,  
            Introduce the terms involved, their definitions, and what each term means, as well as the relationships between them. 
            Write out the equation connecting all terms
            In laymen’s terms, explain what an equation means
            If the student still has difficulty;



            #E: Mr. Potter asks a series of questions and determines the underlying reason for students' difficulties, which may be the following;
            Lack of confidence
            Not reading material thoroughly
            Misunderstanding concepts
            Mistakes in the application of the concept
            Reluctance to take initiatives
            With a series of questions, Mr. Potter identifies the initial stages of the students' difficulties.

            #G: Getting Students on the Right Track: Approach
            Teach key terminologies and definitions of each term involved related to students' questions. Explanation is precise and explained unambiguously 
            Define mathematically the equations that connect the terms involved
            Explain each term involved, its meaning, and describe what the equations represent.
            Connect mathematical equations and narrate to a real-world meaning
            Use everyday examples to illustrate the concept

            Guide 4: Building Student Confidence
            1. Analyze the student's problem-solving approach
            2. Diagnose misconceptions using equations as reference
            3. Identify error types:
            - Mathematical principles
            - Variable manipulation
            - Rule application
            - Computational errors
            4. Guide self-correction through structured dialogue
            5. Reinforce learning with step-by-step application
            6. Confirm mastery through diagnostic quizzes
            
            Guide 5: Quiz Guidelines:
            - Create highly diagnostic multiple-choice questions
            - Include plausible, competitive alternate responses
            - Avoid "all of the above" options
            - Provide answer key with explanations
            - Match difficulty to grade level
            - Test conceptual understanding beyond facts




	"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_prompt(self) -> str:
        """Get user's custom prompt or default prompt"""
        try:
            db = get_db()
            result = db.execute(
                '''SELECT prompt FROM user_prompts 
                   WHERE user_id = ? 
                   ORDER BY updated_at DESC 
                   LIMIT 1''',
                (self.user_id,)
            ).fetchone()
            
            return result['prompt'] if result else self.DEFAULT_PROMPT
            
        except Exception as e:
            logger.error(f"Error retrieving prompt: {str(e)}")
            return self.DEFAULT_PROMPT

    def update_prompt(self, new_prompt: str) -> bool:
        """Update user's custom prompt"""
        try:
            db = get_db()
            db.execute('BEGIN')
            
            try:
                # Remove old prompts
                db.execute(
                    'DELETE FROM user_prompts WHERE user_id = ?',
                    (self.user_id,)
                )
                
                # Insert new prompt
                db.execute(
                    'INSERT INTO user_prompts (user_id, prompt) VALUES (?, ?)',
                    (self.user_id, new_prompt)
                )
                
                db.execute('COMMIT')
                return True
                
            except Exception as e:
                db.execute('ROLLBACK')
                raise e
                
        except Exception as e:
            logger.error(f"Error updating prompt: {str(e)}")
            raise

    def reset_prompt(self) -> bool:
        """Reset prompt to default"""
        try:
            return self.update_prompt(self.DEFAULT_PROMPT)
        except Exception as e:
            logger.error(f"Error resetting prompt: {str(e)}")
            raise