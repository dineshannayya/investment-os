"""
Password hashing utilities.

This module provides password hashing and verification helpers for
authentication. The underlying hashing implementation is intentionally
hidden from the rest of the application.
"""

from __future__ import annotations

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

# Singleton password hasher
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password.

    Args:
        password:
            Plain-text password.

    Returns:
        Encoded password hash.
    """
    return _password_hash.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a password against a stored hash.

    Returns:
        True if the password matches.

        False if the password is incorrect or the stored
        password hash is invalid or unsupported.
    """
    try:
        return _password_hash.verify(password, password_hash)

    except UnknownHashError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """
    Determine whether a stored password hash should be upgraded.

    Returns:
        True if the hash should be regenerated using the current
        recommended algorithm.
    """
    return (
        _password_hash.verify_and_update(
            "dummy",
            password_hash,
        )[1]
        is not None
    )
