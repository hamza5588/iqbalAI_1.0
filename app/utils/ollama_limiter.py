import threading
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class OllamaLimiter:
    """Limits concurrent requests to Ollama across all Flask instances."""
    
    def __init__(self, max_concurrent=2):
        self.semaphore = threading.Semaphore(max_concurrent)
        self.active_requests = 0
        self.lock = threading.Lock()
        self.max_concurrent = max_concurrent
    
    def acquire(self, timeout=None):
        with self.lock:
            self.active_requests += 1
            logger.info(f"[OLLAMA] Active requests: {self.active_requests}/{self.max_concurrent}")
        return self.semaphore.acquire(timeout=timeout)
    
    def release(self):
        with self.lock:
            self.active_requests -= 1
            logger.info(f"[OLLAMA] Active requests: {self.active_requests}/{self.max_concurrent}")
        return self.semaphore.release()
    
    def get_active_count(self):
        with self.lock:
            return self.active_requests

# Global limiter - only 2 requests to Ollama at a time
ollama_limiter = OllamaLimiter(max_concurrent=2)

def limit_ollama_requests(timeout=600):
    """Decorator to limit concurrent Ollama requests."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            acquired = ollama_limiter.acquire(timeout=timeout)
            if not acquired:
                raise TimeoutError("Could not acquire Ollama lock within timeout")
            try:
                return func(*args, **kwargs)
            finally:
                ollama_limiter.release()
        return wrapper
    return decorator