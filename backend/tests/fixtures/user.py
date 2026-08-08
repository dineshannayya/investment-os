"""
User model fixtures.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.security.password import hash_password
from app.models.user import User


@pytest.fixture
def user_factory(db_session):
    """
    Factory fixture for creating User instances.
    """

    def _create(**kwargs) -> User:
        unique = uuid.uuid4().hex[:8]

        user = User(
            email=kwargs.pop("email", f"user-{unique}@example.com"),
            full_name=kwargs.pop("full_name", "Test User"),
            password_hash=kwargs.pop(
                "password_hash",
                hash_password("Password123!"),
            ),
            is_active=kwargs.pop("is_active", True),
            is_superuser=kwargs.pop("is_superuser", False),
            email_verified=kwargs.pop("email_verified", False),
            last_login=kwargs.pop("last_login", None),
            **kwargs,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        return user

    return _create


@pytest.fixture
def user(user_factory) -> User:
    """
    Return a persisted default user.
    """
    return user_factory()


@pytest.fixture
def admin_user(user_factory) -> User:
    """
    Return a persisted administrator.
    """
    return user_factory(
        email="admin@example.com",
        full_name="Administrator",
        is_superuser=True,
        email_verified=True,
    )


@pytest.fixture
def inactive_user(user_factory) -> User:
    """
    Return a persisted inactive user.
    """
    return user_factory(
        is_active=False,
    )


@pytest.fixture
def verified_user(user_factory) -> User:
    """
    Return a persisted verified user.
    """
    return user_factory(
        email_verified=True,
    )
