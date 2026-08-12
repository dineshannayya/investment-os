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

    secondary_document_types: tuple[str, ...] = ()

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

    #
    # Funding
    # 
    raise_amount: Decimal | None = None
    valuation: Decimal | None = None

    #
    # Business performance
    #
    revenue: Decimal | None = None
    arr: Decimal | None = None
    ebitda: Decimal | None = None
    margin: Decimal | None = None

    #
    # Cash
    #
    burn_rate: Decimal | None = None
    runway_months: int | None = None

    confidence: float = 1.0


# ============================================================================
# Investment Profile
# ============================================================================
@dataclass(slots=True, frozen=True)
class InvestmentSignals:
    """
    Investment-specific signals inferred from the document.
    """

    #
    # Company maturity
    #
    stage: str | None = None

    #
    # Business
    #
    industry: tuple[str, ...] = ()

    business_models: tuple[str, ...] = ()

    #
    # Technology
    #
    technologies: tuple[str, ...] = ()

    #
    # Customers
    #
    markets: tuple[str, ...] = ()

    #
    # Geography
    #
    geographies: tuple[str, ...] = ()

    #
    # Investment themes
    #
    themes: tuple[str, ...] = ()

    confidence: float = 1.0

@dataclass(slots=True, frozen=True)
class RiskAssessment:
    """
    Investment risks inferred from the document.
    """

    #
    # Founder
    #
    founder_risks: tuple[str, ...] = ()

    #
    # Financial
    #
    financial_risks: tuple[str, ...] = ()

    #
    # Execution
    #
    execution_risks: tuple[str, ...] = ()

    #
    # Market
    #
    market_risks: tuple[str, ...] = ()

    #
    # Technology
    #
    technology_risks: tuple[str, ...] = ()

    #
    # Legal / Regulatory
    #
    legal_risks: tuple[str, ...] = ()

    confidence: float = 1.0


@dataclass(slots=True, frozen=True)
class InvestmentProfile:
    """
    Consolidated investment intelligence for a document.
    """

    document_id: UUID

    metadata: DocumentMetadata

    entities: InvestmentEntities

    financials: FinancialMetrics

    signals: investmentSignals = field( default_factory=InvestmentSignals,)

    risks: RiskAssessment = field( default_factory=RiskAssessment,)

    extras: dict[str, Any] = field(default_factory=dict)

    confidence: float = 1.0


