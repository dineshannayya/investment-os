"""
Tests for Role ORM model.

Coverage
--------
- ORM metadata
- Defaults
- Factory
- UUID/Audit fields
- Persistence
- Updates
- Representation
"""

from __future__ import annotations

from uuid import UUID

from app.models import Role


# =============================================================================
# Section 1 — ORM Metadata
# =============================================================================


def test_tablename() -> None:
    assert Role.__tablename__ == "roles"


def test_primary_key() -> None:
    assert Role.__table__.c.id.primary_key


def test_name_column_exists() -> None:
    assert "name" in Role.__table__.columns


def test_display_name_column_exists() -> None:
    assert "display_name" in Role.__table__.columns


def test_description_column_exists() -> None:
    assert "description" in Role.__table__.columns


def test_is_system_column_exists() -> None:
    assert "is_system" in Role.__table__.columns


def test_created_at_exists() -> None:
    assert "created_at" in Role.__table__.columns


def test_updated_at_exists() -> None:
    assert "updated_at" in Role.__table__.columns


# =============================================================================
# Section 2 — Factory
# =============================================================================


def test_factory(role_factory) -> None:
    role = role_factory()

    assert role is not None


def test_factory_default_values(role) -> None:
    assert role.name is not None
    assert role.display_name is not None


# =============================================================================
# Section 3 — Defaults
# =============================================================================


def test_default_is_system(role) -> None:
    assert role.is_system is False


# =============================================================================
# Section 4 — UUID / Audit
# =============================================================================


def test_uuid(role) -> None:
    assert isinstance(role.id, UUID)


def test_created_at(role) -> None:
    assert role.created_at is not None


def test_updated_at(role) -> None:
    assert role.updated_at is not None


# =============================================================================
# Section 5 — Persistence
# =============================================================================


def test_insert(
    db_session,
    role,
) -> None:
    db_session.flush()

    assert role.id is not None


def test_query(
    db_session,
    role,
) -> None:
    found = db_session.get(
        Role,
        role.id,
    )

    assert found == role


# =============================================================================
# Section 6 — Update
# =============================================================================


def test_update_description(
    db_session,
    role,
) -> None:
    role.description = "Updated description"

    db_session.flush()

    assert role.description == "Updated description"


# =============================================================================
# Section 7 — Representation
# =============================================================================


def test_repr(role_factory) -> None:
    role = role_factory(
        name="administrator",
        display_name="Administrator",
    )

    result = repr(role)

    assert "Role(" in result
    assert "administrator" in result
    assert "Administrator" in result
