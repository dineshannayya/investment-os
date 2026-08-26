from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.llm.models import LLMResponse
from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceItem,
    DimensionEvidenceSet,
)
from app.models.investment_scorecard import (
    DimensionEvaluation,
    InvestmentScorecard,
)
from app.services.investment_scorecard_evaluation import (
    InvestmentScorecardEvaluationService,
)


@pytest.fixture
def scorecard() -> InvestmentScorecard:
    return InvestmentScorecard.model_validate(
        {
            "schema_version": "1.0",
            "scorecard": {
                "name": "Test Investment Scorecard",
                "version": 1,
                "description": "Test scorecard for investment evaluation.",
            },
            "investor_profile": {
                "name": "Test Investor",
                "description": "Test investor profile.",
            },
            "evaluation_principles": {
                "evidence_semantics": {
                    "missing_information_is_not_negative_evidence": True,
                    "absence_of_evidence_is_not_evidence_of_negative_condition": True,
                    "risk_requires_supporting_evidence": True,
                },
                "missing_information_rule": {
                    "title": "Missing Information",
                    "rules": [
                        "Missing information is not negative evidence.",
                        "Absence of evidence is not evidence of a negative condition.",
                        "Risk requires supporting evidence.",
                        "Report unavailable information separately.",
                    ],
                },
            },
            "dimensions": [
                {
                    "id": dimension_id,
                    "name": dimension_id.replace("_", " ").title(),
                    "weight": 10,
                    "evaluation_spec": {
                        "objective": f"Evaluate {dimension_id}.",
                        "evaluate": [f"Evaluate {dimension_id}."],
                        "evidence_required": [
                            f"Evidence for {dimension_id}."
                        ],
                        "positive_signals": [
                            f"Positive signals for {dimension_id}."
                        ],
                        "negative_signals": [
                            f"Negative signals for {dimension_id}."
                        ],
                        "do_not_assume": [
                            f"Do not assume information about {dimension_id}."
                        ],
                        "scoring_guidance": {
                            "score_90_100": "Exceptional.",
                            "score_75_89": "Strong.",
                            "score_60_74": "Good.",
                            "score_40_59": "Moderate.",
                            "score_0_39": "Weak.",
                        },
                    },
                    "investor_preferences": {
                        "priority": "high",
                        "notes": "",
                    },
                }
                for dimension_id in [
                    "founder_team",
                    "market_tam",
                    "product_technology",
                    "business_model",
                    "traction",
                    "competitive_position",
                    "financials",
                    "valuation",
                    "risk",
                    "exit_potential",
                ]
            ],
        }
    )

# ============================================================================
# FAKE PROVIDERS
# ============================================================================


@dataclass
class FakeProvider:
    responses: list[str]

    def __post_init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)

        if not self.responses:
            raise AssertionError(
                "Fake provider has no remaining responses."
            )

        return LLMResponse(
            text=self.responses.pop(0),
            model="fake-qwen",
            finish_reason="stop",
        )


class RecordingProvider:
    """
    Provider used to inspect prompts and verify evidence isolation.
    """

    def __init__(
        self,
        responses: list[str],
    ) -> None:
        self.responses = list(responses)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)

        if not self.responses:
            raise AssertionError(
                "RecordingProvider has no remaining responses."
            )

        return LLMResponse(
            text=self.responses.pop(0),
            model="fake-qwen",
            finish_reason="stop",
        )


class TruncatedProvider:
    """
    Provider returning a deliberately truncated response.
    """

    def __init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)

        return LLMResponse(
            text='{"dimension_id":"founder_team"',
            model="fake-qwen",
            finish_reason="length",
        )


# ============================================================================
# HELPERS
# ============================================================================


def dimension_response(
    dimension_id: str,
    score: int = 70,
    confidence: int = 80,
    reasoning: str = "Test evaluation.",
) -> str:
    return f"""
{{
  "dimension_id": "{dimension_id}",
  "score": {score},
  "confidence": {confidence},
  "evidence": [],
  "positive_observations": [],
  "risk_observations": [],
  "missing_information": [],
  "reasoning": "{reasoning}"
}}
"""


def dimension_ids(
    scorecard: InvestmentScorecard,
) -> list[str]:
    return [
        dimension.id
        for dimension in scorecard.dimensions
    ]


def make_dimension_evidence_set(
    scorecard: InvestmentScorecard,
) -> DimensionEvidenceSet:
    """
    Create deterministic dimension-specific evidence for every
    scorecard dimension.

    Each dimension gets a unique evidence reference so the tests
    can detect cross-dimension evidence leakage.
    """

    dimensions = {}

    for dimension in scorecard.dimensions:
        dimensions[dimension.id] = DimensionEvidence(
            evidence=[
                DimensionEvidenceItem(
                    evidence_ref=(
                        f"{dimension.id}_evidence"
                    ),
                    observation=(
                        f"Evidence specifically supplied "
                        f"for {dimension.id}."
                    ),
                    source_type="test_fixture",
                )
            ]
        )

    return DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions=dimensions,
    )


# ============================================================================
# DAY-1.7.5.3 — COMPLETE MULTI-DIMENSION EVALUATION
# ============================================================================


def test_evaluate_all_dimensions(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    provider = FakeProvider(
        responses=[
            dimension_response(
                dimension_id,
                score=60 + index,
                confidence=80,
                reasoning=(
                    f"Evaluation for {dimension_id}."
                ),
            )
            for index, dimension_id
            in enumerate(expected_ids)
        ]
    )

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    result = service.evaluate(
        scorecard=scorecard,
        startup_name="RestoMart",
        evidence_set=evidence_set,
    )

    assert result.scorecard_version == (
        scorecard.scorecard.version
    )

    assert result.startup_name == "RestoMart"

    assert [
        item.dimension_id
        for item in result.evaluations
    ] == expected_ids

    assert len(result.evaluations) == 10

    assert len(provider.requests) == 10


# ============================================================================
# DAY-1.7.5.3 — EVIDENCE ROUTING
# ============================================================================


def test_each_dimension_receives_only_its_own_evidence(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    provider = RecordingProvider(
        responses=[
            dimension_response(
                dimension_id,
                reasoning=(
                    f"Evaluation for {dimension_id}."
                ),
            )
            for dimension_id in expected_ids
        ]
    )

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    service.evaluate(
        scorecard=scorecard,
        startup_name="RestoMart",
        evidence_set=evidence_set,
    )

    assert len(provider.requests) == 10

    for request in provider.requests:
        dimension_id = request.metadata[
            "scorecard_dimension"
        ]

        prompt = request.messages[1].content

        own_reference = (
            f"{dimension_id}_evidence"
        )

        assert own_reference in prompt

        for other_dimension_id in expected_ids:
            if other_dimension_id == dimension_id:
                continue

            other_reference = (
                f"{other_dimension_id}_evidence"
            )

            assert other_reference not in prompt


# ============================================================================
# DAY-1.7.5.3 — EVIDENCE COUNT METADATA
# ============================================================================


def test_dimension_evidence_count_is_recorded(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    provider = RecordingProvider(
        responses=[
            dimension_response(
                dimension_id,
            )
            for dimension_id in expected_ids
        ]
    )

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    service.evaluate(
        scorecard=scorecard,
        startup_name="RestoMart",
        evidence_set=evidence_set,
    )

    for request in provider.requests:
        assert request.metadata[
            "dimension_evidence_count"
        ] == 1


# ============================================================================
# DAY-1.7.5.3 — MISSING EVIDENCE
# ============================================================================


def test_dimension_without_evidence_is_allowed(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    dimensions = {}

    for dimension_id in expected_ids:
        dimensions[dimension_id] = (
            DimensionEvidence(
                evidence=[]
            )
        )

    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions=dimensions,
    )

    provider = RecordingProvider(
        responses=[
            dimension_response(
                dimension_id,
            )
            for dimension_id in expected_ids
        ]
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    result = service.evaluate(
        scorecard=scorecard,
        startup_name="RestoMart",
        evidence_set=evidence_set,
    )

    assert len(result.evaluations) == 10

    assert len(provider.requests) == 10

    for request in provider.requests:
        assert request.metadata[
            "dimension_evidence_count"
        ] == 0


# ============================================================================
# DAY-1.7.5.3 — UNKNOWN EVIDENCE DIMENSION
# ============================================================================


def test_evaluation_rejects_unknown_evidence_dimension(
    scorecard: InvestmentScorecard,
):
    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "unknown_dimension": DimensionEvidence(
                evidence=[]
            )
        },
    )

    provider = RecordingProvider(
        responses=[],
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    with pytest.raises(
        ValueError,
        match="Unexpected dimension evidence",
    ):
        service.evaluate(
            scorecard=scorecard,
            startup_name="RestoMart",
            evidence_set=evidence_set,
        )

    # Validation must happen before Qwen is called.
    assert provider.requests == []


# ============================================================================
# DAY-1.7.5.3 — WRONG DIMENSION RETURNED BY QWEN
# ============================================================================


def test_evaluate_rejects_wrong_dimension(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    wrong_dimension = expected_ids[1]

    provider = FakeProvider(
        responses=[
            dimension_response(
                wrong_dimension,
                score=70,
                confidence=80,
                reasoning="Wrong dimension.",
            )
        ]
    )

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    with pytest.raises(
        ValueError,
        match="unexpected dimension ID",
    ):
        service.evaluate(
            scorecard=scorecard,
            startup_name="RestoMart",
            evidence_set=evidence_set,
        )


# ============================================================================
# DAY-1.7.5.3 — TRUNCATED QWEN RESPONSE
# ============================================================================


def test_evaluate_rejects_truncated_response(
    scorecard: InvestmentScorecard,
):
    provider = TruncatedProvider()

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    with pytest.raises(
        ValueError,
        match="truncated",
    ):
        service.evaluate(
            scorecard=scorecard,
            startup_name="RestoMart",
            evidence_set=evidence_set,
        )


# ============================================================================
# DAY-1.7.2 REGRESSION — MISSING DIMENSION
# ============================================================================


def test_dimension_coverage_rejects_missing_dimension():
    evaluation = DimensionEvaluation(
        dimension_id="founder_team",
        score=80,
        confidence=90,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="Test",
    )

    with pytest.raises(
        ValueError,
        match="Missing dimension evaluations",
    ):
        InvestmentScorecardEvaluationService._validate_dimension_coverage(
            expected_dimension_ids=[
                "founder_team",
                "market_tam",
            ],
            evaluations=[
                evaluation,
            ],
        )


# ============================================================================
# DAY-1.7.2 REGRESSION — UNEXPECTED DIMENSION
# ============================================================================

def test_dimension_coverage_rejects_unexpected_dimension():
    founder = DimensionEvaluation(
        dimension_id="founder_team",
        score=80,
        confidence=90,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="Founder evaluation.",
    )

    market = DimensionEvaluation(
        dimension_id="market_tam",
        score=70,
        confidence=80,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="Market evaluation.",
    )

    unexpected = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=60,
        confidence=70,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="Unexpected evaluation.",
    )

    with pytest.raises(
        ValueError,
        match="Unexpected dimension evaluations",
    ):
        InvestmentScorecardEvaluationService._validate_dimension_coverage(
            expected_dimension_ids=[
                "founder_team",
                "market_tam",
            ],
            evaluations=[
                founder,
                market,
                unexpected,
            ],
        )



# ============================================================================
# DAY-1.7.2 REGRESSION — DUPLICATE DIMENSION
# ============================================================================


def test_dimension_coverage_rejects_duplicate_dimensions():
    evaluation_one = DimensionEvaluation(
        dimension_id="founder_team",
        score=80,
        confidence=90,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="First evaluation.",
    )

    evaluation_two = DimensionEvaluation(
        dimension_id="founder_team",
        score=70,
        confidence=80,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[],
        reasoning="Duplicate evaluation.",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate dimension evaluations",
    ):
        InvestmentScorecardEvaluationService._validate_dimension_coverage(
            expected_dimension_ids=[
                "founder_team",
            ],
            evaluations=[
                evaluation_one,
                evaluation_two,
            ],
        )


# ============================================================================
# DAY-1.7.5.3 — SCORECARD ORDER PRESERVATION
# ============================================================================


def test_dimension_order_is_preserved(
    scorecard: InvestmentScorecard,
):
    expected_ids = dimension_ids(scorecard)

    provider = FakeProvider(
        responses=[
            dimension_response(
                dimension_id,
            )
            for dimension_id in expected_ids
        ]
    )

    evidence_set = make_dimension_evidence_set(
        scorecard,
    )

    service = InvestmentScorecardEvaluationService(
        provider=provider,
    )

    result = service.evaluate(
        scorecard=scorecard,
        startup_name="RestoMart",
        evidence_set=evidence_set,
    )

    actual_ids = [
        evaluation.dimension_id
        for evaluation in result.evaluations
    ]

    assert actual_ids == expected_ids
