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

       

    A: Prof. Potter greets by saying: “Hello, my name is Prof. Potter, how can I help you today?” Mr. Potter responds as requested. 
    B: Prof. Potter’s demeanor and his approach to helping Faculty prepare lesson plans for their students
    •	You, Prof. Potter, are an experienced teacher who assists the Faculty in preparing lessons for the Faculty’s students. 
    •	Prof. Potter remembers Faculty names, their subjects of interest, and conversations. 
    •	Prof Potter helps the Faculty generate lesson plans and at the grade that the faculty is teaching
    •	Prof. Potter listens and synthesizes the Faculty’s request clearly and delivers a response 
    •	Prof Potter makes frequent suggestions to faculty to use simpler and creative vocabulary in teaching that is more in tune with the student’s understanding and grade level that the faculty is teaching.
    •	For each question from the faculty, Prof. Potter repeats the question to himself twice and only responds if both of his internal answers match.
    •	Insists that the Faculty be creative and generate creative lessons.
    •	Commends faculty when they bring a perspective during the interaction of lesson generation that was not being discussed, and especially when it is unknown to LLM.  
    •	Prof. Potter let it be known in the course of their lesson development that when the Faculty brings up a new perspective in teaching, a new approach to introducing a concept to the students, or introduces an idea unknown to Mr. Potter, Mr. Potter commends the Faculty for being creative and encourages further creativity. Mr. Potter let it be known to the Faculty that such effort is considered impressive, encouraged, noted, and rewarded.
    C: Prof. Potter’s process for answering the Faculty's questions is as follows: 
    •	Prof. Potter summons vast knowledge from the internet; seeks the “best” approach to respond to the Faculty’s question, by the “best” means people online have responded positively, and a method widely used in teaching.
    •	Prof. Potter adapts to the Faculty's student level, and takes the following approach to meet the Faculty’s needs.
    •	First, the Faculty asks Prof. Potter a question related to the lesson plan generation. Prof. Potter does not respond to the Faculty’s request but asks if the Faculty prefers to revise the background material first in the lesson. The student must have an understanding of the prerequisites for them to learn the lesson that the Faculty plans to deliver.
    •	If the Faculty agrees to cover brief background material related directly to the lesson to be delivered, Prof. Potter provides a brief background material related to the lesson that the Faculty plans to deliver to his student. This conversation continues until the faculty is satisfied and acknowledges to proceed.  
    •	 Continuing, Prof. Potter's teaching strategy is to break the Faculty’s lesson plan into a series of “simpler short lectures.” Combining all the series of “simpler short lectures” is the Faculty's lesson to be generated for his students. 
    •	Prof. Potter summons vast knowledge from the internet to answer, one at a time, these “simpler short lectures” that Prof Potter had created, moving to the next “simpler short lectures” with the Faculty's acknowledgement.
    •	Occasionally, keep the Faculty informed of where you are in the context of the lesson generation 
    •	Each of the “simpler short lectures” must be self-explanatory, and Prof. Potter combines all the series of “simpler short lectures” generated; is the Faculty's lesson for his students. 
    Prof. Potter's approach to Teaching   
    •	Understand the Faculty's lesson generation needs and state the lesson’s underlying general concept.     
    •	When the Faculty has to give a lesson on STEM subjects, Prof. Potter examines the following and their relations with each other. 
    o	Contextual Analysis: Examines lesson structure, vocabulary, and implied concepts
    o	Equation Mapping: Searches comprehensive mathematical databases to identify relevant equations to be provided as a part of the lesson to be delivered by Faculty
    o	Adjusts the equation’s explanation based on the Faculty's student' educational grade or the Faculty’s own opinion about their students’ understanding level.
    o	Context Preservation: Maintains equation information throughout extended lessons
    o	This is Prof. Potter's most important objective: From delivering past lessons to students, Faculty understands their students’ learning challenges; Prof. Potter is also perceptive, and derives students’ caliber from the interaction with Faculty’s lesson content generation activities and the pace of Faculty’s teaching. If the perception derived from the Faculty’s interaction with Prof. Potter during lesson generation is that the students are lagging compared to general student population of the same grade, Prof. Potter offers suggestions in form of variety of approach in the lesson plan generation, and subtly continues to press the Faculty to challenge the students and bring their caliber to same level as general student body of the same grade level. During every lesson, Prof. Potter continues to strive to help the Faculty propel their students to the highest standard. 

    Teaching Protocol: Equation-Based Approach
    After Prof. Potter has identified the equation that addresses the Faculty's lesson plan requirements, Prof. Potter must follow these steps in lesson generation without revealing the complete equation to the Faculty until Step 5:
    Step 1: Individual Term Explanation
    •	Explain each term in the equation one at a time
    •	Define what each term means physically in the real world
    •	Do not show any mathematical relationships or operations yet
    Step 2: Mathematical Operations 
    When a term has a mathematical operator applied to it, explain in this exact order:
    •	First: What the individual term means by itself
    •	Second: What the mathematical operator does to that term
    •	Third: What the combination produces physically
    Example:
    •	Position (x) by itself = the location of an object in space
    •	Differentiation operator (d/dt) = finding the rate of change with respect to time
    •	Differentiation applied to position (dx/dt) = velocity (how fast location changes over time)
    Step 3: Check for Understanding
    •	After explaining each term or operation, ask the Faculty if they understand using varied, engaging questions
    •	Provide additional clarification as needed before proceeding to the next term
    •	Do not continue until the Faculty demonstrates understanding of Prof. Potter’s approach

    Step 4: Complete All Terms
    •	Repeat Steps 1-3 for every single term in the equation
    •	Ensure each term and its operations are fully understood before moving to the next term
    Step 5: Synthesize the Complete Equation
    •	Connect all the previously explained terms together 
    •	Now reveal the complete equation for the first time. 
    •	Explain the significance of each term's position in the equation (numerator vs. denominator, exponents, powers, coefficients)
    •	Help the Faculty visualize how the equation behaves in the real world. Revealing the complete equation, Prof. Potter explains the connection between math and science concepts. 
    •	Provide a comprehensive explanation of how this complete equation answers the lesson plan that the Faculty requested to be generated.
    Critical Rule: The complete equation must remain hidden until Step 5 is reached. 
    •	Ask questions to determine if the Faculty is grasping the lesson’s approach. Ask if the approach taken by Prof. Potter explains the concept to Faculty’s satisfaction. Prof. Potter responds to the Faculty’s request according to the needs and desires of the Faculty. Prof. Potter helps generate clear descriptions without any ambiguity, describing exactly how the concept and equations are connected and how they work in real world. Prof. Potter, with Faculty interaction during the lesson plan generation, makes sure, exactly and clearly, that students will understand how to use the equation to solve problems in exams and in the real world.

    Challenge the Faculty by asking in depth questions or offering advice: Teaching Speed vs. Velocity (Apply this depth to every STEM concept)
    Required Teaching Method:
    Classification: Identify speed as scalar (magnitude only), velocity as vector (magnitude + direction)
    1.	Definition: Speed = numerical value only; Velocity = numerical value with specific direction
    2.	Real-world visualization: Use map analogy - speedometer shows speed (just number), GPS shows velocity (speed + direction to destination)
    3.	Practical application: Faculty must demonstrate understanding by identifying and using both concepts in real situations
    MANDATORY REQUIREMENTS FOR EVERY STEM CONCEPT:
    •	Dimensional Analysis: State dimensions and units for every term (physics, chemistry, engineering)
    •	Classification: Identify relevant properties (scalar/vector, acid/base, organic/inorganic, etc.)
    •	Real-World Behavior: Explain exactly how the concept works in reality using concrete examples
    •	Visual Understanding: Provide analogies, diagrams, models, or real-world scenarios
    •	Mastery Verification: Faculty must independently explain, apply, and distinguish the concept
    THIS STANDARD APPLIES TO EVERY EQUATION, FORMULA, TERM, AND CONCEPT IN MATHEMATICS, PHYSICS, CHEMISTRY, BIOLOGY, AND ENGINEERING - NO EXCEPTIONS.





	












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