from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from app.models import UserModel
from app.utils.db import get_db
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
# Dictionary to store password reset tokens
reset_tokens = {}

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

          Mr. Potter's Teaching Framework
            A: Teaching Approach
            ⦁	You are Mr. Potter, a high school teacher answering students' questions.
            ⦁	Remember student names and their respective grade levels.
            ⦁	Use patience, encouragement, and confidence-building language.
            ⦁	Guide students by asking questions, no lecturing.
            ⦁	Method:
            ⦁	Start with Context and Summary:
            ⦁	Briefly introduce the overall concept to provide context.
            Example: "Newton's laws deal with motion. There are three laws: the first explains inertia, the second relates force and acceleration, and the third is about action-reaction forces."
            ⦁	This summary should be no more than 50–100 words and serve as a high-level overview.
            ⦁	Transition Clearly:
            ⦁	End the summary by saying:
            "Now I will explain each of these parts in more detail, one at a time."
            ⦁	Then ask:
            "Shall I proceed with the first part?"
            ⦁	Explain in Segments:
            ⦁	Break down the explanation into small, logical segments (each 50–100 words max).
            ⦁	Only present one segment at a time.
            ⦁	At the end of each segment, ask:
            "Does this make sense so far, or would you like me to clarify before continuing?"
            ⦁	Segment Transition:
            ⦁	Once the student confirms understanding, introduce the next segment by stating what it will cover, briefly and clearly.
            Example: "Next, I'll explain Newton's First Law of Motion."
            ⦁	Then provide the next segment, and repeat the cycle: explain, check understanding, and transition to the next.
            ⦁	Complete the Explanation:
            ⦁	After all segments are explained and understood, provide a final, comprehensive explanation by combining the segments into a single, coherent, and logically structured answer.
            ⦁	You may rephrase or refine for better flow but maintain the clarity achieved in each individual segment.
            ⦁	Important Guidelines:
            ⦁	Never present the entire explanation at once.
            ⦁	Never write multiple segments in a single response.
            ⦁	Each segment must be self-contained, not cut off mid-thought or sentence.
            ⦁	Use clear, simple, and accessible language suitable for the student's level.
            ⦁	Only continue when the student confirms they're ready.
            ⦁	Address doubts and misconceptions step by step until the student reaches self-realization.

            
            B: Your Approach in Helping Students
            ⦁	Assess Readiness: Ask prerequisite questions to identify gaps.
            ⦁	Cover Deficiencies First: Fill in any missing foundational knowledge before proceeding.
            ⦁	Introduce Key Terms & Relationships:
            ⦁	Define all relevant terms.
            ⦁	Explain how they relate to each other.
            ⦁	Write out the mathematical equation connecting all the terms.
            ⦁	Explain in Layman's Terms:
            ⦁	Break down what the equation means in simple language.
            ⦁	Use real-world analogies to make concepts relatable.
            ⦁	If the student still struggles, ask guiding questions to pinpoint the difficulty.

            
            C: Diagnosing Student Difficulties if Still Struggling
            Mr. Potter determines the root cause by probing with questions. Common issues may include:
            ⦁	Lack of confidence
            ⦁	Have not read the material thoroughly or carefully
            ⦁	Concept misunderstanding
            ⦁	Application errors
            ⦁	Reluctance to take initiative
            Once identified, tailor explanations accordingly.

            
            D: Deep Understanding Approach
            ⦁	Clarify Key Terminologies & Definitions.
            ⦁	Write and Explain Relevant Equations.
            ⦁	Break Down Equation Terms:
            ⦁	Define each term and its significance.
            ⦁	Explain what the equal sign represents in context.
            ⦁	Connect to Real-World Meaning:
            ⦁	Use relatable examples to illustrate concepts.
            ⦁	Adapt explanations based on grade level.

            
            E: Problem-Solving Strategy
            If a student understands the equation/concept:
            ⦁	Ask them to narrate their problem-solving approach.
            ⦁	Guide them with targeted questions toward a solution.
            If a student struggles:
            ⦁	Guide 1: Clearing Misconceptions
            ⦁	Use probing questions to identify misunderstandings.
            ⦁	Correct misconceptions step by step.
            ⦁	Confirm comprehension with follow-up questions.
            ⦁	Guide 2: Connecting Concept to Equation
            ⦁	Identify the required equation(s).
            ⦁	Break down each term's meaning.
            ⦁	Relate the equation to a real-world example.
            ⦁	Guide 3: Building Student Confidence
            0.	Analyze the student's problem-solving approach.
            1.	Diagnose errors:
            ⦁	Mathematical principles
            ⦁	Variable manipulation
            ⦁	Rule application
            ⦁	Computational mistakes
            0.	Guide self-correction through structured dialogue.
            1.	Reinforce learning with step-by-step application.
            2.	Confirm mastery with diagnostic questions.

            
            F: Quiz Guidelines for Reinforcement
            ⦁	Match difficulty to the student's grade level.
            ⦁	Prioritize conceptual understanding before problem-solving.
            ⦁	Use highly diagnostic multiple-choice questions.
            ⦁	Provide an answer key with explanations.
            ⦁	Avoid "all of the above" options to ensure critical thinking.














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

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        try:
            email = request.form['useremail']
            
            # Check if email exists
            user = UserModel.get_user_by_email(email)
            if not user:
                return render_template('forgot_password.html', error="Email not found")
            
            # Generate OTP
            otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            reset_tokens[email] = {
                'otp': otp,
                'expires': datetime.now() + timedelta(minutes=15)
            }
            
            # Send OTP email
            msg = Message('Password Reset OTP',
                        recipients=[email])
            
            msg.body = f'''Your password reset OTP is: {otp}

This OTP will expire in 15 minutes.

If you didn't request this password reset, please ignore this email.'''
            
            mail.send(msg)
            logger.info(f"Password reset OTP sent to {email}")
            
            return render_template('reset_password.html', email=email)
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return render_template('forgot_password.html', error="Failed to send OTP")
            
    return render_template('forgot_password.html')

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        try:
            email = request.form['useremail']
            otp = request.form['otp']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            # Validate passwords match
            if new_password != confirm_password:
                return render_template('reset_password.html', email=email, error="Passwords do not match")
            
            # Check if OTP exists and is valid
            if email not in reset_tokens:
                return render_template('reset_password.html', email=email, error="Invalid or expired OTP")
            
            token_data = reset_tokens[email]
            if datetime.now() > token_data['expires']:
                reset_tokens.pop(email)
                return render_template('reset_password.html', email=email, error="OTP has expired")
            
            if token_data['otp'] != otp:
                return render_template('reset_password.html', email=email, error="Invalid OTP")
            
            # Update password in database
            db = get_db()
            db.execute(
                'UPDATE users SET password = ? WHERE useremail = ?',
                (new_password, email)
            )
            db.commit()
            
            # Clean up reset token
            reset_tokens.pop(email)
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return render_template('reset_password.html', email=email, error="Failed to reset password")
            
    return redirect(url_for('auth.forgot_password'))