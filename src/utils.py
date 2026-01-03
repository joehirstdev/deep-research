"""Simple retry utility."""

import time
from functools import wraps


def retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0):
    """Retry a function with exponential backoff."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor

        return wrapper

    return decorator
