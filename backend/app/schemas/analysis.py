"""
Startup analysis schemas.

This module defines the input, derived metrics, evidence,
and qualitative output structures used by the startup
analysis pipeline.

The schemas intentionally do not contain investment scoring
or final investment decisions. Those belong to later stages.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

class AnalysisBase(BaseModel):
    """Base configuration for analysis schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class CompanyAnalysis(AnalysisBase):
    """Basic company information used during analysis."""

    name: str
    description: str | None = None
    industry: str | None = None
    sector: str | None = None
    stage: str | None = None
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    headquarters: str | None = None


# ---------------------------------------------------------------------------
# Founder
# ---------------------------------------------------------------------------

class FounderAnalysis(AnalysisBase):
    """Founder information relevant to investment analysis."""

    founder_id: UUID | None = None
    name: str
    role: str | None = None

    background: str | None = None
    relevant_experience: str | None = None

    previous_startups: int | None = Field(default=None, ge=0)
    previous_exits: int | None = Field(default=None, ge=0)

    analysis_notes: str | None = None


# ---------------------------------------------------------------------------
# Product / Problem
# ---------------------------------------------------------------------------

class ProductAnalysis(AnalysisBase):
    """Product and problem assessment inputs."""

    problem: str | None = None
    solution: str | None = None
    product_description: str | None = None

    target_customer: str | None = None
    value_proposition: str | None = None

    product_stage: str | None = None
    technology: str | None = None
    differentiation: str | None = None


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

class MarketAnalysis(AnalysisBase):
    """Market information available for analysis."""

    market_description: str | None = None

    tam: Decimal | None = Field(default=None, ge=0)
    sam: Decimal | None = Field(default=None, ge=0)
    som: Decimal | None = Field(default=None, ge=0)

    market_growth_rate: Decimal | None = None

    geographic_market: str | None = None

    competitors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Traction
# ---------------------------------------------------------------------------

class TractionAnalysis(AnalysisBase):
    """Business traction information."""

    revenue: Decimal | None = Field(default=None, ge=0)
    revenue_growth_yoy: Decimal | None = None

    customers: int | None = Field(default=None, ge=0)
    paying_customers: int | None = Field(default=None, ge=0)
    active_users: int | None = Field(default=None, ge=0)

    repeat_customer_rate: Decimal | None = None

    key_traction_notes: str | None = None


# ---------------------------------------------------------------------------
# Financials
# ---------------------------------------------------------------------------

class FinancialAnalysis(AnalysisBase):
    """Financial information available for analysis."""

    revenue: Decimal | None = Field(default=None, ge=0)
    revenue_growth_yoy: Decimal | None = None

    gross_profit: Decimal | None = None
    gross_margin: Decimal | None = None

    ebitda: Decimal | None = None
    ebitda_margin: Decimal | None = None

    net_profit: Decimal | None = None

    cash: Decimal | None = Field(default=None, ge=0)
    debt: Decimal | None = Field(default=None, ge=0)

    burn_rate: Decimal | None = Field(default=None, ge=0)
    runway_months: Decimal | None = Field(default=None, ge=0)



# ---------------------------------------------------------------------------
# Fundraising
# ---------------------------------------------------------------------------

class FundraisingAnalysis(AnalysisBase):
    """Current fundraising information."""

    current_round: str | None = None

    amount_raising: Decimal | None = Field(default=None, ge=0)
    amount_raised: Decimal | None = Field(default=None, ge=0)

    pre_money_valuation: Decimal | None = Field(default=None, ge=0)
    post_money_valuation: Decimal | None = Field(default=None, ge=0)

    valuation_cap: Decimal | None = Field(default=None, ge=0)

    instrument: str | None = None

    investor_commitments: Decimal | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Business Model
# ---------------------------------------------------------------------------

class BusinessModelAnalysis(AnalysisBase):
    """Business model information."""

    business_model: str | None = None

    revenue_streams: list[str] = Field(default_factory=list)

    pricing_model: str | None = None

    gross_margin: Decimal | None = None

    customer_acquisition_cost: Decimal | None = Field(
        default=None,
        ge=0,
    )

    lifetime_value: Decimal | None = Field(
        default=None,
        ge=0,
    )

    ltv_to_cac: Decimal | None = Field(
        default=None,
        ge=0,
    )


# ---------------------------------------------------------------------------
# Derived Metrics
# ---------------------------------------------------------------------------

class FinancialMetrics(AnalysisBase):
    """Deterministic financial metrics."""

    revenue_multiple: Decimal | None = None
    ebitda_multiple: Decimal | None = None
    valuation_to_growth: Decimal | None = None

    ebitda_margin: Decimal | None = None
    gross_margin: Decimal | None = None
    ltv_to_cac: Decimal | None = None
    runway_months: Decimal | None = None

# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class AnalysisEvidence(AnalysisBase):
    """Source evidence supporting an analysis fact."""

    document_id: UUID | None = None

    page: int | None = Field(default=None, ge=1)
    section: str | None = None

    source_text: str | None = None

    confidence: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
    )


# ---------------------------------------------------------------------------
# Analysis Input
# ---------------------------------------------------------------------------

class StartupAnalysisInput(AnalysisBase):
    """
    Normalized information supplied to the startup analysis engine.
    """

    startup_id: UUID | None = None

    company: CompanyAnalysis

    founders: list[FounderAnalysis] = Field(
        default_factory=list
    )

    product: ProductAnalysis | None = None
    market: MarketAnalysis | None = None
    traction: TractionAnalysis | None = None
    financials: FinancialAnalysis | None = None
    fundraising: FundraisingAnalysis | None = None
    business_model: BusinessModelAnalysis | None = None

    evidence: list[AnalysisEvidence] = Field(
        default_factory=list
    )


# ---------------------------------------------------------------------------
# Qualitative Result
# ---------------------------------------------------------------------------

class StartupAnalysisResult(AnalysisBase):
    """Qualitative output from startup analysis."""

    company_overview: str | None = None

    founder_assessment: str | None = None
    product_assessment: str | None = None
    market_assessment: str | None = None
    traction_assessment: str | None = None
    financial_assessment: str | None = None
    valuation_assessment: str | None = None
    business_model_assessment: str | None = None
    competitive_assessment: str | None = None

    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    key_observations: list[str] = Field(default_factory=list)

    investment_thesis: str | None = None

    preliminary_recommendation: Literal[
        "insufficient_information",
        "promising",
        "needs_further_diligence",
        "concerns",
    ] = "insufficient_information"


# ---------------------------------------------------------------------------
# Complete Analysis
# ---------------------------------------------------------------------------

class StartupAnalysis(AnalysisBase):
    """Complete startup analysis output."""

    startup_id: UUID | None = None

    input: StartupAnalysisInput

    metrics: FinancialMetrics = Field(
        default_factory=FinancialMetrics
    )

    result: StartupAnalysisResult

    analysis_version: str = "1.0"

