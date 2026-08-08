"""
Tests for Permission model.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.permission import Permission


class TestPermissionModel:
    """Permission model tests."""

    def test_tablename(self) -> None:
        """Model uses expected table name."""
        assert Permission.__tablename__ == "permissions"

    def test_create_permission(self, db_session) -> None:
        """Create and persist a permission."""

        permission = Permission(
            name="startup:read",
            display_name="Read Startup",
            description="Allows viewing startup information.",
            resource="startup",
            action="read",
        )

        db_session.add(permission)
        db_session.commit()
        db_session.refresh(permission)

        assert permission.id is not None
        assert isinstance(permission.id, uuid.UUID)

        assert permission.name == "startup:read"
        assert permission.display_name == "Read Startup"
        assert permission.resource == "startup"
        assert permission.action == "read"
        assert permission.is_system is False

    def test_nullable_description(self, db_session) -> None:
        """Description may be omitted."""

        permission = Permission(
            name="startup:update",
            display_name="Update Startup",
            resource="startup",
            action="update",
        )

        db_session.add(permission)
        db_session.commit()

        assert permission.description is None

    @pytest.mark.parametrize(
        ("resource", "action"),
        [
            ("startup", "read"),
            ("startup", "create"),
            ("startup", "update"),
            ("startup", "delete"),
            ("investment", "approve"),
            ("user", "manage"),
        ],
    )
    def test_permission_pairs(
        self,
        db_session,
        resource,
        action,
    ) -> None:
        """Different resource/action combinations are valid."""

        permission = Permission(
            name=f"{resource}:{action}",
            display_name=f"{action.title()} {resource.title()}",
            resource=resource,
            action=action,
        )

        db_session.add(permission)
        db_session.commit()

        assert permission.resource == resource
        assert permission.action == action

    def test_unique_name(self, db_session) -> None:
        """Permission name must be unique."""

        db_session.add(
            Permission(
                name="startup:read",
                display_name="Read Startup",
                resource="startup",
                action="read",
            )
        )
        db_session.commit()

        duplicate = Permission(
            name="startup:read",
            display_name="Duplicate",
            resource="startup",
            action="read",
        )

        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_is_system_default(self, db_session) -> None:
        """Default system flag is False."""

        permission = Permission(
            name="system:test",
            display_name="System Test",
            resource="system",
            action="test",
        )

        db_session.add(permission)
        db_session.commit()

        assert permission.is_system is False

    def test_repr(self) -> None:
        """Developer representation."""

        permission = Permission(
            id=uuid.uuid4(),
            name="startup:read",
            display_name="Read Startup",
            resource="startup",
            action="read",
        )

        text = repr(permission)

        assert "Permission" in text
        assert "startup:read" in text
        assert "startup" in text
        assert "read" in text

    def test_created_updated_timestamps(self, db_session) -> None:
        """Timestamp mixin populates audit fields."""

        permission = Permission(
            name="document:upload",
            display_name="Upload Document",
            resource="document",
            action="upload",
        )

        db_session.add(permission)
        db_session.commit()

        assert permission.created_at is not None
        assert permission.updated_at is not None

    def test_permission_factory(self, permission_factory) -> None:
        """Fixture factory creates valid permission."""

        permission = permission_factory()

        assert permission.id is not None
        assert permission.name.startswith("startup:read:")
        assert permission.resource == "startup"
        assert permission.action == "read"
        
        assert permission.display_name.startswith("Startup Read")


    def test_permission_fixture(self, permission) -> None:
        """Fixture returns persisted permission."""

        assert permission.id is not None
        assert permission.name.startswith("startup:read:")
        assert permission.resource == "startup"
        assert permission.action == "read"
