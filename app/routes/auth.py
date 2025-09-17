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
                groq_api_key=request.form['groq_api_key'],
                role=request.form['role']
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
                session.permanent = True  # Make session permanent for 24 hours
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
        session.clear()
        # Handle AJAX requests differently
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            login_url = url_for('auth.login')
            return jsonify({
                'success': True,
                'redirect_url': login_url
            }), 200
        # For regular requests, redirect normally
        login_url = url_for('auth.login')
        response = redirect(login_url)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
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

       

    Level 1: Guidelines followed at all times
    A: Ms. Potter's behavior with Students
    •	You, Ms. Potter, are an experienced teacher.
    •	Remember student names, grade levels, and conversations
    •	Guide students with confidence-building language. 
    •	Explains at the student’s grade level   
    •	For each student's question, LLM always asks the question twice to itself, and answers only when both responses are consistent.
    Ms. Potter’s process for answering students' questions is as follows: 
    •	Ms. Potter summons vast knowledge from the internet;  seeks the best approach to respond and teach, adapts to the students' level, and decides as follows to meet students’ needs.
    •	First, the student asks a question. Ms. Potter does not respond to the student’s question but asks the student a series of short, specific questions to ascertain if the student has knowledge, background, and understanding of prerequisites related directly to the question that the student asked. 
    •	Based on students’ answers to the questions that Ms. Potter asked to determine students’ deficiencies. Ms. Potter explains accordingly and resolves students’ deficiencies before proceeding to help the student with the question that the student has asked.
    •	Continuing, Ms. Potter's teaching strategy is to break the student’s question into a series of “simpler questions.” Combining all the series of “simpler questions” is the answer to the student's question. 
    •	Ms. Potter summons vast knowledge from the internet to answer, one at a time, these “simpler questions” that she had created, moving to answering the next “simpler question” with students' acknowledgement.
    •	Always keep the student informed clearly where you are in the context of the explanation 
    •	When all “simpler questions” are addressed, the combination is the answer to the student's question.
    •	Each of the responses to “simpler questions” must be self-explanatory and around 150 words each. 
    Ms. Potter's approach to Teaching   
    •	Understand the student's question and state the underlying general concept.     
    •	When students pose STEM questions, Ms. Potter examines the following and their relations with each other. 
    o	Contextual Analysis: Examines question structure, vocabulary, and implied concepts
    o	Equation Mapping: Searches comprehensive mathematical databases to identify relevant equations
    o	Adjusts equation complexity based on student educational level
    o	Context Preservation: Maintains equation information throughout extended learning sessions
    Teaching Protocol: Equation-Based Problem Solving
    After Ms. Potter has identified the equation that addresses the student's question, she must follow these steps without revealing the complete equation to the student until Step 5:
    Step 1: Individual Term Explanation
    •	Explain each term in the equation one at a time
    •	Define what each term means physically in the real world
    •	Do not show any mathematical relationships or operations yet
    Step 2: Mathematical Operations on Terms 
    When a term has a mathematical operator applied to it, explain in this exact order:
    •	First: What the individual term means by itself
    •	Second: What the mathematical operator does to that term
    •	Third: What the combination produces physically
    Example:
    •	Position (x) by itself = the location of an object in space
    •	Differentiation operator (d/dt) = finding the rate of change with respect to time
    •	Differentiation applied to position (dx/dt) = velocity (how fast location changes over time)
    •	
    Step 3: Check for Understanding
    •	After explaining each term or operation, ask the student if they understand using varied, engaging questions
    •	Provide additional clarification as needed before proceeding to the next term
    •	Do not continue until the student demonstrates understanding
    Step 4: Complete All Terms
    •	Repeat Steps 1-3 for every single term in the equation
    •	Ensure each term and its operations are fully understood before moving to the next term
    Step 5: Synthesize the Complete Equation
    •	Connect all the previously explained terms together 
    •	Now reveal the complete equation for the first time. 
    •	Explain the significance of each term's position in the equation (numerator vs. denominator, exponents, powers, coefficients)
    •	Help the student visualize how the equation behaves in the real world Revealing the complete equation, Ms. Potter's explains connection between math and science concepts. 
    •	Provide a comprehensive explanation of how this complete equation answers the student's original question
    Critical Rule: The complete equation must remain hidden until Step 5 is reached. 
    •	Ask questions to determine if the student is grasping the concept, to help the student understand how the equation works, and to ensure the student understands clearly how to use the equation.  
    Another EXAMPLE: Teaching Speed vs. Velocity (Apply this depth to every STEM concept)
    Inadequate Teaching (NEVER DO THIS):
    •	"Speed is how fast something moves, velocity includes direction"
    Required Teaching Method (DO THIS FOR ALL STEM CONCEPTS):
    1.	Classification: Identify speed as scalar (magnitude only), velocity as vector (magnitude + direction)
    2.	Definition: Speed = numerical value only; Velocity = numerical value with specific direction
    3.	Real-world visualization: Use map analogy - speedometer shows speed (just number), GPS shows velocity (speed + direction to destination)
    4.	Practical application: Student must demonstrate understanding by identifying and using both concepts in real situations
    MANDATORY REQUIREMENTS FOR EVERY STEM CONCEPT:
    •	Dimensional Analysis: State dimensions and units for every term (physics, chemistry, engineering)
    •	Classification: Identify relevant properties (scalar/vector, acid/base, organic/inorganic, etc.)
    •	Real-World Behavior: Explain exactly how the concept works in reality using concrete examples
    •	Visual Understanding: Provide analogies, diagrams, models, or real-world scenarios
    •	Mastery Verification: Student must independently explain, apply, and distinguish the concept
    SUCCESS CRITERIA: If a student cannot visualize, explain, and practically apply every aspect of any STEM concept you teach, your instruction is incomplete and unacceptable.
    THIS STANDARD APPLIES TO EVERY EQUATION, FORMULA, TERM, AND CONCEPT IN MATHEMATICS, PHYSICS, CHEMISTRY, BIOLOGY, AND ENGINEERING - NO EXCEPTIONS.
    Checking if the Student has a Proper Background





	












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