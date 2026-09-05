from __future__ import annotations

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
    Evaluate every InvestmentScorecard dimension using only the evidence
    owned by that dimension.
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
        Evaluate every scorecard dimension exactly once.

        Evidence ownership is deterministic and established before
        invoking the LLM.

        For dimension D:

            supplied evidence =
                evidence_set.dimensions[D]

        Qwen cannot cite evidence belonging to another dimension.
        """

        self._validate_startup_identity(
            startup_name=startup_name,
            evidence_set=evidence_set,
        )

        # --------------------------------------------------------------
        # Validate evidence namespace before calling Qwen.
        #
        # Unknown dimension IDs are configuration errors.
        # Missing evidence for known dimensions is allowed.
        # --------------------------------------------------------------
        DimensionEvidenceLoader.validate_dimension_coverage(
            scorecard=scorecard,
            evidence_set=evidence_set,
        )

        expected_dimension_ids = [
            dimension.id
            for dimension in scorecard.dimensions
        ]

        evaluations: list[DimensionEvaluation] = []

        # --------------------------------------------------------------
        # Scorecard ordering is authoritative.
        # --------------------------------------------------------------
        for dimension in scorecard.dimensions:
            owned_evidence = (
                DimensionEvidenceLoader.get_dimension_evidence(
                    evidence_set,
                    dimension.id,
                )
            )

            allowed_refs = self._get_evidence_refs(
                dimension_id=dimension.id,
                dimension_evidence=owned_evidence,
            )

            startup_evidence = self._build_prompt_evidence(
                owned_evidence,
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
                    "dimension_evidence_count": len(
                        owned_evidence.evidence
                    ),
                },
            )

            response = self._provider.generate(request)

            # ----------------------------------------------------------
            # A structured JSON response must not be truncated.
            # ----------------------------------------------------------
            if response.finish_reason == "length":
                raise ValueError(
                    "Investment scorecard dimension evaluation "
                    f"was truncated: {dimension.id}"
                )

            evaluation = InvestmentScorecardParser.parse(
                response.text,
            )

            # ----------------------------------------------------------
            # The LLM must answer the dimension it was asked to answer.
            # ----------------------------------------------------------
            if evaluation.dimension_id != dimension.id:
                raise ValueError(
                    "LLM returned an unexpected dimension ID. "
                    f"Expected '{dimension.id}', "
                    f"received '{evaluation.dimension_id}'."
                )

            # ----------------------------------------------------------
            # Critical evidence ownership boundary.
            # ----------------------------------------------------------
            self._validate_evidence_ownership(
                dimension_id=dimension.id,
                allowed_evidence_refs=allowed_refs,
                evaluation=evaluation,
            )

            evaluations.append(evaluation)

        # --------------------------------------------------------------
        # Exactly one evaluation for every scorecard dimension.
        # --------------------------------------------------------------
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
    def _validate_startup_identity(
        *,
        startup_name: str,
        evidence_set: DimensionEvidenceSet,
    ) -> None:
        """
        Ensure evaluation and evidence refer to the same startup.
        """

        if not startup_name.strip():
            raise ValueError(
                "startup_name must not be empty."
            )

        if evidence_set.startup != startup_name:
            raise ValueError(
                "Dimension evidence startup does not match "
                "evaluation startup. "
                f"Expected '{startup_name}', "
                f"received '{evidence_set.startup}'."
            )

    @staticmethod
    def _get_evidence_refs(
        *,
        dimension_id: str,
        dimension_evidence: DimensionEvidence,
    ) -> set[str]:
        """
        Establish the authoritative evidence_ref set for one dimension.

        Duplicate references are rejected rather than silently removed.
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
                f"evidence_ref values for dimension "
                f"'{dimension_id}': {duplicates}"
            )

        return set(refs)

    @staticmethod
    def _build_prompt_evidence(
        dimension_evidence: DimensionEvidence,
    ) -> list[dict[str, str]]:
        """
        Convert dimension-owned evidence into the prompt representation.

        This function performs no enrichment, inference, reassignment,
        or filtering.
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
    def _validate_evidence_ownership(
        *,
        dimension_id: str,
        allowed_evidence_refs: set[str],
        evaluation: DimensionEvaluation,
    ) -> None:
        """
        Ensure every evidence reference returned by Qwen belongs to
        the current dimension's input evidence bucket.
        """

        returned_refs = {
            evidence.evidence_ref
            for evidence in evaluation.evidence
        }

        unexpected_refs = (
            returned_refs - allowed_evidence_refs
        )

        if unexpected_refs:
            raise ValueError(
                "Dimension evaluation returned evidence references "
                f"not owned by dimension '{dimension_id}': "
                f"{sorted(unexpected_refs)}"
            )

        # --------------------------------------------------------------
        # Risk references are checked independently.
        #
        # DimensionEvaluation validates that risk references point to
        # evidence included in that evaluation. This check additionally
        # proves that the cited evidence originated in this dimension's
        # input bucket.
        # --------------------------------------------------------------
        risk_refs = {
            evidence_ref
            for risk in evaluation.risk_observations
            for evidence_ref in risk.evidence_refs
        }

        unexpected_risk_refs = (
            risk_refs - allowed_evidence_refs
        )

        if unexpected_risk_refs:
            raise ValueError(
                "Dimension evaluation returned risk evidence "
                f"references not owned by dimension "
                f"'{dimension_id}': "
                f"{sorted(unexpected_risk_refs)}"
            )

    @staticmethod
    def _validate_dimension_coverage(
        *,
        expected_dimension_ids: list[str],
        evaluations: list[DimensionEvaluation],
    ) -> None:
        """
        Ensure exactly one evaluation exists for every scorecard dimension.
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
