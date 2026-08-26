"""
Multi-dimension investment scorecard evaluation service.

Day-1.7.5.3:
    Dimension-specific evidence routing.

Responsibilities:
    - validate evidence coverage against the scorecard
    - iterate through scorecard dimensions
    - route only the evidence belonging to the current dimension
    - build dimension-specific prompts
    - invoke the LLM
    - parse structured dimension evaluations
    - validate dimension identity
    - validate complete dimension coverage

This service does NOT:
    - calculate weighted scores
    - calculate overall score
    - generate investment recommendations
    - modify startup evidence
    - modify scorecard weights
"""

from __future__ import annotations

from app.llm.models import LLMMessage, LLMRequest
from app.llm.providers.qwen import QwenProvider
from app.models.dimension_evidence import DimensionEvidenceSet
from app.models.investment_scorecard import (
    DimensionEvaluation,
    InvestmentScorecard,
    MultiDimensionEvaluation,
)
from app.prompt.investment_scorecard import (
    build_dimension_evaluation_prompt,
)
from app.services.dimension_evidence_loader import (
    DimensionEvidenceLoader,
)
from app.services.investment_scorecard_parser import (
    InvestmentScorecardParser,
)


class InvestmentScorecardEvaluationService:
    """
    Orchestrate evaluation of all dimensions in an investment scorecard.

    Day-1.7.5.3 introduces dimension-specific evidence routing.

    For each scorecard dimension:

        scorecard dimension
                ↓
        DimensionEvidenceLoader
                ↓
        dimension-specific evidence
                ↓
        dimension prompt
                ↓
        LLM
                ↓
        DimensionEvaluation
    """

    def __init__(
        self,
        *,
        provider: QwenProvider | None = None,
    ) -> None:
        self._provider = provider or QwenProvider()

    def evaluate(
        self,
        *,
        scorecard: InvestmentScorecard,
        startup_name: str,
        evidence_set: DimensionEvidenceSet,
        temperature: float = 0.0,
        max_tokens: int = 768,
        thinking_enabled: bool = False,
    ) -> MultiDimensionEvaluation:
        """
        Evaluate every dimension in the scorecard.

        Evidence is routed independently for each dimension.

        Missing evidence is allowed.

        Unknown evidence dimensions are rejected before
        any LLM request is made.
        """

        # ------------------------------------------------------------------
        # Validate evidence dimension IDs before invoking the LLM.
        # ------------------------------------------------------------------

        DimensionEvidenceLoader.validate_dimension_coverage(
            scorecard=scorecard,
            evidence_set=evidence_set,
        )

        expected_dimension_ids = [
            dimension.id
            for dimension in scorecard.dimensions
        ]

        evaluations: list[DimensionEvaluation] = []

        # ------------------------------------------------------------------
        # Evaluate dimensions sequentially.
        # ------------------------------------------------------------------

        for dimension in scorecard.dimensions:

            # --------------------------------------------------------------
            # DAY-1.7.5.3
            #
            # Retrieve ONLY the evidence mapped to this dimension.
            # --------------------------------------------------------------

            dimension_evidence = (
                DimensionEvidenceLoader.get_dimension_evidence(
                    evidence_set,
                    dimension.id,
                )
            )

            prompt = build_dimension_evaluation_prompt(
                scorecard=scorecard,
                dimension_id=dimension.id,
                startup_name=startup_name,
                startup_evidence=[
                    evidence.model_dump(mode="json")
                    for evidence
                    in dimension_evidence.evidence
                ],
            )

            request = LLMRequest(
                messages=(
                    LLMMessage(
                        role="system",
                        content=(
                            "You are an investment analysis engine. "
                            "Return ONLY the structured JSON object "
                            "requested by the user prompt. "
                            "Do not use markdown fences. "
                            "Follow the evidence semantics exactly."
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=prompt,
                    ),
                ),
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={
                    "thinking_enabled": thinking_enabled,
                    "scorecard_dimension": dimension.id,
                    "startup_name": startup_name,
                    "dimension_evidence_count": len(
                        dimension_evidence.evidence
                    ),
                },
            )

            response = self._provider.generate(request)

            # --------------------------------------------------------------
            # Reject truncated LLM responses.
            # --------------------------------------------------------------

            if response.finish_reason == "length":
                raise ValueError(
                    "Investment scorecard dimension evaluation "
                    f"was truncated: {dimension.id}"
                )

            # --------------------------------------------------------------
            # Parse structured response.
            # --------------------------------------------------------------

            evaluation = InvestmentScorecardParser.parse(
                response.text
            )

            # --------------------------------------------------------------
            # Validate that Qwen evaluated the requested dimension.
            # --------------------------------------------------------------

            if evaluation.dimension_id != dimension.id:
                raise ValueError(
                    "LLM returned an unexpected dimension ID. "
                    f"Expected '{dimension.id}', "
                    f"received '{evaluation.dimension_id}'."
                )

            evaluations.append(evaluation)

        # ------------------------------------------------------------------
        # Validate complete dimension coverage.
        # ------------------------------------------------------------------

        self._validate_dimension_coverage(
            expected_dimension_ids=expected_dimension_ids,
            evaluations=evaluations,
        )

        # ------------------------------------------------------------------
        # Return structured multi-dimension evaluation.
        # ------------------------------------------------------------------

        return MultiDimensionEvaluation(
            scorecard_version=scorecard.scorecard.version,
            startup_name=startup_name,
            evaluations=evaluations,
        )

    @staticmethod
    def _validate_dimension_coverage(
        *,
        expected_dimension_ids: list[str],
        evaluations: list[DimensionEvaluation],
    ) -> None:
        """
        Validate that exactly the expected dimensions were evaluated.
        """

        actual_dimension_ids = [
            evaluation.dimension_id
            for evaluation in evaluations
        ]

        expected = set(expected_dimension_ids)
        actual = set(actual_dimension_ids)

        duplicates = {
            dimension_id
            for dimension_id in actual_dimension_ids
            if actual_dimension_ids.count(dimension_id) > 1
        }

        if duplicates:
            raise ValueError(
                "Duplicate dimension evaluations: "
                f"{sorted(duplicates)}"
            )

        missing = expected - actual
        unexpected = actual - expected

        if missing:
            raise ValueError(
                "Missing dimension evaluations: "
                f"{sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                "Unexpected dimension evaluations: "
                f"{sorted(unexpected)}"
            )

        if len(actual_dimension_ids) != len(
            expected_dimension_ids
        ):
            raise ValueError(
                "Dimension evaluation count does not match "
                "scorecard dimension count."
            )
