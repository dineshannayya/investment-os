"""
JWT utilities.

Provides helpers for creating and validating JSON Web Tokens (JWT).

This module is intentionally independent of FastAPI and the database
layer so it can be reused by APIs, CLI tools, background workers,
and future services.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings

CLAIM_SUBJECT = "sub"
CLAIM_TYPE = "type"
CLAIM_ISSUER = "iss"
CLAIM_ISSUED_AT = "iat"
CLAIM_EXPIRATION = "exp"


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:
            Unique subject (typically the user ID).

        expires_delta:
            Optional expiration override.

        additional_claims:
            Optional custom JWT claims.

    Returns:
        Encoded JWT.
    """

    now = datetime.now(UTC)

    expire = now + expires_delta

    payload: dict[str, Any] = {
        CLAIM_SUBJECT    : subject,
        CLAIM_TYPE       : token_type,
        CLAIM_ISSUED_AT  : now,
        CLAIM_EXPIRATION : expire,
        CLAIM_ISSUER     : settings.jwt_issuer,
    }

    if additional_claims:
        for reserved in ("sub", "exp", "iat", "type", "iss"):
            additional_claims.pop(reserved, None)

        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:
            Unique subject (typically the user ID).

        expires_delta:
            Optional expiration override.

        additional_claims:
            Optional custom JWT claims.

    Returns:
        Encoded JWT.
    """
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=( 
            expires_delta 
            or 
            timedelta( 
                minutes=settings.jwt_access_token_expire_minutes,
            )
        ),
        additional_claims=additional_claims,
    )

def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT refresh token.
    """

    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=( expires_delta or timedelta( days=settings.jwt_refresh_token_expire_days,)),
    )


def decode_token(
    token: str,
) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Args:
        token:
            Encoded JWT.

    Returns:
        Decoded payload.

    Raises:
        jwt.InvalidTokenError
            If the token is invalid or expired.
    """

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={
            "require": ["sub", "exp", "iat", "type"],
        },
    )



def is_access_token(
    payload: dict[str, Any],
) -> bool:
    """
    Return True if payload represents an access token.
    """

    return payload.get("type") == "access"


def is_refresh_token(
    payload: dict[str, Any],
) -> bool:
    """
    Return True if payload represents a refresh token.
    """

    return payload.get("type") == "refresh"
