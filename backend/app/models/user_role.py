"""
UserRole model.

Represents assignment of a Role to a User.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class UserRole(Base, UUIDMixin, TimestampMixin):
    """
    User-to-Role assignment.

    A user may have multiple roles.
    A role may be assigned to multiple users.

    The assignment itself is represented by this entity to support:

    * audit history
    * temporary role assignments
    * administrator tracking
    """

    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_id",
            name="uq_user_roles_user_role",
        ),
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
        Index("ix_user_roles_expires_at", "expires_at"),
    )

    # ------------------------------------------------------------------
    # Foreign Keys
    # ------------------------------------------------------------------

    user_id: Mapped[sa.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User receiving the role.",
    )

    role_id: Mapped[sa.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        doc="Assigned role.",
    )

    assigned_by: Mapped[sa.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Administrator who assigned the role.",
    )

    # ------------------------------------------------------------------
    # Assignment Metadata
    # ------------------------------------------------------------------

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="Timestamp when the role was assigned.",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional role expiry timestamp.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_roles",
        lazy="selectin",
    )

    assigned_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by],
        lazy="selectin",
    )


    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            "UserRole("
            f"id={self.id!s}, "
            f"user_id={self.user_id!s}, "
            f"role_id={self.role_id!s})"
        )
