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
# API
# =============================================================================

API_PREFIX: Final[str] = "/api/v1"

OPENAPI_URL: Final[str] = "/openapi.json"
DOCS_URL: Final[str] = "/docs"
REDOC_URL: Final[str] = "/redoc"

# =============================================================================
# Pagination
# =============================================================================

DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# =============================================================================
# Logging
# =============================================================================

DEFAULT_LOG_LEVEL: Final[str] = "INFO"

# =============================================================================
# HTTP Headers
# =============================================================================

HEADER_REQUEST_ID: Final[str] = "X-Request-ID"
HEADER_RESPONSE_TIME: Final[str] = "X-Response-Time"

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
