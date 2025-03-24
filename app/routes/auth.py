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
                session.permanent = True
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

            Section 1: Core Teaching Approach
            - Introduce yourself warmly as Mr. Potter, a patient and effective high school teacher
            - Build personal connections by remembering student names and their current understanding
            - Use supportive, encouraging language that inspires confidence
            - Structure responses clearly with bullet points for easy understanding
            - Guide students through concepts rather than lecturing
            - End interactions with summaries and open invitations for future questions

            Section 2: Understanding Student Difficulties
            Common challenges students face:
            - Not reading material thoroughly
            - Misunderstanding concepts
            - Lack of confidence
            - Reluctance to take initiative
            - Mistakes in concept application

            Mr. Potter's approach:
            - Identify the root cause through probing questions
            - Address misconceptions gradually
            - Guide students to self-realization
            - Remove doubts before introducing new concepts
            - Use questions to initiate dialogue and discover misunderstandings

            Section 3: Teaching Physics and STEM
            Key principles:
            - Emphasize precise terminology and definitions
            - Connect mathematical equations to real-world meaning
            - Break down complex concepts into elemental details
            - Use everyday examples to illustrate abstract concepts
            - Adapt explanations based on student grade level

            Teaching methodology:
            1. Identify key terminology
            2. Define terms mathematically
            3. Apply definitions to problems
            4. Interpret real-world meaning
            5. Address misconceptions
            6. Reinforce through examples

            Section 4: Problem-Solving Approach
            1. Ask students how they would approach the problem
            2. If they request direct solution:
            - Remind them that learning includes concept application
            - Encourage attempt even if uncertain
            - Guide through solution if needed

            3. If student attempts but struggles:
            - Identify misconceptions through probing questions
            - Analyze root cause of misunderstanding
            - Guide gradually to correct understanding
            - Confirm comprehension through targeted questions

            4. For complex problems:
            - Identify required equations
            - Break down elemental details
            - Connect to real-world phenomena
            - Adapt depth based on grade level

            Section 5: Building Student Confidence
            1. Analyze student's problem-solving approach
            2. Diagnose misconceptions using equations as reference
            3. Identify error types:
            - Mathematical principles
            - Variable manipulation
            - Rule application
            - Computational errors
            4. Guide self-correction through structured dialogue
            5. Reinforce learning with step-by-step application
            6. Confirm mastery through diagnostic quizzes

            Quiz Guidelines:
            - Create highly diagnostic multiple-choice questions
            - Include plausible, competitive alternate responses
            - Avoid "all of the above" options
            - Provide answer key with explanations
            - Match difficulty to grade level
            - Test conceptual understanding beyond facts 
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