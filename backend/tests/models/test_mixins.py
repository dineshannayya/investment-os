# ------------------------------------------
# | Mixin               |     Tests |
# | ------------------- | --------: |
# | TimestampMixin      |         6 |
# | UUIDMixin           |         3 |
# | SoftDeleteMixin     |         3 |
# | AuditMixin          |         2 |
# | Generic inheritance |       4–8 |
# | **Total**           | **18–22** |
# ------------------------------------------------ 


"""
Reusable SQLAlchemy ORM mixins.

These mixins provide common fields and behaviors shared across
multiple ORM models.

Mixins:
    - UUIDMixin
    - TimestampMixin
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import UUID, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """
    UUID primary key mixin.

    Provides:
        id : UUID

    Example:
        id = 6f1b0e4b-68db-4d57-89fe-52d3c2d5ef93
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        index=True,
    )


class TimestampMixin:
    """
    Timestamp tracking mixin.

    Fields:
        created_at
        updated_at

    Both timestamps are stored in UTC.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )



def test_timestamp_columns_exist(startup_factory):

    startup = startup_factory()

    assert hasattr(startup, "created_at")
    assert hasattr(startup, "updated_at")


def test_created_at_is_datetime(startup_factory):

    startup = startup_factory()

    assert isinstance(startup.created_at, datetime)

def test_updated_at_is_datetime(startup_factory):

    startup = startup_factory()

    assert isinstance(startup.updated_at, datetime)


def test_created_at_initialized(startup_factory):

    startup = startup_factory()

    assert startup.created_at is not None

def test_updated_at_initialized(startup_factory):

    startup = startup_factory()

    assert startup.updated_at is not None


#def test_updated_at_changes(
#    startup_factory,
#    db_session,
#):
#
#    startup = startup_factory()
#
#    old = startup.updated_at
#
#    startup.name = "New Name"
#
#    db_session.flush()
#    db_session.refresh(startup)
#
#    assert startup.updated_at >= old

from uuid import UUID


def test_uuid_is_generated(startup_factory):

    startup = startup_factory()

    assert startup.id is not None

def test_uuid_type(startup_factory):

    startup = startup_factory()

    assert isinstance(startup.id, UUID)


def test_uuid_unique(
    startup_factory,
):

    a = startup_factory()

    b = startup_factory()

    assert a.id != b.id


#def test_default_not_deleted(startup_factory):
#
#    startup = startup_factory()
#
#    assert startup.is_deleted is False



def test_soft_delete(startup_factory):

    startup = startup_factory()

    startup.is_deleted = True
    startup.deleted_at = datetime.utcnow()

    assert startup.is_deleted

    assert startup.deleted_at is not None

#def test_created_by_exists(startup_factory):
#
#    startup = startup_factory()
#
#    assert hasattr(startup, "created_by")


