import json
from pathlib import Path

import pytest

from app.models.investment_scorecard import InvestmentScorecard
from app.prompt.investment_scorecard import (
    build_dimension_evaluation_messages,
    build_dimension_evaluation_prompt,
    build_scorecard_system_prompt,
)


SCORECARD_PATH = (
    Path(__file__).parents[2]
    / "data"
    / "real_startups"
    / "restomart"
    / "investment_scorecard.json"
)


@pytest.fixture
def scorecard() -> InvestmentScorecard:
    data = json.loads(
        SCORECARD_PATH.read_text(encoding="utf-8")
    )

    return InvestmentScorecard.model_validate(data)


@pytest.fixture
def evidence() -> list[dict]:
    return [
        {
            "evidence_ref": "financials_2025",
            "observation": (
                "Revenue is INR 2.68 crore."
            ),
            "source_type": "financial_document",
        },
        {
            "evidence_ref": "founders_2025",
            "observation": (
                "Three founders are identified."
            ),
            "source_type": "startup_database",
        },
    ]


def test_system_prompt_contains_core_rules():
    prompt = build_scorecard_system_prompt()

    assert "Do not invent facts" in prompt
    assert "Missing information is NOT negative evidence" in prompt
    assert "Separate risks from missing information" in prompt
    assert "Do NOT apply investment weight" in prompt
    assert "Do NOT calculate weighted score" in prompt
    assert "Do NOT produce an overall investment recommendation" in prompt


def test_system_prompt_requires_evidence_based_scoring():
    prompt = build_scorecard_system_prompt()

    assert "Score this dimension from 0 to 100" in prompt
    assert "Use the supplied scoring guidance" in prompt
    assert "Confidence must be from 0 to 100" in prompt


def test_dimension_prompt_contains_startup(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert "RestoMart" in prompt
    assert "commercial_traction" in prompt
    assert "financials_2025" in prompt


def test_dimension_prompt_contains_dimension_specification(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert "Revenue" in prompt
    assert "Customer concentration" in prompt
    assert "Missing retention data" in prompt


def test_dimension_prompt_contains_do_not_assume_rules(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert (
        "Missing retention data is not automatically "
        "evidence of poor retention"
    ) in prompt


def test_dimension_prompt_contains_scoring_guidance(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert (
        "Meaningful but still developing commercial traction."
        in prompt
    )


def test_dimension_prompt_contains_investor_profile(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert "Dinesh" in prompt
    assert "Missing information must not automatically" in prompt


def test_dimension_weight_is_not_sent_to_llm(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    dimension = payload["dimension"]

    assert "weight" not in dimension


def test_dimension_weight_is_not_in_dimension_payload(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="founder_team",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert "weight" not in payload["dimension"]


def test_required_output_contains_no_weight(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="market_tam",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert "weight" not in payload["required_output"]
    assert "weighted_score" not in payload["required_output"]


def test_required_output_contains_risk_structure(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    risk = payload["required_output"]["risk_observations"][0]

    assert "risk" in risk
    assert "severity" in risk
    assert "impact" in risk
    assert "evidence_refs" in risk


def test_required_output_contains_missing_information(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="unit_economics_margins",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert (
        "missing_information"
        in payload["required_output"]
    )


def test_unknown_dimension_is_rejected(
    scorecard,
    evidence,
):
    with pytest.raises(ValueError, match="Unknown investment dimension"):
        build_dimension_evaluation_prompt(
            scorecard=scorecard,
            dimension_id="does_not_exist",
            startup_name="RestoMart",
            startup_evidence=evidence,
        )


def test_empty_evidence_is_allowed(scorecard):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="market_tam",
        startup_name="RestoMart",
        startup_evidence=[],
    )

    payload = json.loads(prompt)

    assert payload["evidence"] == []


def test_evidence_is_preserved_exactly(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert payload["evidence"] == evidence


def test_messages_contain_system_and_user(
    scorecard,
    evidence,
):
    messages = build_dimension_evaluation_messages(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_messages_use_scorecard_system_prompt(
    scorecard,
    evidence,
):
    messages = build_dimension_evaluation_messages(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert messages[0]["content"] == (
        build_scorecard_system_prompt()
    )


def test_messages_are_llm_compatible(
    scorecard,
    evidence,
):
    messages = build_dimension_evaluation_messages(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    for message in messages:
        assert set(message.keys()) == {
            "role",
            "content",
        }
        assert isinstance(message["role"], str)
        assert isinstance(message["content"], str)
        assert message["content"]


def test_prompt_is_valid_json(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert isinstance(payload, dict)
    assert payload["startup"]["name"] == "RestoMart"


def test_prompt_is_dimension_specific(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="valuation_deal_terms",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    payload = json.loads(prompt)

    assert (
        payload["dimension"]["id"]
        == "valuation_deal_terms"
    )

    assert (
        payload["required_output"]["dimension_id"]
        == "valuation_deal_terms"
    )

def test_dimension_prompt_contains_evaluation_principles(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    assert "evaluation_principles" in prompt

    assert (
        "missing_information_is_not_negative_evidence"
        in prompt
    )

    assert (
        "absence_of_evidence_is_not_evidence_of_negative_condition"
        in prompt
    )

    assert (
        "risk_requires_supporting_evidence"
        in prompt
    )

    assert (
        "Do not convert missing information into a risk"
        in prompt
    )

    assert (
        "Do not use absence of evidence as evidence"
        in prompt
    )

def test_dimension_prompt_contains_all_missing_information_rules(
    scorecard,
    evidence,
):
    prompt = build_dimension_evaluation_prompt(
        scorecard=scorecard,
        dimension_id="commercial_traction",
        startup_name="RestoMart",
        startup_evidence=evidence,
    )

    for rule in (
        scorecard
        .evaluation_principles
        .missing_information_rule
        .rules
    ):
        assert rule in prompt
