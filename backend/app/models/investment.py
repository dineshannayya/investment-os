"""
Investment ORM model.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    InvestmentDecision,
    InvestmentStatus,
)
from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class Investment(
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Investment made (or evaluated) against a fundraising opportunity.
    """

    __tablename__ = "investments"

    #
    # Relationship
    #
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #
    # Decision
    #
    decision: Mapped[InvestmentDecision] = mapped_column(
        Enum(InvestmentDecision),
        nullable=False,
        default=InvestmentDecision.PENDING,
        index=True,
    )

    status: Mapped[InvestmentStatus] = mapped_column(
        Enum(InvestmentStatus),
        nullable=False,
        default=InvestmentStatus.DRAFT,
        index=True,
    )

    #
    # Investment Details
    #
    investment_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    ownership_target: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    expected_ownership: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    investment_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    #
    # Internal Tracking
    #
    investment_lead: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    committee_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    requires_followup: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    #
    # Notes
    #
    rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # Relationship
    #
    opportunity: Mapped[Opportunity] = relationship(
        back_populates="investments",
    )

    def __repr__(self) -> str:
        return (
            f"Investment("
            f"id={self.id}, "
            f"decision='{self.decision.value}', "
            f"status='{self.status.value}')"
        )

