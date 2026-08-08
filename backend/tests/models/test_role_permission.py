"""
Tests for RolePermission model.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.role_permission import RolePermission


class TestRolePermissionModel:
    """Tests for the RolePermission model."""

    def test_tablename(self) -> None:
        """Verify table name."""
        assert RolePermission.__tablename__ == "role_permissions"

    def test_create_role_permission(
        self,
        db_session,
        role_factory,
        permission_factory,
    ) -> None:
        """Create and persist a role-permission assignment."""

        role = role_factory()
        permission = permission_factory()

        assignment = RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.id is not None
        assert isinstance(assignment.id, uuid.UUID)

        assert assignment.role_id == role.id
        assert assignment.permission_id == permission.id
        assert assignment.granted_at is not None

    def test_granted_by(
        self,
        db_session,
        role_factory,
        permission_factory,
        user_factory,
    ) -> None:
        """Verify administrator tracking."""

        admin = user_factory(email="admin@example.com")
        role = role_factory()
        permission = permission_factory()

        assignment = RolePermission(
            role_id=role.id,
            permission_id=permission.id,
            granted_by=admin.id,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.granted_by == admin.id

    def test_relationships(
        self,
        db_session,
        role_factory,
        permission_factory,
    ) -> None:
        """Verify ORM relationships."""

        role = role_factory()
        permission = permission_factory()

        assignment = RolePermission(
            role=role,
            permission=permission,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.role.id == role.id
        assert assignment.permission.id == permission.id

    def test_unique_role_permission(
        self,
        db_session,
        role_factory,
        permission_factory,
    ) -> None:
        """A role cannot have the same permission twice."""

        role = role_factory()
        permission = permission_factory()

        db_session.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
        )
        db_session.commit()

        duplicate = RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )

        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_repr(
        self,
        role_factory,
        permission_factory,
    ) -> None:
        """Developer representation."""

        assignment = RolePermission(
            id=uuid.uuid4(),
            role_id=role_factory().id,
            permission_id=permission_factory().id,
        )

        text = repr(assignment)

        assert "RolePermission" in text
        assert str(assignment.role_id) in text
        assert str(assignment.permission_id) in text

    def test_factory(self, role_permission_factory) -> None:
        """Verify fixture factory."""

        assignment = role_permission_factory()

        assert assignment.id is not None
        assert assignment.role is not None
        assert assignment.permission is not None

    def test_fixture(self, role_permission) -> None:
        """Verify default fixture."""

        assert role_permission.id is not None
        assert role_permission.role is not None
        assert role_permission.permission is not None

    def test_timestamps(self, role_permission) -> None:
        """Timestamp mixin populates audit fields."""

        assert role_permission.created_at is not None
        assert role_permission.updated_at is not None
