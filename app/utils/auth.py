# from functools import wraps
# from flask import session, redirect, url_for

# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             return redirect(url_for('auth.login'))
#         return f(*args, **kwargs)
#     return decorated_function 






from functools import wraps
from flask import session, redirect, url_for, request, jsonify

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if it's an AJAX/JSON request
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Not authenticated'}), 401
            # Otherwise redirect to login page
            return redirect(url_for('auth.login'))
        
        # Set user_id on request object for easy access
        request.user_id = session['user_id']
        return f(*args, **kwargs)
    return decorated_function