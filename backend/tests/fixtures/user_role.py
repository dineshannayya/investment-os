"""
UserRole model fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.user_role import UserRole


@pytest.fixture
def user_role_factory(db_session, user_factory, role_factory):
    """
    Factory fixture for creating UserRole instances.

    Returns:
        Callable that creates and persists UserRole objects.
    """

    def _create(**kwargs) -> UserRole:
        user = kwargs.pop("user", None)
        role = kwargs.pop("role", None)
        assigned_by_user = kwargs.pop("assigned_by_user", None)

        if user is None:
            user = user_factory()

        if role is None:
            role = role_factory()

        if assigned_by_user is None and kwargs.get("assigned_by") is None:
            assigned_by = kwargs.pop("assigned_by", None)

        user_role = UserRole(
            user=user,
            role=role,
            assigned_by=(
                assigned_by_user.id
                if assigned_by_user is not None
                else kwargs.pop("assigned_by", None)
            ),
            assigned_at=kwargs.pop("assigned_at", datetime.now(UTC)),
            expires_at=kwargs.pop("expires_at", None),
            **kwargs,
        )

        db_session.add(user_role)
        db_session.commit()
        db_session.refresh(user_role)

        return user_role

    return _create


@pytest.fixture
def user_role(user_role_factory) -> UserRole:
    """
    Return a persisted default UserRole.
    """
    return user_role_factory()


@pytest.fixture
def expired_user_role(user_role_factory) -> UserRole:
    """
    Return an expired role assignment.
    """
    return user_role_factory(
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )


@pytest.fixture
def active_user_role(user_role_factory) -> UserRole:
    """
    Return an active role assignment.
    """
    return user_role_factory(
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
