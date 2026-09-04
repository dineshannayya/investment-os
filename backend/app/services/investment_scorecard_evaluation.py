from __future__ import annotations

from typing import Any

from app.llm.models import LLMMessage, LLMRequest
from app.llm.providers.qwen import QwenProvider
from app.models.investment_scorecard import (
    DimensionEvaluation,
    InvestmentScorecard,
    MultiDimensionEvaluation,
)
from app.prompt.investment_scorecard import (
    build_dimension_evaluation_prompt,
)
from app.services.investment_scorecard_parser import (
    InvestmentScorecardParser,
)


class InvestmentScorecardEvaluationService:
    """
    Orchestrate evaluation of all dimensions in an investment scorecard.

    Responsibilities:
        - iterate through scorecard dimensions
        - build dimension prompts
        - invoke the LLM
        - parse structured dimension evaluations
        - validate dimension identity
        - validate returned evidence references
        - validate complete dimension coverage

    This service does NOT:
        - calculate weighted scores
        - calculate overall score
        - generate investment recommendations
        - modify startup evidence
        - modify scorecard weights
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
        startup_evidence: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 768,
        thinking_enabled: bool = False,
    ) -> MultiDimensionEvaluation:
        """
        Evaluate every dimension in the scorecard.

        Evaluation is performed sequentially to keep the initial
        implementation simple and predictable for local Qwen inference.

        Evidence integrity is enforced at two levels:

        1. DimensionEvaluation validates that evidence references are
           unique and that risk references point to returned evidence.

        2. This service validates that every evidence reference returned
           by the LLM existed in the supplied startup evidence.

        The current service contract receives a flat startup_evidence
        collection. Therefore this method does not infer dimension
        ownership from evidence metadata. A future DimensionEvidenceSet
        contract can enforce cross-dimension ownership explicitly.
        """

        expected_dimension_ids = [
            dimension.id
            for dimension in scorecard.dimensions
        ]

        # ------------------------------------------------------------------
        # Phase 1:
        #
        # Build the authoritative set of evidence references supplied to
        # the LLM. The LLM may select from this set, but it may not invent
        # a new reference.
        #
        # Ignore malformed entries here only long enough to let the
        # existing prompt/provider path operate as before; returned
        # evidence refs are always checked strictly below.
        # ------------------------------------------------------------------
        allowed_evidence_refs = {
            evidence_ref
            for evidence_ref in (
                self._extract_evidence_ref(item)
                for item in startup_evidence
            )
            if evidence_ref is not None
        }

        evaluations: list[DimensionEvaluation] = []

        for dimension in scorecard.dimensions:
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

            # --------------------------------------------------------------
            # Phase 1 evidence-integrity validation.
            #
            # Every evidence_ref returned by Qwen must have existed in the
            # evidence supplied to the evaluation service.
            #
            # Do not silently remove invalid references. A fabricated or
            # altered evidence reference is a hard evaluation-contract
            # violation and must fail the evaluation.
            # --------------------------------------------------------------
            self._validate_evidence_references(
                evaluation=evaluation,
                allowed_evidence_refs=allowed_evidence_refs,
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
    def _extract_evidence_ref(
        evidence: dict[str, Any],
    ) -> str | None:
        """
        Extract an evidence_ref from one supplied evidence item.

        The current service contract accepts generic dictionaries, so
        malformed input is not assumed to have a particular structure.

        Valid references are normalized only for presence checking;
        the actual reference returned by the LLM is never modified.
        """

        if not isinstance(evidence, dict):
            return None

        value = evidence.get("evidence_ref")

        if not isinstance(value, str):
            return None

        if not value.strip():
            return None

        return value

    @staticmethod
    def _validate_evidence_references(
        *,
        evaluation: DimensionEvaluation,
        allowed_evidence_refs: set[str],
    ) -> None:
        """
        Validate that every returned evidence_ref was supplied to the LLM.

        This is a trust-boundary check between the LLM and Investment OS.

        The LLM may:
            - select supplied evidence
            - interpret supplied evidence
            - summarize supplied evidence

        The LLM may not:
            - invent evidence references
            - rename evidence references
            - fabricate evidence identifiers

        Duplicate references are already rejected by DimensionEvaluation.
        Risk references are also already required to reference evidence
        contained in the same DimensionEvaluation.
        """

        returned_evidence_refs = {
            evidence.evidence_ref
            for evidence in evaluation.evidence
        }

        invalid_refs = (
            returned_evidence_refs
            - allowed_evidence_refs
        )

        if invalid_refs:
            raise ValueError(
                "Dimension evaluation returned evidence_ref values "
                "that were not present in the supplied evidence: "
                f"{sorted(invalid_refs)}"
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
