"""
Tests for UserRole model.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user_role import UserRole


class TestUserRoleModel:
    """Tests for the UserRole model."""

    def test_tablename(self) -> None:
        """Verify table name."""
        assert UserRole.__tablename__ == "user_roles"

    def test_create_user_role(
        self,
        db_session,
        user_factory,
        role_factory,
    ) -> None:
        """Create and persist a user-role assignment."""

        user = user_factory()
        role = role_factory()

        assignment = UserRole(
            user_id=user.id,
            role_id=role.id,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.id is not None
        assert isinstance(assignment.id, uuid.UUID)

        assert assignment.user_id == user.id
        assert assignment.role_id == role.id
        assert assignment.assigned_at is not None
        assert assignment.expires_at is None

    def test_assigned_by(
        self,
        db_session,
        user_factory,
        role_factory,
    ) -> None:
        """Verify administrator assignment."""

        user = user_factory(email="user@example.com")
        admin = user_factory(email="admin@example.com")
        role = role_factory()

        assignment = UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_by=admin.id,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.assigned_by == admin.id

    def test_expires_at(
        self,
        db_session,
        user_factory,
        role_factory,
    ) -> None:
        """Verify expiry timestamp."""

        expiry = datetime.now(UTC) + timedelta(days=30)

        assignment = UserRole(
            user_id=user_factory().id,
            role_id=role_factory().id,
            expires_at=expiry,
        )

        db_session.add(assignment)
        db_session.commit()

        assert assignment.expires_at == expiry

    def test_relationships(
        self,
        db_session,
        user_factory,
        role_factory,
    ) -> None:
        """Verify ORM relationships."""

        user = user_factory()
        role = role_factory()

        assignment = UserRole(
            user=user,
            role=role,
        )

        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)

        assert assignment.user.id == user.id
        assert assignment.role.id == role.id

    def test_unique_user_role(
        self,
        db_session,
        user_factory,
        role_factory,
    ) -> None:
        """A user cannot have the same role twice."""

        user = user_factory()
        role = role_factory()

        db_session.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )
        db_session.commit()

        duplicate = UserRole(
            user_id=user.id,
            role_id=role.id,
        )

        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_repr(
        self,
        user_factory,
        role_factory,
    ) -> None:
        """Developer representation."""

        assignment = UserRole(
            id=uuid.uuid4(),
            user_id=user_factory().id,
            role_id=role_factory().id,
        )

        text = repr(assignment)

        assert "UserRole" in text
        assert str(assignment.user_id) in text
        assert str(assignment.role_id) in text

    def test_factory(self, user_role_factory) -> None:
        """Verify fixture factory."""

        assignment = user_role_factory()

        assert assignment.id is not None
        assert assignment.user is not None
        assert assignment.role is not None

    def test_fixture(self, user_role) -> None:
        """Verify default fixture."""

        assert user_role.id is not None
        assert user_role.user is not None
        assert user_role.role is not None

    def test_timestamps(
        self,
        user_role,
    ) -> None:
        """Timestamp mixin populates audit fields."""

        assert user_role.created_at is not None
        assert user_role.updated_at is not None
