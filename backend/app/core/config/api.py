# --------------------------------------------------
#  Reason:
#
#  These constants are used by:
#      FastAPI initialization
#      API routers
#      Middleware
#      ResponseFactory
#      Pagination
#      OpenAPI configuration
#  They are all API-framework concerns.
# ---------------------------------------------------

from typing import Final

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
# HTTP Headers
# =============================================================================

HEADER_REQUEST_ID: Final[str] = "X-Request-ID"
HEADER_RESPONSE_TIME: Final[str] = "X-Response-Time"
