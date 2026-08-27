from __future__ import annotations

from app.models.investment_decision import (
    DecisionSeverity,
    InvestmentDecision,
    InvestmentDecisionOverlay,
)
from app.models.investment_score_aggregation import (
    WeightedScoreAggregation,
)
from app.models.investment_scorecard import (
    MultiDimensionEvaluation,
)


class InvestmentDecisionService:
    """
    Deterministically convert score + risks + missing information
    into an investment decision.

    No LLM is used here.
    """

    @staticmethod
    def evaluate(
        *,
        aggregation: WeightedScoreAggregation,
        evaluation: MultiDimensionEvaluation,
    ) -> InvestmentDecisionOverlay:

        risks = [
            risk
            for dimension in evaluation.evaluations
            for risk in dimension.risk_observations
        ]

        high_risks = [
            risk
            for risk in risks
            if risk.severity == DecisionSeverity.HIGH
        ]

        critical_risks = [
            risk
            for risk in risks
            if risk.severity == DecisionSeverity.CRITICAL
        ]

        medium_risks = [
            risk
            for risk in risks
            if risk.severity == DecisionSeverity.MEDIUM
        ]

        critical_missing_information = (
            InvestmentDecisionService
            ._identify_critical_missing_information(
                evaluation
            )
        )

        blocking_reasons: list[str] = []

        # --------------------------------------------------------------
        # Risk gates
        # --------------------------------------------------------------

        if critical_risks:
            decision = InvestmentDecision.AVOID

            blocking_reasons.extend(
                f"Critical risk: {risk.risk}"
                for risk in critical_risks
            )

        elif len(high_risks) >= 2:
            decision = InvestmentDecision.FURTHER_DILIGENCE

            blocking_reasons.extend(
                f"High risk: {risk.risk}"
                for risk in high_risks
            )

        elif high_risks:
            decision = InvestmentDecision.CONDITIONAL

            blocking_reasons.extend(
                f"High risk: {risk.risk}"
                for risk in high_risks
            )

        elif critical_missing_information:
            decision = InvestmentDecision.FURTHER_DILIGENCE

            blocking_reasons.extend(
                f"Critical missing information: {item}"
                for item in critical_missing_information
            )

        else:
            decision = (
                InvestmentDecisionService
                ._score_to_decision(
                    aggregation.overall_score
                )
            )

        positive_factors = (
            InvestmentDecisionService
            ._collect_positive_factors(
                evaluation
            )
        )

        reason = (
            InvestmentDecisionService
            ._build_reason(
                decision=decision,
                overall_score=aggregation.overall_score,
                high_risk_count=len(high_risks),
                critical_risk_count=len(critical_risks),
                critical_missing_count=len(
                    critical_missing_information
                ),
            )
        )

        return InvestmentDecisionOverlay(
            startup_name=aggregation.startup_name,
            scorecard_version=aggregation.scorecard_version,
            overall_score=aggregation.overall_score,
            decision=decision,
            decision_reason=reason,
            high_risk_count=len(high_risks),
            critical_risk_count=len(critical_risks),
            medium_risk_count=len(medium_risks),
            critical_missing_information=(
                critical_missing_information
            ),
            blocking_reasons=blocking_reasons,
            positive_factors=positive_factors,
        )

    @staticmethod
    def _score_to_decision(
        score: float,
    ) -> InvestmentDecision:

        if score >= 90:
            return InvestmentDecision.STRONG

        if score >= 75:
            return InvestmentDecision.CONDITIONAL

        if score >= 60:
            return InvestmentDecision.FURTHER_DILIGENCE

        return InvestmentDecision.AVOID

    @staticmethod
    def _identify_critical_missing_information(
        evaluation: MultiDimensionEvaluation,
    ) -> list[str]:
        """
        Missing information is NOT automatically treated as
        negative evidence.

        Until the scorecard contains an explicit deterministic
        classification of critical missing information, return
        an empty list.
        """

        return []

    @staticmethod
    def _collect_positive_factors(
        evaluation: MultiDimensionEvaluation,
    ) -> list[str]:

        factors: list[str] = []

        for dimension in evaluation.evaluations:
            factors.extend(
                dimension.positive_observations
            )

        return factors

    @staticmethod
    def _build_reason(
        *,
        decision: InvestmentDecision,
        overall_score: float,
        high_risk_count: int,
        critical_risk_count: int,
        critical_missing_count: int,
    ) -> str:

        if decision == InvestmentDecision.AVOID:
            return (
                f"Overall score is {overall_score:.2f}, "
                "and critical investment risks require "
                "an avoid decision."
            )

        if decision == InvestmentDecision.FURTHER_DILIGENCE:
            return (
                f"Overall score is {overall_score:.2f}, "
                "but additional diligence is required "
                "before an investment decision."
            )

        if decision == InvestmentDecision.CONDITIONAL:
            return (
                f"Overall score is {overall_score:.2f}. "
                "The opportunity has merit but requires "
                "specific risk or diligence conditions."
            )

        return (
            f"Overall score is {overall_score:.2f} "
            "with no overriding critical risk gate."
        )
