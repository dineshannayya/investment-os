"""
User model.

Stores application users for authentication and authorization.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import (
    TimestampMixin,
    UUIDMixin,
)


class User(Base, UUIDMixin, TimestampMixin):
    """
    Application user.
    """

    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default=sa.true(),
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=sa.false(),
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=sa.false(),
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"User("
            f"id={self.id!r}, "
            f"email={self.email!r}, "
            f"is_active={self.is_active!r}"
            f")"
        )
