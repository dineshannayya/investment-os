"""
Structured startup evidence used for dimension-level investment evaluation.

This model deliberately contains evidence only.

It does not contain:
    - scores
    - confidence
    - weights
    - risks
    - missing information
    - investment conclusions
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class DimensionEvidenceItem(BaseModel):
    """
    One evidence observation supplied to a dimension evaluator.
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
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    evidence: List[DimensionEvidenceItem] = Field(
        default_factory=list,
    )


class DimensionEvidenceSet(BaseModel):
    """
    Startup-specific evidence organized by investment dimension.

    This is intentionally independent from InvestmentScorecard.

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

    dimensions: Dict[str, DimensionEvidence] = Field(
        default_factory=dict,
    )
