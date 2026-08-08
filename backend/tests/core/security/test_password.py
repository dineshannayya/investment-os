"""
Unit tests for password hashing utilities.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import app.core.security.password as password_module
from app.core.security.password import (
    hash_password,
    needs_rehash,
    verify_password,
)

# =============================================================================
# Password Hashing
# =============================================================================


def test_hash_password_returns_string() -> None:
    """hash_password() should return a string."""

    password_hash = hash_password("secret123")

    assert isinstance(password_hash, str)
    assert password_hash


def test_hash_password_not_equal_plaintext() -> None:
    """Password hash should not equal the original password."""

    password = "secret123"

    password_hash = hash_password(password)

    assert password_hash != password


def test_hash_password_is_non_deterministic() -> None:
    """
    Hashing the same password twice should produce different hashes.

    Modern password hashing algorithms use a random salt.
    """

    password = "secret123"

    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2


# =============================================================================
# Password Verification
# =============================================================================


def test_verify_password_success() -> None:
    """Correct password should verify successfully."""

    password = "secret123"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_failure() -> None:
    """Incorrect password should fail verification."""

    password_hash = hash_password("secret123")

    assert verify_password("wrong-password", password_hash) is False


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.parametrize(
    "password",
    [
        "",
        "a",
        "password",
        "correct horse battery staple",
        "P@ssw0rd!",
        "日本語パスワード",
        "🔐SecurePassword123!",
    ],
)
def test_hash_and_verify_various_passwords(password: str) -> None:
    """Hashing and verification should work for different password values."""

    password_hash = hash_password(password)

    assert verify_password(password, password_hash)


def test_verify_invalid_hash_returns_false() -> None:
    """
    Verifying against an invalid hash should fail gracefully.
    """

    assert (
        verify_password(
            "secret123",
            "this-is-not-a-valid-password-hash",
        )
        is False
    )


def test_needs_rehash_true(monkeypatch):
    mock = MagicMock()
    mock.verify_and_update.return_value = (
        True,
        "new-hash",
    )

    monkeypatch.setattr(
        password_module,
        "_password_hash",
        mock,
    )

    assert needs_rehash("old-hash") is True
