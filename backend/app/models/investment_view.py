from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InvestmentDimensionSummary(BaseModel):
    """
    Presentation-oriented summary of one investment dimension.
    """

    model_config = ConfigDict(extra="forbid")

    dimension_id: str

    score: int = Field(
        ge=0,
        le=100,
    )

    weight: int = Field(
        ge=0,
        le=100,
    )

    weighted_score: float = Field(
        ge=0.0,
        le=100.0,
    )


class InvestmentView(BaseModel):
    """
    Human-readable investment view derived from the
    deterministic scorecard evaluation.
    """

    model_config = ConfigDict(extra="forbid")

    startup_name: str

    scorecard_name: str

    scorecard_version: int

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    decision: str

    decision_reason: str

    dimension_summary: list[InvestmentDimensionSummary]

    positive_factors: list[str]

    key_risks: list[str]

    missing_information: list[str]

    diligence_focus: list[str]

    investment_summary: str
