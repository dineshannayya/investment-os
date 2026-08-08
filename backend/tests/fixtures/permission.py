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
    import uuid

    def _create(**kwargs) -> Permission:
        suffix = uuid.uuid4().hex[:8]
        permission = Permission(
            name=kwargs.pop(
                "name",
                f"startup:read:{suffix}",
            ),
            display_name=kwargs.pop(
                "display_name",
                f"Startup Read {suffix}",
            ),
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
