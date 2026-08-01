"""
HTTP status codes used by Investment OS.

Centralizes the HTTP status codes used by the application.
"""

from http import HTTPStatus
from typing import Final

# =============================================================================
# Success
# =============================================================================

HTTP_OK: Final[int] = HTTPStatus.OK
HTTP_CREATED: Final[int] = HTTPStatus.CREATED
HTTP_ACCEPTED: Final[int] = HTTPStatus.ACCEPTED
HTTP_NO_CONTENT: Final[int] = HTTPStatus.NO_CONTENT

# =============================================================================
# Client Errors
# =============================================================================

HTTP_BAD_REQUEST: Final[int] = HTTPStatus.BAD_REQUEST
HTTP_UNAUTHORIZED: Final[int] = HTTPStatus.UNAUTHORIZED
HTTP_FORBIDDEN: Final[int] = HTTPStatus.FORBIDDEN
HTTP_NOT_FOUND: Final[int] = HTTPStatus.NOT_FOUND
HTTP_CONFLICT: Final[int] = HTTPStatus.CONFLICT
HTTP_UNPROCESSABLE_ENTITY: Final[int] = HTTPStatus.UNPROCESSABLE_ENTITY
HTTP_TOO_MANY_REQUESTS: Final[int] = HTTPStatus.TOO_MANY_REQUESTS

# =============================================================================
# Server Errors
# =============================================================================

HTTP_INTERNAL_SERVER_ERROR: Final[int] = HTTPStatus.INTERNAL_SERVER_ERROR
HTTP_NOT_IMPLEMENTED: Final[int] = HTTPStatus.NOT_IMPLEMENTED
HTTP_BAD_GATEWAY: Final[int] = HTTPStatus.BAD_GATEWAY
HTTP_SERVICE_UNAVAILABLE: Final[int] = HTTPStatus.SERVICE_UNAVAILABLE
HTTP_GATEWAY_TIMEOUT: Final[int] = HTTPStatus.GATEWAY_TIMEOUT
