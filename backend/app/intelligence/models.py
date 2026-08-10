"""
Models for Investment Intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID


# ============================================================================
# Document Metadata
# ============================================================================


@dataclass(slots=True, frozen=True)
class DocumentMetadata:
    """
    High-level metadata describing a processed document.
    """

    title: str

    document_type: str | None = None

    language: str | None = None

    page_count: int = 0

    sections: tuple[str, ...] = ()

    keywords: tuple[str, ...] = ()

    confidence: float = 1.0


# ============================================================================
# Investment Entities
# ============================================================================


@dataclass(slots=True, frozen=True)
class InvestmentEntities:
    """
    Named entities extracted from the document.
    """

    company_name: str | None = None

    founders: tuple[str, ...] = ()

    investors: tuple[str, ...] = ()

    accelerators: tuple[str, ...] = ()

    locations: tuple[str, ...] = ()

    sectors: tuple[str, ...] = ()

    products: tuple[str, ...] = ()

    technologies: tuple[str, ...] = ()

    confidence: float = 1.0


# ============================================================================
# Financial Metrics
# ============================================================================


@dataclass(slots=True, frozen=True)
class FinancialMetrics:
    """
    Financial information extracted from the document.
    """

    currency: str | None = None

    raise_amount: Decimal | None = None

    valuation: Decimal | None = None

    revenue: Decimal | None = None

    arr: Decimal | None = None

    ebitda: Decimal | None = None

    burn_rate: Decimal | None = None

    runway_months: int | None = None

    confidence: float = 1.0


# ============================================================================
# Investment Profile
# ============================================================================


@dataclass(slots=True, frozen=True)
class InvestmentProfile:
    """
    Consolidated investment intelligence for a document.
    """

    document_id: UUID

    metadata: DocumentMetadata

    entities: InvestmentEntities

    financials: FinancialMetrics

    extras: dict[str, Any] = field(default_factory=dict)

    confidence: float = 1.0
