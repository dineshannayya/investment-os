"""
Permission model fixtures.
"""

from __future__ import annotations

import pytest

from app.models.permission import Permission


@pytest.fixture
def permission_factory(db_session):
    """
    Factory fixture for creating Permission instances.

    Returns:
        Callable that creates and persists Permission objects.
    """

    def _create(**kwargs) -> Permission:
        permission = Permission(
            name=kwargs.pop("name", "startup:read"),
            display_name=kwargs.pop("display_name", "Read Startup"),
            description=kwargs.pop(
                "description",
                "Allows reading startup information.",
            ),
            resource=kwargs.pop("resource", "startup"),
            action=kwargs.pop("action", "read"),
            is_system=kwargs.pop("is_system", False),
            **kwargs,
        )

        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)

        return permission

    return _create


@pytest.fixture
def permission(permission_factory) -> Permission:
    """
    Return a persisted default permission.
    """
    return permission_factory()
