"""
RolePermission model fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.role_permission import RolePermission


@pytest.fixture
def role_permission_factory(
    db_session,
    role_factory,
    permission_factory,
):
    """
    Factory fixture for creating RolePermission instances.

    Returns:
        Callable that creates and persists RolePermission objects.
    """

    def _create(**kwargs) -> RolePermission:
        role = kwargs.pop("role", None)
        permission = kwargs.pop("permission", None)

        if role is None:
            role = role_factory()

        if permission is None:
            permission = permission_factory()

        role_permission = RolePermission(
            role=role,
            permission=permission,
            granted_by=kwargs.pop("granted_by", None),
            granted_at=kwargs.pop(
                "granted_at",
                datetime.now(UTC),
            ),
            **kwargs,
        )

        db_session.add(role_permission)
        db_session.commit()
        db_session.refresh(role_permission)

        return role_permission

    return _create


@pytest.fixture
def role_permission(role_permission_factory) -> RolePermission:
    """
    Return a persisted default RolePermission.
    """
    return role_permission_factory()
