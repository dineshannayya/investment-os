"""
Structured startup evidence used for dimension-level investment evaluation.

This module contains evidence only.

It does not contain:
    - scores
    - confidence
    - weights
    - risks
    - missing information
    - investment conclusions
    - LLM logic
    - scorecard logic
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DimensionEvidenceItem(BaseModel):
    """
    One evidence observation supplied to a dimension evaluator.

    evidence_ref is the stable reference used by downstream evaluation
    results to cite the evidence.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    evidence_ref: str = Field(
        min_length=1,
    )

    observation: str = Field(
        min_length=1,
    )

    source_type: str = Field(
        min_length=1,
    )


class DimensionEvidence(BaseModel):
    """
    Evidence applicable to one investment dimension.

    An empty evidence list is valid. Missing evidence must not be
    interpreted as negative evidence.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    evidence: list[DimensionEvidenceItem] = Field(
        default_factory=list,
    )


class DimensionEvidenceSet(BaseModel):
    """
    Startup-specific evidence organized by investment dimension.

    InvestmentScorecard answers:
        What should be evaluated?

    DimensionEvidenceSet answers:
        What evidence is currently available for this startup?
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: str = Field(
        min_length=1,
    )

    startup: str = Field(
        min_length=1,
    )

    dimensions: dict[str, DimensionEvidence] = Field(
        default_factory=dict,
    )
