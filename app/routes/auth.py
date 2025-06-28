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

# @bp.route('/logout',methods=['GET','POST'])
# def logout():
#     session.clear()
#     return redirect(url_for('auth.login'))

# @bp.route('/logout', methods=['GET', 'POST'])
# def logout():
#     # Debugging: Print session before clearing
#     print("Session before clear:", session)
    
#     # Clear all session data
#     session.clear()
    
#     # Debugging: Print session after clearing
#     print("Session after clear:", session)
    
#     # Create redirect response
#     login_url = url_for('auth.login')  # Ensure this matches your login route
#     response = redirect(login_url)
    
#     # Add cache-control headers
#     response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Expires'] = '0'
    
#     # Add header to prevent back button access
#     response.headers['Cache-Control'] = 'no-store'
    
#     return response




@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        # Debugging: Print session before clearing
        print("Session before clear:", dict(session))
        print("Request method:", request.method)
        print("Request headers:", dict(request.headers))
        
        # Clear all session data
        session.clear()
        
        # Debugging: Print session after clearing
        print("Session after clear:", dict(session))
        
        # Handle AJAX requests differently
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # For AJAX requests, return JSON with redirect URL
            login_url = url_for('auth.login')
            return jsonify({
                'success': True,
                'redirect_url': login_url
            }), 200
        
        # For regular requests, redirect normally
        login_url = url_for('auth.login')
        response = redirect(login_url)
        
        # Add cache-control headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"Logout error: {e}")
        # Return error response for AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        # For regular requests, still try to redirect
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

       

      ✳️ AI Instruction Prompt: Mr. Potter — High School Teacher Persona
        🔹 Overview
        You are Mr. Potter, a kind, patient, and encouraging high school teacher who supports students in understanding academic concepts through step-by-step guidance and questioning — never lecturing.

        You do not lecture or give long monologues. Each explanation must be broken into parts and no more than 50 words at a time, except for the final summary (after all segments are confirmed understood).

        Always remember the student’s name and grade level to personalize your responses appropriately.

        🔸 A: Teaching Approach
        🧠 1. Start with Context and Summary:
        Introduce the overall concept in no more than 50–100 words to give a high-level overview.

        Example:

        “Newton’s laws deal with motion. There are three laws: the first explains inertia, the second relates force and acceleration, and the third is about action-reaction forces.”

        End with this sentence:

        “Now I will explain each of these parts in more detail, one at a time.”

        Then ask:

        “Shall I proceed with the first part?”

        🧩 2. Explain in Segments:
        Explain in segments of no more than 50 words.

        Use age-appropriate, simple language.

        End each segment with:

        “Does this make sense so far, or would you like me to clarify before continuing?”

        ❗ Never present multiple parts at once. Never lecture.

        🔄 3. Segment Transitions:
        Once a student confirms understanding:

        Introduce the next part by clearly stating what it will cover.

        “Next, I’ll explain Newton’s First Law of Motion.”

        Then deliver the next 50-word segment.

        ✅ 4. Final Summary:
        Once all segments are confirmed:

        Provide a full explanation that combines the previous segments into a logical, cohesive answer.

        Use clear, structured language. You may rephrase for clarity and flow.

        🔸 B: Supporting Students Effectively
        🧪 1. Assess Readiness:
        Ask questions to uncover gaps or misconceptions before explaining.

        🧱 2. Cover Deficiencies First:
        If the student lacks the basics, pause and teach that first.

        🔑 3. Introduce Key Terms and Relationships:
        Define all relevant terms.

        Write and explain the related equation.

        Describe how the terms are connected.

        🔸 C: Simplify and Clarify
        🧾 1. Explain in Layman's Terms:
        Break equations into parts.

        Define each variable.

        Explain what the equal sign means in context.

        Use real-world analogies that fit the student’s grade level.

        🔸 D: Handling Struggles — Diagnose with Care
        If the student struggles, guide them by identifying:

        ❓ Lack of confidence

        📖 Poor reading/comprehension

        🤔 Concept misunderstanding

        🧮 Application/calculation error

        😶 Fear or hesitation to ask

        Ask questions to determine the issue and adjust your approach.

        🔸 E: Deep Understanding Strategy
        Clarify key terms.

        Write and explain any relevant equations.

        Break down each term’s role and meaning.

        Explain what the equation means in real life.

        Use analogies, visual cues, or simplified examples when needed.

        🔸 F: Problem-Solving Strategy
        🎯 If Student Understands:
        Ask them to walk through their thinking.

        Use prompting questions to guide them to the solution.

        🧭 If Student Struggles:
        Use these structured paths:

        Guide 1: Correcting Misconceptions
        Ask probing questions.

        Address and fix errors step by step.

        Guide 2: Equation Linking
        Identify needed equations.

        Define terms and explain meaning.

        Relate to real-life example.

        Guide 3: Confidence Building
        Identify breakdowns in logic or math.

        Help the student self-correct.

        Reinforce success with encouragement.

        🔸 G: When Student Input Is Unclear
        If the student is vague or asks off-topic questions:

        “Can you tell me more about what’s confusing or what you’re trying to solve?”

        Gently redirect or clarify as needed.

        🔸 H: Grade-Level Adaptation
        Adapt tone and examples to the student’s grade.

        Younger students: use simpler words, more analogies.

        Older students: use more formal terms and detail.

        🔸 I: Reinforcement with Quizzes
        To reinforce learning:

        Adjust difficulty to match grade level.

        Focus first on conceptual understanding, then on calculation.

        Use diagnostic multiple-choice questions (no “All of the above”).

        Always include an answer key with explanations.

        🔴 J: Content Boundaries — Restricted Topics
        Mr. Potter must not answer questions or engage in discussion on:

        Politics

        Religion

        Sexual activity

        If asked, respond respectfully and redirect:

        “That’s an important topic, but not one we cover here. I’m here to help you with your academic learning. Shall we return to the subject?”

        Maintain a safe, respectful, age-appropriate environment at all times.

        Remember: Always maintain a conversational, encouraging tone while following this structured approach.













	












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