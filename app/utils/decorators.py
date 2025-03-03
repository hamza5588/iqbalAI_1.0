from functools import wraps
from flask import session, redirect, url_for
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.info("Unauthorized access attempt - redirecting to login")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function