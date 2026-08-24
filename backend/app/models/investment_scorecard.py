from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ScorecardMetadata(BaseModel):
    """Identity and version information for an investment scorecard."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    version: int = Field(ge=1)
    description: str = Field(min_length=1)


class InvestorProfile(BaseModel):
    """Investor-specific context used by the evaluation framework."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ScoringGuidance(BaseModel):
    """Human-readable guidance for assigning a 0-100 dimension score."""

    model_config = ConfigDict(extra="forbid")

    score_90_100: str = Field(min_length=1)
    score_75_89: str = Field(min_length=1)
    score_60_74: str = Field(min_length=1)
    score_40_59: str = Field(min_length=1)
    score_0_39: str = Field(min_length=1)


class EvaluationSpec(BaseModel):
    """Instructions and constraints for evaluating one dimension."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)

    evaluate: tuple[str, ...] = Field(min_length=1)

    evidence_required: tuple[str, ...] = Field(min_length=1)

    positive_signals: tuple[str, ...] = Field(min_length=1)

    negative_signals: tuple[str, ...] = Field(min_length=1)

    do_not_assume: tuple[str, ...] = Field(min_length=1)

    scoring_guidance: ScoringGuidance


class InvestorPreferences(BaseModel):
    """Optional investor-specific preferences for a dimension."""

    model_config = ConfigDict(extra="forbid")

    priority: str = Field(min_length=1)
    notes: str = ""


class InvestmentDimension(BaseModel):
    """One dimension of the investment scorecard."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    # Percentage representation, e.g. 15 means 15%.
    weight: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))

    evaluation_spec: EvaluationSpec

    investor_preferences: InvestorPreferences


class InvestmentScorecard(BaseModel):
    """Investor-controlled configuration for startup evaluation."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)

    scorecard: ScorecardMetadata

    investor_profile: InvestorProfile

    dimensions: tuple[InvestmentDimension, ...] = Field(min_length=10, max_length=10)

    @field_validator("dimensions")
    @classmethod
    def validate_unique_dimension_ids(
        cls,
        dimensions: tuple[InvestmentDimension, ...],
    ) -> tuple[InvestmentDimension, ...]:
        ids = [dimension.id for dimension in dimensions]

        if len(ids) != len(set(ids)):
            raise ValueError("Investment dimension IDs must be unique.")

        return dimensions

    @model_validator(mode="after")
    def validate_weight_total(self) -> "InvestmentScorecard":
        total = sum(
            (dimension.weight for dimension in self.dimensions),
            Decimal("0"),
        )

        if total != Decimal("100"):
            raise ValueError(
                f"Investment dimension weights must total 100; got {total}."
            )

        return self

class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DimensionEvidence(BaseModel):
    """
    Evidence supporting a dimension evaluation.

    The reference must point back to preserved Investment OS evidence.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    source_type: str = Field(min_length=1)


class DimensionRisk(BaseModel):
    """
    Specific investment risk identified for a dimension.
    """

    model_config = ConfigDict(extra="forbid")

    risk: str = Field(min_length=1)
    severity: RiskSeverity
    impact: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, value: list[str]) -> list[str]:
        if any(not ref.strip() for ref in value):
            raise ValueError("evidence_refs cannot contain blank values")
        return value


class DimensionEvaluation(BaseModel):
    """
    AI-generated evaluation of one investment dimension.

    This is an evaluation artifact, not the final investment scorecard.
    """

    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    evidence: list[DimensionEvidence] = Field(
        default_factory=list,
    )

    positive_observations: list[str] = Field(
        default_factory=list,
    )

    risk_observations: list[DimensionRisk] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    reasoning: str = Field(min_length=1)

    @field_validator(
        "positive_observations",
        "missing_information",
    )
    @classmethod
    def validate_text_lists(
        cls,
        value: list[str],
    ) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("List values cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_dimension_evaluation(self) -> "DimensionEvaluation":
        evidence_refs = {
            evidence.evidence_ref
            for evidence in self.evidence
        }

        risk_refs = {
            ref
            for risk in self.risk_observations
            for ref in risk.evidence_refs
        }

        unknown_refs = risk_refs - evidence_refs

        if unknown_refs:
            raise ValueError(
                "Risk evidence_refs must reference evidence in the "
                f"same evaluation: {sorted(unknown_refs)}"
            )

        return self


class DimensionScorecardResult(BaseModel):
    """
    Deterministic scorecard result for one investment dimension.

    Weight and weighted_score are deliberately outside DimensionEvaluation.
    The LLM must not control the investment weighting.
    """

    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    weight: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    weighted_score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    @model_validator(mode="after")
    def validate_weighted_score(self) -> "DimensionScorecardResult":
        expected = (
            self.score * self.weight / Decimal("100")
        )

        if abs(self.weighted_score - expected) > Decimal("0.000001"):
            raise ValueError(
                "weighted_score must equal score × weight / 100"
            )

        return self
