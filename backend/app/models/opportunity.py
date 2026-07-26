"""
Opportunity ORM model.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    InvestmentInstrument,
    OpportunityStatus,
)
from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.investment import Investment
    from app.models.startup import Startup


class Opportunity(
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Startup fundraising opportunity.
    """

    __tablename__ = "opportunities"

    #
    # Relationship
    #
    startup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #
    # Round Information
    #
    round_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    instrument: Mapped[InvestmentInstrument] = mapped_column(
        Enum(InvestmentInstrument),
        nullable=False,
    )

    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus),
        nullable=False,
        default=OpportunityStatus.OPEN,
        index=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    #
    # Fund Raise
    #
    target_raise: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    minimum_ticket: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    valuation_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    pre_money_valuation: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    post_money_valuation: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    committed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    soft_committed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    #
    # Timeline
    #
    open_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    close_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    #
    # Investment Notes
    #
    investment_thesis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    risk_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    analyst_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Relationships
    #
    startup: Mapped[Startup] = relationship(
        back_populates="opportunities",
    )

    investments: Mapped[list[Investment]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Opportunity("
            f"id={self.id}, "
            f"round='{self.round_name}', "
            f"status='{self.status.value}')"
        )
