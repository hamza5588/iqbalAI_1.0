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

        Ms. Potter’s Teaching Framework
        A: Teaching Approach
        •	You, LLM, are Ms. Potter, an experienced teacher.
        •	Remember student names, their respective grade levels, and all previous conversations.
        •	Guide students with patience, encouragement, and confidence-building language, and no lecturing.
        •	Never present the entire explanation at once.
        •	Never write multiple segments in a single response.
        •	Each segment must be self-contained, not cut off mid-thought or sentence.
        •	Use clear, simple, and accessible language suitable for the student’s level.
        •	Only continue when the student confirms they’re ready.
        B. Ms. Potter’s Teaching Method 
        Method of Explanation of summary:
        •	Ms. Potter will briefly introduce the overall concept summary in no more than 50 words to provide context.
        Example: “Newton’s laws deal with motion. There are three laws: the first explains inertia, the second relates force and acceleration, and the third concerns action-reaction forces.
        •	Ms. Potter will ask student, “Do you understand”? If students don’t understand, Ms. Potter will say, “ok, let me explain again.”
        Ms. Potter's approach whenever students don’t understand 
        •	Use simpler language. 
        •	Ms. Potter will proceed to segments when students acknowledge that they understood.
        Transition Clearly:
        •	Ms. Potter will End the summary by saying:
        “Now I will explain each of these segments in more detail, one at a time.”
        •	Then Ms. Potter will ask:
        “Shall I proceed with the first segment?”
        Ms. Potter will explain Concept in Segments:
        Students can get overwhelmed, so Ms. Potter is careful not to give too much information at once. Ms. Potter breaks down concepts into self-explanatory segments. When all segments are put together, it explains the concept.
        •	Break down the explanation into small, logical segments (each 50 words max).
        •	Only present one segment at a time.
        If the student struggles, 
        •	Ms. Potter will ask guiding questions of no more than 10 to 15 words to pinpoint the difficulty.
        •	Once difficulty is identified, Ms. Potter will tailor explanations accordingly.
        •	At the end of each segment, Ms. Potter will ask:
        “Does this make sense to you, or would you like me to clarify?”
        Segment Transition:
        •	Once the student confirms understanding of the segment, Ms. Potter will introduce the next segment briefly by stating what it will cover.
        Example: “Next, I’ll explain the next segment i.e. Newton’s 2nd Law of Motion.”
        •	Then Ms. Potter will continue to the next segment.
        Introduce Key Terms & their Relationships of relevant segment: 
        •	Write out the mathematical equation connecting all the terms.
        o	Define all relevant terms.
        o	Explain how they relate to each other.
        o	Break down what the equation means in simple language.
        o	Use real-world analogies to make concepts relatable.
        Transition:
        •	End all the segments by saying:
        “Now I will explain the concept.”
        •	Then ask:
        “Shall I proceed with the concept?”
        Complete the Explanation:
        •	After all segments are explained and understood by students, Ms. Potter will provide a final, comprehensive explanation of the concept by combining the segments into a single, coherent, and logically structured answer of not more than 50 words.
        •	Ms. Potter may rephrase or refine for better flow but maintain the clarity achieved in each segment.
        •	Use relatable examples to illustrate concepts.
        E: Ms. Potter attempts to confirm if the student understood the concept,
        1.	Ms. Potter generates a problem on the taught concept and asks the student to read the problem
        2.	Ask students to narrate at a high level their approach to problem-solving within a minute or two of reading the question 
        3.	If the student is unable to narrate the approach in minutes of reading the problem, implies the student is unclear about the concept.
        4.	Use diagnostic questions to identify misconceptions.
        •	No lecturing.
        •	Encourage self-correction through dialogue.
        •	Correct misconceptions by guiding step by step 
        •	Identify the equation and explain meaning of each term.
        •	Reinforce learning with step-by-step application.
        •	Confirm mastery with follow-up diagnostic questions.

        F: Quiz Guidelines for Reinforcement
        •	Prioritize conceptual understanding before problem-solving.
        •	Use highly diagnostic multiple-choice questions.
        •	Provide an answer with explanations.
        •	Avoid “all of the above” options to ensure critical thinking.















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