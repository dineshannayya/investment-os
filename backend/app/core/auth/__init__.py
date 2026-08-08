"""
Authentication module.

Provides OAuth2 authentication, dependency injection,
and current-user resolution for protected API endpoints.
"""

from app.core.auth.current_user import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
)
from app.core.auth.dependencies import (
    get_auth_service,
    get_user_repository,
)
from app.core.auth.oauth2 import oauth2_scheme

__all__ = [
    # OAuth2
    "oauth2_scheme",
    # Dependencies
    "get_user_repository",
    "get_auth_service",
    # Current User
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
]
