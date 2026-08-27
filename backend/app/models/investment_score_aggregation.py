from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DimensionWeightedScore(BaseModel):
    """
    Deterministic weighted contribution of one investment
    scorecard dimension.
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


class WeightedScoreAggregation(BaseModel):
    """
    Deterministic aggregation of all scorecard dimensions.

    The overall score is calculated entirely outside the LLM.
    """

    model_config = ConfigDict(extra="forbid")

    scorecard_version: int

    startup_name: str

    dimension_scores: list[DimensionWeightedScore]

    total_weight: int = Field(
        ge=0,
        le=100,
    )

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
    )
