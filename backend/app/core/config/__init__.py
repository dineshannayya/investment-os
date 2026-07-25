"""
Configuration package.

Provides a single import point for configuration.
"""

# =============================================================================
# Runtime Settings
# =============================================================================

# =============================================================================
# Constants
# =============================================================================
from app.core.config.constants import (
    API_PREFIX,
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENVIRONMENT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PAGE_SIZE,
    DOCS_URL,
    HEADER_REQUEST_ID,
    HEADER_RESPONSE_TIME,
    MAX_PAGE_SIZE,
    OPENAPI_URL,
    REDOC_URL,
    SERVICE_DATABASE,
    SERVICE_LLM,
    SERVICE_REDIS,
    STATUS_NOT_CONFIGURED,
    STATUS_OK,
    STATUS_READY,
)
from app.core.config.settings import (
    Settings,
    get_settings,
    settings,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    "get_settings",
    # Application
    "APP_NAME",
    "APP_VERSION",
    # Environment
    "DEFAULT_ENVIRONMENT",
    # API
    "API_PREFIX",
    "OPENAPI_URL",
    "DOCS_URL",
    "REDOC_URL",
    # Pagination
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    # Logging
    "DEFAULT_LOG_LEVEL",
    # Headers
    "HEADER_REQUEST_ID",
    "HEADER_RESPONSE_TIME",
    # Health
    "STATUS_OK",
    "STATUS_READY",
    "STATUS_NOT_CONFIGURED",
    # Services
    "SERVICE_DATABASE",
    "SERVICE_REDIS",
    "SERVICE_LLM",
]
