"""
Deterministic weighted investment score aggregation.

This service contains no LLM logic.

Responsibilities:
    - validate dimension coverage
    - validate scorecard weights
    - calculate weighted dimension contributions
    - calculate the overall investment score
"""

from __future__ import annotations

from decimal import Decimal

from app.models.investment_score_aggregation import (
    DimensionWeightedScore,
    WeightedScoreAggregation,
)
from app.models.investment_scorecard import (
    InvestmentScorecard,
    MultiDimensionEvaluation,
)


class InvestmentScoreAggregationService:
    """
    Deterministically calculate the weighted investment score.

    All arithmetic is performed using Decimal to avoid
    float/Decimal incompatibility and floating-point
    precision issues.
    """

    @staticmethod
    def calculate(
        *,
        scorecard: InvestmentScorecard,
        evaluation: MultiDimensionEvaluation,
    ) -> WeightedScoreAggregation:
        expected_dimensions = {
            dimension.id: dimension
            for dimension in scorecard.dimensions
        }

        actual_dimensions = {
            item.dimension_id: item
            for item in evaluation.evaluations
        }

        expected_ids = set(expected_dimensions)
        actual_ids = set(actual_dimensions)

        missing = expected_ids - actual_ids
        unexpected = actual_ids - expected_ids

        if missing:
            raise ValueError(
                "Cannot calculate weighted score. "
                "Missing dimension evaluations: "
                f"{sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                "Cannot calculate weighted score. "
                "Unexpected dimension evaluations: "
                f"{sorted(unexpected)}"
            )

        total_weight = sum(
            dimension.weight
            for dimension in scorecard.dimensions
        )

        if total_weight != Decimal("100"):
            raise ValueError(
                "Scorecard dimension weights must total 100. "
                f"Actual total: {total_weight}"
            )

        dimension_scores: list[
            DimensionWeightedScore
        ] = []

        weighted_total = Decimal("0")

        # Preserve scorecard ordering.
        for dimension in scorecard.dimensions:
            dimension_evaluation = actual_dimensions[
                dimension.id
            ]

            weighted_score = (
                Decimal(dimension_evaluation.score)
                * dimension.weight
                / Decimal("100")
            )

            weighted_total += weighted_score

            dimension_scores.append(
                DimensionWeightedScore(
                    dimension_id=dimension.id,
                    score=dimension_evaluation.score,
                    weight=dimension.weight,
                    weighted_score=float(
                        weighted_score.quantize(
                            Decimal("0.01")
                        )
                    ),
                )
            )

        overall_score = weighted_total.quantize(
            Decimal("0.01")
        )

        return WeightedScoreAggregation(
            scorecard_version=scorecard.scorecard.version,
            startup_name=evaluation.startup_name,
            dimension_scores=dimension_scores,
            total_weight=total_weight,
            overall_score=float(overall_score),
        )
