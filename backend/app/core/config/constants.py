"""
Application constants.

This module contains immutable constants that are shared across the
application. These values should NOT depend on environment variables.
"""

from typing import Final

# =============================================================================
# Application
# =============================================================================

APP_NAME: Final[str] = "Investment OS"
APP_VERSION: Final[str] = "0.1.0"

# =============================================================================
# Environment
# =============================================================================

DEFAULT_ENVIRONMENT: Final[str] = "development"

# =============================================================================
# Health Status
# =============================================================================

STATUS_OK: Final[str] = "ok"
STATUS_READY: Final[str] = "ready"
STATUS_NOT_CONFIGURED: Final[str] = "not_configured"

# =============================================================================
# Service Names
# =============================================================================

SERVICE_DATABASE: Final[str] = "database"
SERVICE_REDIS: Final[str] = "redis"
SERVICE_LLM: Final[str] = "llm"

# ===========================================================
# Security
# ==========================================================
DEFAULT_JWT_SECRET_KEY: Final[str] = ( "development-only-secret-key-change-before-production")

DEFAULT_JWT_ALGORITHM: Final[str] = "HS256"

DEFAULT_JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30

DEFAULT_JWT_REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 30

DEFAULT_JWT_ISSUER: Final[str] = "investment-os"

