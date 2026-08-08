"""
RolePermission model.

Represents assignment of a Permission to a Role.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class RolePermission(Base, UUIDMixin, TimestampMixin):
    """
    Role-to-Permission assignment.

    A role may contain multiple permissions.
    A permission may belong to multiple roles.

    The assignment itself is represented by this entity to support:

    * audit history
    * delegated administration
    * future policy extensions
    """

    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
        Index("ix_role_permissions_role_id", "role_id"),
        Index("ix_role_permissions_permission_id", "permission_id"),
    )

    # ------------------------------------------------------------------
    # Foreign Keys
    # ------------------------------------------------------------------

    role_id: Mapped[sa.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        doc="Role receiving the permission.",
    )

    permission_id: Mapped[sa.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Permission granted to the role.",
    )

    granted_by: Mapped[sa.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Administrator who granted the permission.",
    )

    # ------------------------------------------------------------------
    # Assignment Metadata
    # ------------------------------------------------------------------

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="Timestamp when the permission was granted.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="role_permissions",
        lazy="selectin",
    )

    permission: Mapped["Permission"] = relationship(
        "Permission",
        back_populates="role_permissions",
        lazy="selectin",
    )

    granted_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[granted_by],
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            "RolePermission("
            f"id={self.id!s}, "
            f"role_id={self.role_id!s}, "
            f"permission_id={self.permission_id!s})"
        )
