"""
Founder ORM model.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import FounderRole
from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.startup import Startup


class Founder(
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Founder information for a startup.
    """

    __tablename__ = "founders"

    #
    # Relationship
    #
    startup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #
    # Personal Information
    #
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    designation: Mapped[FounderRole] = mapped_column(
        Enum(FounderRole),
        nullable=False,
        default=FounderRole.OTHER,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    #
    # Professional Background
    #
    experience_years: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    education: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    previous_companies: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Ownership
    #
    ownership_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    is_primary_contact: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
    )

    #
    # Notes
    #
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Relationships
    #
    startup: Mapped[Startup] = relationship(
        back_populates="founders",
    )

    def __repr__(self) -> str:
        return (
            f"Founder("
            f"id={self.id}, "
            f"name='{self.full_name}', "
            f"designation='{self.designation.value}')"
        )
