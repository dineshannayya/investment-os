"""
Startup ORM model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import StartupStage, StartupStatus
from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.founder import Founder
    from app.models.opportunity import Opportunity


class Startup(
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Startup entity.
    """

    __tablename__ = "startups"

    #
    # Company Information
    #
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Business Information
    #
    sector: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    stage: Mapped[StartupStage] = mapped_column(
        Enum(StartupStage),
        nullable=False,
        default=StartupStage.IDEA,
    )

    founded_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    headquarters: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[StartupStatus] = mapped_column(
        Enum(StartupStatus),
        default=StartupStatus.ACTIVE,
        nullable=False,
        index=True,
    )


    #
    # Relationships
    #
    founders: Mapped[list[Founder]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan",
    )

    opportunities: Mapped[list[Opportunity]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan",
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="startup",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Startup("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"stage='{self.stage.value}')"
        )
