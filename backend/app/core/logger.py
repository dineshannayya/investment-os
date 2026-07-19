"""
Application logger factory.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger instance.

    Args:
        name: Logger name, typically __name__.

    Returns:
        logging.Logger
    """
    return logging.getLogger(name)
