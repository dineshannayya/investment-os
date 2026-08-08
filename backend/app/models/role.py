"""
Role ORM model.

Represents an authorization role used by the RBAC system.

Examples:
    - administrator
    - investment_manager
    - reviewer
    - analyst
    - viewer
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column
import sqlalchemy as sa

from app.models.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Role(Base, UUIDMixin, TimestampMixin):
    """Role model."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique internal role name.",
    )

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable role name.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional description of the role.",
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
        doc="True for built-in roles that cannot be removed.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    #
    # Added in Sprint 2.3A.3
    #
    # user_roles
    # role_permissions
    #

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            f"Role("
            f"name='{self.name}', "
            f"display_name='{self.display_name}', "
            f"is_system={self.is_system}"
            f")"
        )
