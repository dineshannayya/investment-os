"""
Authentication schemas.

Request and response models for authentication APIs.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema

# =============================================================================
# Login
# =============================================================================


class LoginRequest(BaseSchema):
    """
    Login request.
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


# =============================================================================
# Refresh Token
# =============================================================================


class RefreshTokenRequest(BaseSchema):
    """
    Refresh access token request.
    """

    refresh_token: str = Field(
        min_length=1,
    )


# =============================================================================
# Token Response
# =============================================================================


class TokenData(BaseSchema):
    """
    Authentication tokens.
    """

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

    expires_in: int


# =============================================================================
# Authenticated User
# =============================================================================


class AuthenticatedUser(BaseSchema):
    """
    Authenticated user.
    """

    id: UUID

    email: EmailStr

    full_name: str | None = None

    is_active: bool

    is_superuser: bool

    email_verified: bool

    last_login: datetime | None = None


# =============================================================================
# Login Response
# =============================================================================


class LoginResponse(BaseSchema):
    """
    Login response payload.
    """

    tokens: TokenData

    user: AuthenticatedUser


# =============================================================================
# Refresh Response
# =============================================================================


class RefreshTokenResponse(BaseSchema):
    """
    Refresh token response payload.
    """

    access_token: str

    token_type: str = "bearer"

    expires_in: int
