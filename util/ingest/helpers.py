"""
Generic helper methods
"""

import functools
import logging


logger = logging.getLogger(__name__)


def false_on_fail(func):
    """Return False if any error occurs. Useful for pipelines and validators that need to report success/failure."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception('Task failed due to error')
            return False
    return wrapper
