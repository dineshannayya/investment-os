"""
Production investment-analysis orchestration.

Coordinates:
    - dimension-level scorecard evaluation
    - deterministic weighted-score aggregation
    - deterministic investment decision overlay
    - human-readable investment view

This service does not:
    - build prompts
    - invoke the LLM directly
    - calculate scores itself
    - calculate weights itself
    - modify evidence
    - modify the scorecard
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.dimension_evidence import (
    DimensionEvidenceSet,
)
from app.models.investment_decision import (
    InvestmentDecisionOverlay,
)
from app.models.investment_score_aggregation import (
    WeightedScoreAggregation,
)
from app.models.investment_scorecard import (
    InvestmentScorecard,
    MultiDimensionEvaluation,
)
from app.models.investment_view import (
    InvestmentView,
)
from app.services.investment_decision import (
    InvestmentDecisionService,
)
from app.services.investment_score_aggregation import (
    InvestmentScoreAggregationService,
)
from app.services.investment_scorecard_evaluation import (
    InvestmentScorecardEvaluationService,
)
from app.services.investment_view import (
    InvestmentViewService,
)


class InvestmentAnalysisResult(BaseModel):
    """
    Complete structured result of one investment analysis.

    All major intermediate artifacts are retained so that callers
    can inspect how the final InvestmentView was produced.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    evaluation: MultiDimensionEvaluation

    aggregation: WeightedScoreAggregation

    decision: InvestmentDecisionOverlay

    view: InvestmentView


class InvestmentAnalysisService:
    """
    Generic production investment-analysis orchestrator.

    The service coordinates existing specialized services.

    Responsibilities:
        - invoke scorecard evaluation
        - invoke deterministic score aggregation
        - invoke deterministic decision overlay
        - invoke InvestmentView construction

    It does NOT:
        - construct LLM prompts
        - invoke Qwen directly
        - calculate weighted scores itself
        - implement decision thresholds itself
        - modify evidence
        - modify scorecard configuration
    """

    def __init__(
        self,
        *,
        evaluation_service: InvestmentScorecardEvaluationService,
        aggregation_service: InvestmentScoreAggregationService,
        decision_service: InvestmentDecisionService,
        view_service: InvestmentViewService,
    ) -> None:
        self._evaluation_service = evaluation_service
        self._aggregation_service = aggregation_service
        self._decision_service = decision_service
        self._view_service = view_service

    def analyze(
        self,
        *,
        startup_name: str,
        scorecard: InvestmentScorecard,
        evidence_set: DimensionEvidenceSet,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        thinking_enabled: bool = False,
    ) -> InvestmentAnalysisResult:
        """
        Execute the complete investment scorecard analysis.

        Qwen evaluation is delegated to
        InvestmentScorecardEvaluationService.

        Weighted score calculation is delegated to
        InvestmentScoreAggregationService.

        Investment decision calculation is delegated to
        InvestmentDecisionService.

        InvestmentView construction is delegated to
        InvestmentViewService.
        """

        # --------------------------------------------------------------
        # 1. Multi-dimension Qwen evaluation
        # --------------------------------------------------------------

        evaluation = self._evaluation_service.evaluate(
            scorecard=scorecard,
            startup_name=startup_name,
            evidence_set=evidence_set,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
        )

        # --------------------------------------------------------------
        # 2. Deterministic weighted score
        # --------------------------------------------------------------

        aggregation = (
            self._aggregation_service.calculate(
                scorecard=scorecard,
                evaluation=evaluation,
            )
        )

        # --------------------------------------------------------------
        # 3. Deterministic investment decision
        # --------------------------------------------------------------

        decision = (
            self._decision_service.evaluate(
                aggregation=aggregation,
                evaluation=evaluation,
            )
        )

        # --------------------------------------------------------------
        # 4. Human-readable investment view
        # --------------------------------------------------------------

        view = self._view_service.build(
            scorecard=scorecard,
            evaluation=evaluation,
            aggregation=aggregation,
            decision=decision,
        )

        # --------------------------------------------------------------
        # 5. Preserve all intermediate artifacts
        # --------------------------------------------------------------

        return InvestmentAnalysisResult(
            evaluation=evaluation,
            aggregation=aggregation,
            decision=decision,
            view=view,
        )
