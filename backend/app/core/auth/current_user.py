"""
Current user dependencies.

FastAPI dependencies for resolving the authenticated user.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.auth.dependencies import get_auth_service
from app.core.auth.oauth2 import oauth2_scheme
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
)
from app.core.security.jwt import (
    CLAIM_SUBJECT,
    decode_token,
)
from app.models.user import User
from app.services.auth_service import AuthService


# =============================================================================
# Current User
# =============================================================================


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> User:
    """
    Return the authenticated user.
    """

    payload = decode_token(token)

    subject = payload.get(CLAIM_SUBJECT)

    if subject is None:
        raise AuthenticationException("Invalid authentication token")

    user = auth_service.get_current_user(
        UUID(subject),
    )

    if user is None:
        raise AuthenticationException("User not found")

    return user


# =============================================================================
# Active User
# =============================================================================


def get_current_active_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """
    Return the current active user.
    """

    if not current_user.is_active:
        raise AuthorizationException(
            "User account is inactive",
        )

    return current_user


# =============================================================================
# Superuser
# =============================================================================


def get_current_superuser(
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> User:
    """
    Return the current superuser.
    """

    if not current_user.is_superuser:
        raise AuthorizationException(
            "Administrator privileges required",
        )

    return current_user


# =============================================================================
# Public Exports
# =============================================================================


__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
]

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]


