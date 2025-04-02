from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from app.models import UserModel
import logging
import requests
import secrets
from datetime import datetime, timedelta
from flask_mail import Message
from app import mail
import os

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__)

# Dictionary to store verification tokens
verification_tokens = {}

@bp.route('/register_email', methods=['GET', 'POST'])
def register_email():
    if request.method == 'POST':
        try:
            email = request.form['useremail']
            
            # Check if email already exists
            if UserModel.get_user_by_email(email):
                return render_template('register_email.html', error="Email already registered")
            
            # Generate verification token
            token = secrets.token_urlsafe(32)
            verification_tokens[token] = {
                'email': email,
                'expires': datetime.now() + timedelta(hours=24)
            }
            
            # Send verification email
            msg = Message('Verify your email',
                        recipients=[email])
            
            # Generate verification link using the request host
            verification_link = url_for('auth.verify_email',
                                      token=token,
                                      _external=True,
                                      _scheme=request.scheme)
            
            # If behind proxy, use X-Forwarded-Host
            if 'X-Forwarded-Host' in request.headers:
                verification_link = f"{request.scheme}://{request.headers['X-Forwarded-Host']}{url_for('auth.verify_email', token=token)}"
            
            msg.body = f'''Please click the following link to verify your email and complete registration:
{verification_link}

This link will expire in 24 hours.

If clicking the link doesn't work, please copy and paste it into your browser.'''
            
            mail.send(msg)
            logger.info(f"Verification email sent to {email} with link: {verification_link}")
            
            return render_template('email_sent.html', email=email)
            
        except Exception as e:
            logger.error(f"Email registration error: {str(e)}")
            return render_template('register_email.html', error="Failed to send verification email")
            
    return render_template('register_email.html')

@bp.route('/verify_email/<token>')
def verify_email(token):
    try:
        logger.info(f"Verifying email with token: {token[:10]}...")  # Log only first 10 chars for security
        
        if token not in verification_tokens:
            logger.warning(f"Invalid token attempted: {token[:10]}...")
            return render_template('register.html', error="Invalid or expired verification link")
        
        token_data = verification_tokens[token]
        if datetime.now() > token_data['expires']:
            verification_tokens.pop(token)
            logger.warning(f"Expired token attempted: {token[:10]}...")
            return render_template('register.html', error="Verification link has expired")
        
        email = token_data['email']
        logger.info(f"Email verified successfully for: {email}")
        
        # Keep the token valid until registration is complete
        return render_template('register.html', email=email)
        
    except Exception as e:
        logger.error(f"Error in email verification: {str(e)}")
        return render_template('register.html', error="An error occurred during verification. Please try again.")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['useremail']
            
            # Verify that email was previously verified
            verified_email = None
            for token_data in verification_tokens.values():
                if token_data['email'] == email:
                    verified_email = email
                    break
                    
            if not verified_email:
                return render_template('register.html', error="Email not verified")
            
            user_id = UserModel.create_user(
                username=request.form['username'],
                useremail=email,
                password=request.form['password'],
                class_standard=request.form['class_standard'],
                medium=request.form['medium'],
                groq_api_key=request.form['groq_api_key']
            )
            
            # Clean up verification token
            for token, data in list(verification_tokens.items()):
                if data['email'] == email:
                    verification_tokens.pop(token)
                    
            return redirect(url_for('auth.login'))
        except ValueError as e:
            return render_template('register.html', error=str(e))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error="Registration failed")
            
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            user = UserModel.get_user_by_email(request.form['useremail'])
            if user and user['password'] == request.form['password']:
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['groq_api_key'] = user['groq_api_key']
                return redirect(url_for('chat.index'))
            return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return render_template('login.html', error="Login failed")
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route('/check_session')
def check_session():
    if 'user_id' in session:
        return {'logged_in': True, 'username': session.get('username')}
    return {'logged_in': False}, 401

@bp.route('/session', methods=['GET'])
def get_session():
    """Get OpenAI realtime session token"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({
                'error': 'OpenAI API key not found in session'
            }), 401

        url = "https://api.openai.com/v1/realtime/sessions"
        
        payload = {
            "model": "gpt-4o-realtime-preview-2024-12-17",
            "modalities": ["audio", "text"],
            "instructions": """Mr. Potter's Teaching Philosophy and Methodology

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
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Failed to get session token'
            }), response.status_code

        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting session token: {str(e)}")
        return jsonify({'error': 'Network error occurred'}), 500
    except Exception as e:
        logger.error(f"Error getting session token: {str(e)}")
        return jsonify({'error': str(e)}), 500