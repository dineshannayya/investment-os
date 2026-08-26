from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError


from app.models.investment_scorecard import (
    InvestmentScorecard,
    DimensionEvaluation,
    DimensionEvidence,
    DimensionRisk,
    DimensionScorecardResult,
    RiskSeverity,
)

from app.models.investment_scorecard import (
    InvestmentScorecard,
    DimensionEvaluation,
    MultiDimensionEvaluation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESTOMART_SCORECARD = (
    PROJECT_ROOT
    / "data"
    / "real_startups"
    / "restomart"
    / "investment_scorecard.json"
)


@pytest.fixture
def scorecard() -> InvestmentScorecard:
    data = json.loads(
        RESTOMART_SCORECARD.read_text(
            encoding="utf-8"
        )
    )

    return InvestmentScorecard.model_validate(data)


def load_restomart_scorecard() -> InvestmentScorecard:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return InvestmentScorecard.model_validate(payload)


def test_restomart_scorecard_file_exists() -> None:
    assert RESTOMART_SCORECARD.exists()
    assert RESTOMART_SCORECARD.is_file()


def test_restomart_scorecard_loads() -> None:
    scorecard = load_restomart_scorecard()

    assert isinstance(scorecard, InvestmentScorecard)


def test_scorecard_schema_version() -> None:
    scorecard = load_restomart_scorecard()

    assert scorecard.schema_version == "1.0"


def test_scorecard_identity() -> None:
    scorecard = load_restomart_scorecard()

    assert scorecard.scorecard.name
    assert scorecard.scorecard.version >= 1
    assert scorecard.scorecard.description


def test_investor_profile() -> None:
    scorecard = load_restomart_scorecard()

    assert scorecard.investor_profile.name
    assert scorecard.investor_profile.description


def test_exactly_ten_dimensions() -> None:
    scorecard = load_restomart_scorecard()

    assert len(scorecard.dimensions) == 10


def test_dimension_ids_are_unique() -> None:
    scorecard = load_restomart_scorecard()

    ids = [dimension.id for dimension in scorecard.dimensions]

    assert len(ids) == len(set(ids))


def test_dimension_names_are_present() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        assert dimension.id
        assert dimension.name


def test_dimension_weights_are_valid() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        assert Decimal("0") <= dimension.weight <= Decimal("100")


def test_dimension_weights_total_one_hundred_percent() -> None:
    scorecard = load_restomart_scorecard()

    total = sum(
        (dimension.weight for dimension in scorecard.dimensions),
        Decimal("0"),
    )

    assert total == Decimal("100")


def test_evaluation_spec_is_complete() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        spec = dimension.evaluation_spec

        assert spec.objective
        assert spec.evaluate
        assert spec.evidence_required
        assert spec.positive_signals
        assert spec.negative_signals
        assert spec.do_not_assume
        assert spec.scoring_guidance


def test_scoring_guidance_covers_all_score_ranges() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        guidance = dimension.evaluation_spec.scoring_guidance

        assert guidance.score_90_100
        assert guidance.score_75_89
        assert guidance.score_60_74
        assert guidance.score_40_59
        assert guidance.score_0_39


def test_investor_preferences_are_present() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        preferences = dimension.investor_preferences

        assert preferences.priority is not None
        assert preferences.notes is not None


def test_configuration_does_not_contain_generated_analysis_fields() -> None:
    """
    The scorecard is investor configuration, not analysis output.

    Generated fields such as score, confidence, evidence, risks and
    recommendation must not be accepted by the configuration model.
    """

    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    for dimension in payload["dimensions"]:
        assert "score" not in dimension
        assert "confidence" not in dimension
        assert "evidence" not in dimension
        assert "risks" not in dimension
        assert "recommendation" not in dimension


def test_duplicate_dimension_ids_are_rejected() -> None:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    payload["dimensions"][1]["id"] = payload["dimensions"][0]["id"]

    with pytest.raises(ValidationError):
        InvestmentScorecard.model_validate(payload)


def test_invalid_weight_total_is_rejected() -> None:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    payload["dimensions"][0]["weight"] = 16

    with pytest.raises(ValidationError):
        InvestmentScorecard.model_validate(payload)


def test_invalid_weight_range_is_rejected() -> None:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    payload["dimensions"][0]["weight"] = -1

    with pytest.raises(ValidationError):
        InvestmentScorecard.model_validate(payload)


def test_extra_dimension_is_rejected() -> None:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    payload["dimensions"].append(payload["dimensions"][0].copy())

    with pytest.raises(ValidationError):
        InvestmentScorecard.model_validate(payload)


def test_extra_configuration_field_is_rejected() -> None:
    with RESTOMART_SCORECARD.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    payload["unexpected_field"] = "should not be accepted"

    with pytest.raises(ValidationError):
        InvestmentScorecard.model_validate(payload)

def test_all_dimensions_have_distinct_evaluation_objectives() -> None:
    scorecard = load_restomart_scorecard()

    objectives = [
        dimension.evaluation_spec.objective
        for dimension in scorecard.dimensions
    ]

    assert len(objectives) == 10
    assert len(set(objectives)) == 10


def test_all_dimensions_have_evidence_requirements() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        assert len(dimension.evaluation_spec.evidence_required) >= 1


def test_all_dimensions_have_positive_and_negative_signals() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        spec = dimension.evaluation_spec

        assert len(spec.positive_signals) >= 1
        assert len(spec.negative_signals) >= 1


def test_all_dimensions_have_do_not_assume_constraints() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        assert len(dimension.evaluation_spec.do_not_assume) >= 1


def test_all_dimensions_have_complete_score_bands() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        guidance = dimension.evaluation_spec.scoring_guidance

        assert guidance.score_90_100
        assert guidance.score_75_89
        assert guidance.score_60_74
        assert guidance.score_40_59
        assert guidance.score_0_39


def test_missing_information_is_explicitly_distinguished_from_negative_evidence() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        spec = dimension.evaluation_spec

        # The contract must explicitly tell the AI what it must not assume.
        assert spec.do_not_assume


def test_financial_health_preserves_deterministic_metric_authority() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "financial_health"
    )

    text = " ".join(dimension.evaluation_spec.do_not_assume).lower()
    notes = dimension.investor_preferences.notes.lower()

    assert "revenue does not prove profitability" in text
    assert "deterministic" in notes


def test_valuation_does_not_equate_low_price_with_good_investment() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "valuation_deal_terms"
    )

    assumptions = " ".join(
        dimension.evaluation_spec.do_not_assume
    ).lower()

    assert "low valuation is not automatically attractive" in assumptions
    assert "high valuation is not automatically unattractive" in assumptions


def test_market_does_not_treat_founder_tam_as_fact() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "market_tam"
    )

    assumptions = " ".join(
        dimension.evaluation_spec.do_not_assume
    ).lower()

    assert "founder-provided tam" in assumptions


def test_unit_economics_missing_data_is_not_automatically_negative() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "unit_economics_margins"
    )

    assumptions = " ".join(
        dimension.evaluation_spec.do_not_assume
    ).lower()

    assert "missing cac is not proof of high cac" in assumptions
    assert "missing ltv is not proof of poor ltv" in assumptions


def test_governance_missing_sha_is_not_automatically_negative() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "governance_cap_table"
    )

    assumptions = " ".join(
        dimension.evaluation_spec.do_not_assume
    ).lower()

    assert "missing sha is not proof of an unfavorable sha" in assumptions


def test_risk_dimension_does_not_equate_absence_of_risk_with_no_risk() -> None:
    scorecard = load_restomart_scorecard()

    dimension = next(
        item
        for item in scorecard.dimensions
        if item.id == "risk_exit_potential"
    )

    assumptions = " ".join(
        dimension.evaluation_spec.do_not_assume
    ).lower()

    assert "absence of identified risk is not proof of absence of risk" in assumptions


def test_each_dimension_has_investor_priority() -> None:
    scorecard = load_restomart_scorecard()

    for dimension in scorecard.dimensions:
        assert dimension.investor_preferences.priority


def test_day_1_2_weights_remain_unchanged() -> None:
    scorecard = load_restomart_scorecard()

    expected_weights = {
        "founder_team": Decimal("15"),
        "market_tam": Decimal("10"),
        "product_pmf": Decimal("10"),
        "technology_ip_moat": Decimal("10"),
        "commercial_traction": Decimal("15"),
        "unit_economics_margins": Decimal("10"),
        "financial_health": Decimal("5"),
        "governance_cap_table": Decimal("10"),
        "valuation_deal_terms": Decimal("10"),
        "risk_exit_potential": Decimal("5"),
    }

    actual_weights = {
        dimension.id: dimension.weight
        for dimension in scorecard.dimensions
    }

    assert actual_weights == expected_weights

def test_risk_severity_contract() -> None:
    assert RiskSeverity.LOW.value == "low"
    assert RiskSeverity.MEDIUM.value == "medium"
    assert RiskSeverity.HIGH.value == "high"
    assert RiskSeverity.CRITICAL.value == "critical"


def test_dimension_evidence_contract() -> None:
    evidence = DimensionEvidence(
        evidence_ref="financials_2025",
        observation="Revenue was INR 2.68 crore.",
        source_type="financial_document",
    )

    assert evidence.evidence_ref == "financials_2025"
    assert evidence.observation
    assert evidence.source_type


def test_dimension_risk_contract() -> None:
    risk = DimensionRisk(
        risk="Customer concentration",
        severity=RiskSeverity.MEDIUM,
        impact="Potential revenue volatility.",
        evidence_refs=["customer_data_2025"],
    )

    assert risk.risk == "Customer concentration"
    assert risk.severity == RiskSeverity.MEDIUM
    assert risk.evidence_refs == ["customer_data_2025"]


def test_dimension_evaluation_contract() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=Decimal("72"),
        confidence=Decimal("82"),
        evidence=[
            DimensionEvidence(
                evidence_ref="financials_2025",
                observation="Revenue was INR 2.68 crore.",
                source_type="financial_document",
            ),
        ],
        positive_observations=[
            "Meaningful revenue traction.",
        ],
        risk_observations=[
            DimensionRisk(
                risk="Customer concentration",
                severity=RiskSeverity.MEDIUM,
                impact="Potential revenue volatility.",
                evidence_refs=["financials_2025"],
            ),
        ],
        missing_information=[
            "Customer retention metrics.",
        ],
        reasoning=(
            "Revenue demonstrates commercial traction, "
            "while retention data remains unavailable."
        ),
    )

    assert evaluation.dimension_id == "commercial_traction"
    assert evaluation.score == Decimal("72")
    assert evaluation.confidence == Decimal("82")
    assert len(evaluation.evidence) == 1
    assert len(evaluation.risk_observations) == 1
    assert len(evaluation.missing_information) == 1


def test_dimension_score_boundary_contract() -> None:
    for score in (
        Decimal("0"),
        Decimal("50"),
        Decimal("100"),
    ):
        result = DimensionEvaluation(
            dimension_id="market_tam",
            score=score,
            confidence=Decimal("100"),
            reasoning="Contract test.",
        )

        assert result.score == score


def test_dimension_score_below_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("-0.01"),
            confidence=Decimal("50"),
            reasoning="Invalid score.",
        )


def test_dimension_score_above_100_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("100.01"),
            confidence=Decimal("50"),
            reasoning="Invalid score.",
        )


def test_dimension_confidence_bounds() -> None:
    for confidence in (
        Decimal("0"),
        Decimal("50"),
        Decimal("100"),
    ):
        result = DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("70"),
            confidence=confidence,
            reasoning="Contract test.",
        )

        assert result.confidence == confidence


def test_dimension_confidence_below_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("70"),
            confidence=Decimal("-1"),
            reasoning="Invalid confidence.",
        )


def test_dimension_confidence_above_100_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("70"),
            confidence=Decimal("101"),
            reasoning="Invalid confidence.",
        )


def test_missing_information_is_independent_of_score() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="unit_economics_margins",
        score=Decimal("72"),
        confidence=Decimal("55"),
        missing_information=[
            "CAC",
            "LTV",
        ],
        reasoning="Promising evidence but incomplete economics.",
    )

    assert evaluation.score == Decimal("72")
    assert evaluation.confidence == Decimal("55")
    assert len(evaluation.missing_information) == 2


def test_risk_requires_valid_evidence_reference() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="commercial_traction",
            score=Decimal("72"),
            confidence=Decimal("80"),
            risk_observations=[
                DimensionRisk(
                    risk="Customer concentration",
                    severity=RiskSeverity.HIGH,
                    impact="Revenue concentration risk.",
                    evidence_refs=["unknown_evidence"],
                ),
            ],
            reasoning="Invalid evidence reference.",
        )


def test_risk_without_evidence_reference_is_allowed() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="market_tam",
        score=Decimal("65"),
        confidence=Decimal("60"),
        risk_observations=[
            DimensionRisk(
                risk="Market uncertainty",
                severity=RiskSeverity.MEDIUM,
                impact="Market size requires validation.",
            ),
        ],
        reasoning="Risk is identified but no direct evidence reference exists.",
    )

    assert len(evaluation.risk_observations) == 1


def test_extra_dimension_evaluation_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvaluation(
            dimension_id="market_tam",
            score=Decimal("70"),
            confidence=Decimal("80"),
            reasoning="Contract test.",
            weight=Decimal("10"),
        )


def test_dimension_scorecard_result_calculates_weighted_score() -> None:
    result = DimensionScorecardResult(
        dimension_id="commercial_traction",
        score=Decimal("72"),
        confidence=Decimal("82"),
        weight=Decimal("15"),
        weighted_score=Decimal("10.8"),
    )

    assert result.weighted_score == Decimal("10.8")


def test_dimension_scorecard_result_rejects_incorrect_weighted_score() -> None:
    with pytest.raises(ValidationError):
        DimensionScorecardResult(
            dimension_id="commercial_traction",
            score=Decimal("72"),
            confidence=Decimal("82"),
            weight=Decimal("15"),
            weighted_score=Decimal("72"),
        )


def test_dimension_scorecard_weight_bounds() -> None:
    with pytest.raises(ValidationError):
        DimensionScorecardResult(
            dimension_id="commercial_traction",
            score=Decimal("72"),
            confidence=Decimal("82"),
            weight=Decimal("101"),
            weighted_score=Decimal("72.72"),
        )


def test_llm_evaluation_does_not_contain_weight() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="valuation_deal_terms",
        score=Decimal("60"),
        confidence=Decimal("70"),
        reasoning="Valuation requires additional context.",
    )

    assert "weight" not in evaluation.model_dump()


def test_score_and_confidence_are_independent() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="founder_team",
        score=Decimal("90"),
        confidence=Decimal("40"),
        reasoning="Strong evidence direction but incomplete validation.",
    )

    assert evaluation.score == Decimal("90")
    assert evaluation.confidence == Decimal("40")

def test_dimension_evidence_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionEvidence(
            evidence_ref="financials_2025",
            observation="Revenue was INR 2.68 crore.",
            source_type="financial_document",
            score=80,
        )

def test_dimension_risk_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionRisk(
            risk="Customer concentration",
            severity=RiskSeverity.MEDIUM,
            impact="Potential revenue volatility.",
            risk_score=80,
        )

def test_dimension_risk_blank_evidence_reference_rejected() -> None:
    with pytest.raises(ValidationError):
        DimensionRisk(
            risk="Customer concentration",
            severity=RiskSeverity.MEDIUM,
            impact="Potential revenue volatility.",
            evidence_refs=["   "],
        )

def test_llm_evaluation_does_not_contain_recommendation() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=Decimal("72"),
        confidence=Decimal("82"),
        reasoning="Revenue traction is demonstrated.",
    )

    dumped = evaluation.model_dump()

    assert "recommendation" not in dumped
    assert "investment_recommendation" not in dumped

def test_llm_evaluation_does_not_contain_overall_score() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=Decimal("72"),
        confidence=Decimal("82"),
        reasoning="Revenue traction is demonstrated.",
    )

    dumped = evaluation.model_dump()

    assert "overall_score" not in dumped
    assert "weighted_score" not in dumped

def test_risk_and_missing_information_are_separate() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=Decimal("72"),
        confidence=Decimal("65"),
        evidence=[
            DimensionEvidence(
                evidence_ref="financials_2025",
                observation="Revenue was INR 2.68 crore.",
                source_type="financial_document",
            )
        ],
        risk_observations=[
            DimensionRisk(
                risk="Customer concentration",
                severity=RiskSeverity.HIGH,
                impact="Revenue may be exposed to a concentrated customer base.",
                evidence_refs=["financials_2025"],
            )
        ],
        missing_information=[
            "Customer retention metrics",
            "Customer acquisition cost",
        ],
        reasoning=(
            "Commercial traction is demonstrated, "
            "but concentration risk exists and retention "
            "information remains incomplete."
        ),
    )

    assert len(evaluation.risk_observations) == 1
    assert len(evaluation.missing_information) == 2

    assert evaluation.score == Decimal("72")
    assert evaluation.confidence == Decimal("65")

def test_high_confidence_does_not_imply_high_score() -> None:
    evaluation = DimensionEvaluation(
        dimension_id="governance_cap_table",
        score=Decimal("35"),
        confidence=Decimal("95"),
        reasoning=(
            "Available governance evidence clearly indicates "
            "significant governance concerns."
        ),
    )

    assert evaluation.score == Decimal("35")
    assert evaluation.confidence == Decimal("95")


def test_dimension_scorecard_result_zero_weight() -> None:
    result = DimensionScorecardResult(
        dimension_id="financial_health",
        score=Decimal("90"),
        confidence=Decimal("90"),
        weight=Decimal("0"),
        weighted_score=Decimal("0"),
    )

    assert result.weighted_score == Decimal("0")


def test_dimension_scorecard_result_full_weight() -> None:
    result = DimensionScorecardResult(
        dimension_id="financial_health",
        score=Decimal("90"),
        confidence=Decimal("90"),
        weight=Decimal("100"),
        weighted_score=Decimal("90"),
    )

    assert result.weighted_score == Decimal("90")

def test_dimension_scorecard_result_uses_percentage_weight() -> None:
    result = DimensionScorecardResult(
        dimension_id="commercial_traction",
        score=Decimal("80"),
        confidence=Decimal("90"),
        weight=Decimal("15"),
        weighted_score=Decimal("12"),
    )

    assert result.weighted_score == (
        result.score * result.weight / Decimal("100")
    )


def test_scorecard_contains_evaluation_principles(
    scorecard,
):
    principles = scorecard.evaluation_principles

    assert (
        principles
        .evidence_semantics
        .missing_information_is_not_negative_evidence
        is True
    )

    assert (
        principles
        .evidence_semantics
        .absence_of_evidence_is_not_evidence_of_negative_condition
        is True
    )

    assert (
        principles
        .evidence_semantics
        .risk_requires_supporting_evidence
        is True
    )

    assert len(
        principles
        .missing_information_rule
        .rules
    ) >= 4

def test_multi_dimension_evaluation_accepts_unique_dimensions():
    evaluations = [
        DimensionEvaluation(
            dimension_id="founder_team",
            score=80,
            confidence=90,
            evidence=[],
            positive_observations=[
                "Experienced founding team."
            ],
            risk_observations=[],
            missing_information=[],
            reasoning="Strong founder evidence.",
        ),
        DimensionEvaluation(
            dimension_id="market_tam",
            score=70,
            confidence=75,
            evidence=[],
            positive_observations=[
                "Large addressable market."
            ],
            risk_observations=[],
            missing_information=[],
            reasoning="Market opportunity appears meaningful.",
        ),
    ]

    result = MultiDimensionEvaluation(
        scorecard_version=1,
        startup_name="RestoMart",
        evaluations=evaluations,
    )

    assert result.scorecard_version == 1
    assert result.startup_name == "RestoMart"
    assert len(result.evaluations) == 2

    assert [
        evaluation.dimension_id
        for evaluation in result.evaluations
    ] == [
        "founder_team",
        "market_tam",
    ]

def test_multi_dimension_evaluation_rejects_duplicate_dimensions():
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=60,
        confidence=70,
        evidence=[],
        positive_observations=[
            "Meaningful revenue."
        ],
        risk_observations=[],
        missing_information=[
            "Customer retention",
        ],
        reasoning=(
            "Revenue is available but retention "
            "information is missing."
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate dimension evaluations",
    ):
        MultiDimensionEvaluation(
            scorecard_version=1,
            startup_name="RestoMart",
            evaluations=[
                evaluation,
                evaluation,
            ],
        )

def test_multi_dimension_evaluation_contains_only_evaluations():
    result = MultiDimensionEvaluation(
        scorecard_version=1,
        startup_name="RestoMart",
        evaluations=[],
    )

    payload = result.model_dump()

    assert "score" not in payload
    assert "overall_score" not in payload
    assert "weighted_score" not in payload
    assert "recommendation" not in payload

def test_multi_dimension_evaluation_preserves_dimension_details():
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=60,
        confidence=70,
        evidence=[
            {
                "evidence_ref": "financials_2025",
                "observation": "Revenue is INR 2.68 crore.",
                "source_type": "financial_document",
            }
        ],
        positive_observations=[
            "Meaningful revenue."
        ],
        risk_observations=[],
        missing_information=[
            "Customer retention",
        ],
        reasoning=(
            "Revenue provides evidence of commercial traction."
        ),
    )

    result = MultiDimensionEvaluation(
        scorecard_version=1,
        startup_name="RestoMart",
        evaluations=[evaluation],
    )

    stored = result.evaluations[0]

    assert stored.dimension_id == "commercial_traction"
    assert stored.score == 60
    assert stored.confidence == 70
    assert len(stored.evidence) == 1
    assert len(stored.missing_information) == 1
    assert stored.missing_information[0].item == (
        "Customer retention"
    )
    assert stored.missing_information[0].reason == ""

    assert stored.risk_observations == []

def test_missing_information_accepts_structured_items():
    evaluation = DimensionEvaluation(
        dimension_id="founder_team",
        score=70,
        confidence=80,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[
            {
                "item": "Founder ownership",
                "reason": (
                    "Needed to assess founder alignment."
                ),
            }
        ],
        reasoning="Founder evidence is incomplete.",
    )

    assert len(evaluation.missing_information) == 1

    item = evaluation.missing_information[0]

    assert item.item == "Founder ownership"
    assert item.reason == (
        "Needed to assess founder alignment."
    )


def test_missing_information_accepts_legacy_strings():
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=60,
        confidence=70,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[
            "Customer retention",
            "Revenue growth",
        ],
        reasoning="Commercial evidence is incomplete.",
    )

    assert [
        item.item
        for item in evaluation.missing_information
    ] == [
        "Customer retention",
        "Revenue growth",
    ]

    assert [
        item.reason
        for item in evaluation.missing_information
    ] == [
        "",
        "",
    ]


def test_missing_information_accepts_mixed_items():
    evaluation = DimensionEvaluation(
        dimension_id="commercial_traction",
        score=60,
        confidence=70,
        evidence=[],
        positive_observations=[],
        risk_observations=[],
        missing_information=[
            "Customer retention",
            {
                "item": "Customer concentration",
                "reason": (
                    "Needed to assess revenue concentration."
                ),
            },
        ],
        reasoning="Commercial evidence is incomplete.",
    )

    assert evaluation.missing_information[0].item == (
        "Customer retention"
    )

    assert evaluation.missing_information[0].reason == ""

    assert evaluation.missing_information[1].item == (
        "Customer concentration"
    )

    assert evaluation.missing_information[1].reason == (
        "Needed to assess revenue concentration."
    )


