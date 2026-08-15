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
from app.core.config.api import (
    API_PREFIX,
    DEFAULT_PAGE_SIZE,
    DOCS_URL,
    HEADER_REQUEST_ID,
    HEADER_RESPONSE_TIME,
    MAX_PAGE_SIZE,
    OPENAPI_URL,
    REDOC_URL,
)
from app.core.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENVIRONMENT,
    SERVICE_DATABASE,
    SERVICE_LLM,
    SERVICE_REDIS,
    STATUS_NOT_CONFIGURED,
    STATUS_OK,
    STATUS_READY,
)
from app.core.config.error_codes import ErrorCode
from app.core.config.logging import (
    DEFAULT_LOG_LEVEL,
    LOGGER_NAME,
)
from app.core.config.settings import (
    LLMProviderType,
    Settings,
    get_settings,
    settings,
)
from app.core.config.status_codes import (
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_CREATED,
    HTTP_FORBIDDEN,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_UNAUTHORIZED,
    HTTP_UNPROCESSABLE_ENTITY,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    "get_settings",
    "LLMProviderType",
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
    # Headers
    "HEADER_REQUEST_ID",
    "HEADER_RESPONSE_TIME",
    # Logging
    "LOGGER_NAME",
    "DEFAULT_LOG_LEVEL",
    # Error Codes
    "ErrorCode",
    # Health
    "STATUS_OK",
    "STATUS_READY",
    "STATUS_NOT_CONFIGURED",
    # Services
    "SERVICE_DATABASE",
    "SERVICE_REDIS",
    "SERVICE_LLM",
    # HTTP
    "HTTP_OK",
    "HTTP_CREATED",
    "HTTP_BAD_REQUEST",
    "HTTP_UNAUTHORIZED",
    "HTTP_FORBIDDEN",
    "HTTP_NOT_FOUND",
    "HTTP_CONFLICT",
    "HTTP_UNPROCESSABLE_ENTITY",
    "HTTP_INTERNAL_SERVER_ERROR",
    "HTTP_SERVICE_UNAVAILABLE",
]
