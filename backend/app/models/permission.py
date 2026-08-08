"""
Permission model.

Represents a single application permission that can be assigned
to one or more roles through RolePermission.

Examples:
    startup:read
    startup:create
    investment:approve
    user:manage
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class Permission(Base, UUIDMixin, TimestampMixin):
    """
    Permission entity.

    A permission represents a single action that may be granted to
    one or more roles.

    Examples
    --------
    startup:read
    startup:update
    investment:approve
    user:manage
    """

    __tablename__ = "permissions"

    # ------------------------------------------------------------------
    # Core Information
    # ------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique permission name (e.g. startup:read).",
    )

    display_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Human-readable permission name.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional permission description.",
    )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    resource: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        doc="Protected resource (startup, investment, user, etc.).",
    )

    action: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        doc="Allowed action (read, create, update, delete, etc.).",
    )

    # ------------------------------------------------------------------
    # Flags
    # ------------------------------------------------------------------

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
        doc="True if this permission is system-defined.",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"Permission("
            f"id={self.id!s}, "
            f"name='{self.name}', "
            f"resource='{self.resource}', "
            f"action='{self.action}')"
        )
