"""
Unit tests for JWT utilities.
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_access_token,
    is_refresh_token,
)

# =============================================================================
# Access Token
# =============================================================================


def test_create_access_token_returns_string() -> None:
    """create_access_token() should return a JWT string."""

    token = create_access_token(subject="user-123")

    assert isinstance(token, str)
    assert token


def test_decode_access_token() -> None:
    """Access token should decode successfully."""

    token = create_access_token(subject="user-123")

    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"

    assert "iat" in payload
    assert "exp" in payload


def test_access_token_identification() -> None:
    """Access token should be identified correctly."""

    payload = decode_token(
        create_access_token(subject="user-123")
    )

    assert is_access_token(payload)
    assert not is_refresh_token(payload)


# =============================================================================
# Refresh Token
# =============================================================================


def test_create_refresh_token_returns_string() -> None:
    """create_refresh_token() should return a JWT string."""

    token = create_refresh_token(subject="user-123")

    assert isinstance(token, str)
    assert token


def test_decode_refresh_token() -> None:
    """Refresh token should decode successfully."""

    token = create_refresh_token(subject="user-123")

    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"


def test_refresh_token_identification() -> None:
    """Refresh token should be identified correctly."""

    payload = decode_token(
        create_refresh_token(subject="user-123")
    )

    assert is_refresh_token(payload)
    assert not is_access_token(payload)


# =============================================================================
# Additional Claims
# =============================================================================


def test_access_token_additional_claims() -> None:
    """Additional claims should be preserved."""

    token = create_access_token(
        subject="user-123",
        additional_claims={
            "role": "admin",
            "tenant": "investment-os",
        },
    )

    payload = decode_token(token)

    assert payload["role"] == "admin"
    assert payload["tenant"] == "investment-os"


# =============================================================================
# Expiration
# =============================================================================


def test_expired_access_token() -> None:
    """Expired access token should raise ExpiredSignatureError."""

    token = create_access_token(
        subject="user-123",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


# =============================================================================
# Invalid Tokens
# =============================================================================


def test_invalid_token() -> None:
    """Malformed JWT should raise InvalidTokenError."""

    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not-a-valid-token")


def test_corrupted_token() -> None:
    """Corrupted JWT signature should fail validation."""

    token = create_access_token(subject="user-123")
    
    parts = token.split(".")
    
    parts[2] = "invalid-signature"
    
    corrupted = ".".join(parts)
    
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(corrupted)


# =============================================================================
# Subject Round Trip
# =============================================================================


@pytest.mark.parametrize(
    "subject",
    [
        "1",
        "123",
        "user-123",
        "550e8400-e29b-41d4-a716-446655440000",
        "admin@example.com",
    ],
)
def test_subject_roundtrip(subject: str) -> None:
    """JWT subject should survive encode/decode."""

    token = create_access_token(subject=subject)

    payload = decode_token(token)

    assert payload["sub"] == subject


# =============================================================================
# Token Types
# =============================================================================


def test_access_and_refresh_tokens_are_different() -> None:
    """Access and refresh tokens should carry different types."""

    access = decode_token(
        create_access_token(subject="user-123")
    )

    refresh = decode_token(
        create_refresh_token(subject="user-123")
    )

    assert access["type"] == "access"
    assert refresh["type"] == "refresh"
