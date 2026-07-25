import logging

from app.core.config import settings
from app.core.logging import configure_logging


# Test 1 - Configuration Does Not Raise
def test_configure_logging():
    configure_logging()


# Test 2 - Root Logger Level
def test_root_logger_level():
    configure_logging()

    root = logging.getLogger()

    expected = getattr(logging, settings.log_level.upper())

    assert root.level == expected


# Test 3 - Console Handler Exists
def test_console_handler_exists():
    configure_logging()

    root = logging.getLogger()

    assert len(root.handlers) > 0


# Test 4 - Formatter Exists
def test_formatter_exists():
    configure_logging()

    root = logging.getLogger()

    for handler in root.handlers:
        assert handler.formatter is not None
