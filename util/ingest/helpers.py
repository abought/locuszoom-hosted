"""
Generic helper methods
"""

import functools
import logging

from . import exceptions

logger = logging.getLogger(__name__)


def capture_errors(func):
    """
    Log errors internally, but display a more generic error to the user

    Useful for pipelines and validators that need to report success/failure.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception('Task failed due to unhandled error')
            raise exceptions.UnexpectedIngestException
    return wrapper
