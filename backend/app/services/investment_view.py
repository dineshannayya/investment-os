from __future__ import annotations

from app.models.investment_decision import (
    InvestmentDecisionOverlay,
)
from app.models.investment_score_aggregation import (
    WeightedScoreAggregation,
)
from app.models.investment_scorecard import (
    InvestmentScorecard,
    MultiDimensionEvaluation,
    MissingInformation,
)
from app.models.investment_view import (
    InvestmentDimensionSummary,
    InvestmentView,
)


class InvestmentViewService:
    """
    Build the human-readable InvestmentView from the
    already-computed investment analysis artifacts.

    Responsibilities:
        - combine structured evaluation results
        - combine deterministic weighted-score results
        - combine deterministic decision results
        - collect positive observations
        - collect risk observations
        - collect missing information
        - derive diligence focus

    This service does NOT:
        - call an LLM
        - calculate dimension scores
        - calculate weighted scores
        - make investment decisions
        - modify evidence
    """

    @staticmethod
    def build(
        *,
        scorecard: InvestmentScorecard,
        evaluation: MultiDimensionEvaluation,
        aggregation: WeightedScoreAggregation,
        decision: InvestmentDecisionOverlay,
    ) -> InvestmentView:
        """
        Build the final InvestmentView.

        All analytical inputs must already have been validated
        by their respective services.
        """

        dimension_summary = (
            InvestmentViewService._build_dimension_summary(
                aggregation
            )
        )

        positive_factors = (
            InvestmentViewService._collect_positive_factors(
                evaluation
            )
        )

        key_risks = (
            InvestmentViewService._collect_key_risks(
                evaluation
            )
        )

        missing_information = (
            InvestmentViewService._collect_missing_information(
                evaluation
            )
        )

        diligence_focus = (
            InvestmentViewService._build_diligence_focus(
                evaluation=evaluation,
                decision=decision,
            )
        )

        investment_summary = (
            InvestmentViewService._build_investment_summary(
                startup_name=aggregation.startup_name,
                overall_score=aggregation.overall_score,
                decision=decision,
                positive_factors=positive_factors,
                key_risks=key_risks,
                missing_information=missing_information,
            )
        )

        return InvestmentView(
            startup_name=aggregation.startup_name,
            scorecard_name=scorecard.scorecard.name,
            scorecard_version=scorecard.scorecard.version,
            overall_score=aggregation.overall_score,
            decision=decision.decision.value,
            decision_reason=decision.decision_reason,
            dimension_summary=dimension_summary,
            positive_factors=positive_factors,
            key_risks=key_risks,
            missing_information=missing_information,
            diligence_focus=diligence_focus,
            investment_summary=investment_summary,
        )

    @staticmethod
    def _build_dimension_summary(
        aggregation: WeightedScoreAggregation,
    ) -> list[InvestmentDimensionSummary]:
        """
        Convert deterministic weighted-score results into the
        presentation-oriented dimension summary.

        Score and contribution values come directly from the
        aggregation service.
        """

        return [
            InvestmentDimensionSummary(
                dimension_id=item.dimension_id,
                score=item.score,
                weight=item.weight,
                weighted_score=item.weighted_score,
            )
            for item in aggregation.dimension_scores
        ]

    @staticmethod
    def _collect_positive_factors(
        evaluation: MultiDimensionEvaluation,
    ) -> list[str]:
        """
        Collect positive observations in scorecard dimension order.
        """

        factors: list[str] = []

        for dimension in evaluation.evaluations:
            factors.extend(
                dimension.positive_observations
            )

        return InvestmentViewService._unique_preserve_order(
            factors
        )

    @staticmethod
    def _collect_key_risks(
        evaluation: MultiDimensionEvaluation,
    ) -> list[str]:
        """
        Collect risk observations in scorecard dimension order.

        The original risk observations are preserved; this service
        does not create or reinterpret risks.
        """

        risks: list[str] = []

        for dimension in evaluation.evaluations:
            for risk in dimension.risk_observations:
                risks.append(risk.risk)

        return InvestmentViewService._unique_preserve_order(
            risks
        )

    @staticmethod
    def _format_missing_information(
        value: MissingInformation,
    ) -> str:
        """
        Convert a structured MissingInformation object into a
        human-readable presentation string.

        The structured object is preserved upstream. Only the
        presentation layer converts it to text.

        Examples:

            item="Customer retention"
            reason="No retention data was provided."

        becomes:

            "Customer retention — No retention data was provided."

        If reason is empty, only the item is returned.
        """

        item = value.item.strip()
        reason = value.reason.strip()

        if not item:
            return ""

        if not reason:
            return item

        return f"{item} — {reason}"

    @staticmethod
    def _collect_missing_information(
        evaluation: MultiDimensionEvaluation,
    ) -> list[str]:
        """
        Collect missing-information observations in scorecard
        dimension order.

        Missing information is kept separate from risks.

        Structured MissingInformation objects are converted to
        human-readable strings only at the InvestmentView boundary.

        Missing information is never converted into a risk by
        this service.
        """

        missing: list[str] = []

        for dimension in evaluation.evaluations:
            for value in dimension.missing_information:
                formatted = (
                    InvestmentViewService
                    ._format_missing_information(value)
                )

                if formatted:
                    missing.append(formatted)

        return InvestmentViewService._unique_preserve_order(
            missing
        )

    @staticmethod
    def _build_diligence_focus(
        *,
        evaluation: MultiDimensionEvaluation,
        decision: InvestmentDecisionOverlay,
    ) -> list[str]:
        """
        Build an initial diligence-focus list.

        Priority:
            1. blocking reasons from the deterministic decision layer
            2. risk observations
            3. missing information

        This is intentionally a simple aggregation mechanism.

        A sophisticated diligence-prioritization algorithm belongs
        to a later milestone.
        """

        focus: list[str] = []

        focus.extend(
            decision.blocking_reasons
        )

        for dimension in evaluation.evaluations:
            for risk in dimension.risk_observations:
                focus.append(
                    risk.risk
                )

        for dimension in evaluation.evaluations:
            for value in dimension.missing_information:
                formatted = (
                    InvestmentViewService
                    ._format_missing_information(value)
                )

                if formatted:
                    focus.append(formatted)

        return InvestmentViewService._unique_preserve_order(
            focus
        )

    @staticmethod
    def _build_investment_summary(
        *,
        startup_name: str,
        overall_score: float,
        decision: InvestmentDecisionOverlay,
        positive_factors: list[str],
        key_risks: list[str],
        missing_information: list[str],
    ) -> str:
        """
        Build a concise deterministic human-readable summary.

        This is intentionally NOT an LLM-generated narrative.
        """

        summary = (
            f"{startup_name} has an overall investment score "
            f"of {overall_score:.2f}/100 and a current investment "
            f"posture of {decision.decision.value}."
        )

        if positive_factors:
            summary += (
                f" The analysis identified "
                f"{len(positive_factors)} positive factor"
                f"{'s' if len(positive_factors) != 1 else ''}."
            )

        if key_risks:
            summary += (
                f" {len(key_risks)} risk observation"
                f"{'s' if len(key_risks) != 1 else ''} "
                "require attention."
            )

        if missing_information:
            summary += (
                f" {len(missing_information)} "
                "information item"
                f"{'s' if len(missing_information) != 1 else ''} "
                "remain unavailable."
            )

        return summary

    @staticmethod
    def _unique_preserve_order(
        values: list[str],
    ) -> list[str]:
        """
        Remove duplicates while preserving first occurrence order.
        """

        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            normalized = value.strip()

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(value)

        return result

