"""
Logging configuration constants.

This module defines immutable logging-related constants shared across
the application. Logging initialization should be performed elsewhere.
"""

from typing import Final

# =============================================================================
# Logger
# =============================================================================

LOGGER_NAME: Final[str] = "investment_os"

# =============================================================================
# Log Levels
# =============================================================================

DEFAULT_LOG_LEVEL: Final[str] = "INFO"

# =============================================================================
# Log Format
# =============================================================================

DEFAULT_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | " "%(request_id)s | %(name)s | %(message)s"
)

DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Request Context
# =============================================================================

REQUEST_ID_LOG_KEY: Final[str] = "request_id"

# =============================================================================
# Performance
# =============================================================================

SLOW_REQUEST_THRESHOLD_MS: Final[int] = 1000
