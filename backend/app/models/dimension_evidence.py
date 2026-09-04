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

from typing import Any

from app.llm.models import LLMMessage, LLMRequest
from app.llm.providers.qwen import QwenProvider
from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceSet,
)
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

    Responsibilities:
        - validate dimension evidence against the scorecard
        - route only dimension-owned evidence to each dimension
        - build dimension-specific prompts
        - invoke the LLM
        - parse structured dimension evaluations
        - validate dimension identity
        - validate returned evidence ownership
        - validate complete dimension coverage

    This service does NOT:
        - calculate weighted scores
        - calculate overall score
        - generate investment recommendations
        - modify startup evidence
        - modify scorecard weights
        - assign evidence to dimensions
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
        dimension_evidence: DimensionEvidenceSet,
        temperature: float = 0.0,
        max_tokens: int = 768,
        thinking_enabled: bool = False,
    ) -> MultiDimensionEvaluation:
        """
        Evaluate every dimension in the scorecard.

        Evidence ownership is established before LLM evaluation.

        For each scorecard dimension, the LLM receives only the evidence
        configured for that dimension in DimensionEvidenceSet.

        The LLM may interpret supplied evidence, but it may not introduce
        evidence references belonging to another dimension.
        """

        if not startup_name.strip():
            raise ValueError(
                "startup_name must not be empty."
            )

        if dimension_evidence.startup != startup_name:
            raise ValueError(
                "Dimension evidence startup does not match "
                f"evaluation startup. "
                f"Expected '{startup_name}', "
                f"received '{dimension_evidence.startup}'."
            )

        # ------------------------------------------------------------------
        # Establish the ownership boundary before invoking the LLM.
        #
        # Unknown dimension IDs are rejected.
        # Missing evidence for a known scorecard dimension is allowed.
        # ------------------------------------------------------------------
        DimensionEvidenceLoader.validate_dimension_coverage(
            scorecard=scorecard,
            evidence_set=dimension_evidence,
        )

        expected_dimension_ids = [
            dimension.id
            for dimension in scorecard.dimensions
        ]

        evaluations: list[DimensionEvaluation] = []

        for dimension in scorecard.dimensions:
            owned_evidence = (
                DimensionEvidenceLoader.get_dimension_evidence(
                    dimension_evidence,
                    dimension.id,
                )
            )

            startup_evidence = self._build_prompt_evidence(
                owned_evidence
            )

            allowed_evidence_refs = (
                self._get_evidence_refs(owned_evidence)
            )

            prompt = build_dimension_evaluation_prompt(
                scorecard=scorecard,
                dimension_id=dimension.id,
                startup_name=startup_name,
                startup_evidence=startup_evidence,
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
                            "Follow the evidence semantics exactly. "
                            "Use only evidence supplied for this "
                            "dimension. "
                            "Do not introduce evidence references "
                            "from another dimension."
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
                },
            )

            response = self._provider.generate(request)

            if response.finish_reason == "length":
                raise ValueError(
                    "Investment scorecard dimension evaluation "
                    f"was truncated: {dimension.id}"
                )

            evaluation = InvestmentScorecardParser.parse(
                response.text
            )

            if evaluation.dimension_id != dimension.id:
                raise ValueError(
                    "LLM returned an unexpected dimension ID. "
                    f"Expected '{dimension.id}', "
                    f"received '{evaluation.dimension_id}'."
                )

            self._validate_evidence_ownership(
                dimension_id=dimension.id,
                allowed_evidence_refs=allowed_evidence_refs,
                evaluation=evaluation,
            )

            evaluations.append(evaluation)

        self._validate_dimension_coverage(
            expected_dimension_ids=expected_dimension_ids,
            evaluations=evaluations,
        )

        return MultiDimensionEvaluation(
            scorecard_version=scorecard.scorecard.version,
            startup_name=startup_name,
            evaluations=evaluations,
        )

    @staticmethod
    def _build_prompt_evidence(
        dimension_evidence: DimensionEvidence,
    ) -> list[dict[str, Any]]:
        """
        Convert dimension-owned evidence into the prompt representation.

        Only evidence belonging to the current dimension is returned.
        No evidence is created, reassigned, or enriched here.
        """

        return [
            {
                "evidence_ref": item.evidence_ref,
                "observation": item.observation,
                "source_type": item.source_type,
            }
            for item in dimension_evidence.evidence
        ]

    @staticmethod
    def _get_evidence_refs(
        dimension_evidence: DimensionEvidence,
    ) -> set[str]:
        """
        Return the complete set of evidence references owned by a dimension.
        """

        refs = [
            item.evidence_ref
            for item in dimension_evidence.evidence
        ]

        if len(refs) != len(set(refs)):
            duplicates = sorted(
                {
                    ref
                    for ref in refs
                    if refs.count(ref) > 1
                }
            )

            raise ValueError(
                "Dimension evidence contains duplicate "
                f"evidence_ref values: {duplicates}"
            )

        return set(refs)

    @staticmethod
    def _validate_evidence_ownership(
        *,
        dimension_id: str,
        allowed_evidence_refs: set[str],
        evaluation: DimensionEvaluation,
    ) -> None:
        """
        Ensure that the LLM only cites evidence owned by this dimension.

        This is the critical dimension-ownership integrity boundary.

        A reference is valid only when it was supplied in the evidence
        bucket for the dimension currently being evaluated.
        """

        returned_refs = {
            evidence.evidence_ref
            for evidence in evaluation.evidence
        }

        unexpected_refs = returned_refs - allowed_evidence_refs

        if unexpected_refs:
            raise ValueError(
                "Dimension evaluation returned evidence references "
                f"not owned by dimension '{dimension_id}': "
                f"{sorted(unexpected_refs)}"
            )

        # DimensionEvaluation already verifies that risk references point
        # to evidence inside the same evaluation. Keep that invariant
        # separate from the service-level ownership check above.
        risk_refs = {
            ref
            for risk in evaluation.risk_observations
            for ref in risk.evidence_refs
        }

        unexpected_risk_refs = (
            risk_refs - allowed_evidence_refs
        )

        if unexpected_risk_refs:
            raise ValueError(
                "Dimension evaluation returned risk evidence "
                f"references not owned by dimension '{dimension_id}': "
                f"{sorted(unexpected_risk_refs)}"
            )

    @staticmethod
    def _validate_dimension_coverage(
        *,
        expected_dimension_ids: list[str],
        evaluations: list[DimensionEvaluation],
    ) -> None:
        """
        Validate that exactly one evaluation exists for every
        scorecard dimension.
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

        if missing or unexpected:
            details = []

            if missing:
                details.append(
                    f"missing={sorted(missing)}"
                )

            if unexpected:
                details.append(
                    f"unexpected={sorted(unexpected)}"
                )

            raise ValueError(
                "Dimension evaluation coverage mismatch: "
                + ", ".join(details)
            )

        if len(actual_dimension_ids) != len(
            expected_dimension_ids
        ):
            raise ValueError(
                "Dimension evaluation count does not match "
                "scorecard dimension count."
            )
