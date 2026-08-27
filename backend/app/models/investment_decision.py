from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InvestmentDecision(StrEnum):
    """
    Deterministic investment decision classification.

    These values describe the current investment-analysis posture.
    They are not a final legal or financial investment instruction.
    """

    STRONG = "strong"
    CONDITIONAL = "conditional"
    FURTHER_DILIGENCE = "further_diligence"
    AVOID = "avoid"


class DecisionSeverity(StrEnum):
    """
    Severity classification used by the deterministic
    investment decision overlay.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvestmentDecisionOverlay(BaseModel):
    """
    Deterministic investment decision overlay.

    This model contains the result of applying deterministic
    decision rules to the weighted score and structured
    dimension evaluation.

    No LLM-generated decision is stored here.
    """

    model_config = ConfigDict(extra="forbid")

    startup_name: str

    scorecard_version: int

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    decision: InvestmentDecision

    decision_reason: str

    high_risk_count: int = Field(
        ge=0,
    )

    critical_risk_count: int = Field(
        ge=0,
    )

    medium_risk_count: int = Field(
        ge=0,
    )

    critical_missing_information: list[str] = Field(
        default_factory=list,
    )

    blocking_reasons: list[str] = Field(
        default_factory=list,
    )

    positive_factors: list[str] = Field(
        default_factory=list,
    )
