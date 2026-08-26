from __future__ import annotations

import json

import pytest

from app.models.investment_scorecard import DimensionEvaluation
from app.services.investment_scorecard_parser import (
    InvestmentScorecardParser,
)


def valid_payload() -> dict:
    return {
        "dimension_id": "commercial_traction",
        "score": 72,
        "confidence": 84,
        "evidence": [
            {
                "evidence_ref": "financials_2025",
                "observation": "Revenue is INR 2.68 crore.",
                "source_type": "financial_document",
            }
        ],
        "positive_observations": [
            "Demonstrated revenue traction."
        ],
        "risk_observations": [
            {
                "risk": "Customer concentration",
                "severity": "medium",
                "impact": (
                    "Revenue may be exposed to "
                    "a concentrated customer base."
                ),
                "evidence_refs": [
                    "financials_2025"
                ],
            }
        ],
        "missing_information": [
            "Customer retention metrics"
        ],
        "reasoning": (
            "Revenue demonstrates commercial traction, "
            "while retention information remains incomplete."
        ),
    }


def test_parser_accepts_valid_json() -> None:
    result = InvestmentScorecardParser.parse(
        json.dumps(valid_payload())
    )

    assert isinstance(result, DimensionEvaluation)
    assert result.dimension_id == "commercial_traction"
    assert result.score == 72
    assert result.confidence == 84


def test_parser_accepts_missing_information_without_lowering_score() -> None:
    payload = valid_payload()

    payload["score"] = 75
    payload["missing_information"] = [
        "CAC",
        "Retention",
    ]

    result = InvestmentScorecardParser.parse(
        json.dumps(payload)
    )

    assert result.score == 75
    assert len(result.missing_information) == 2


def test_parser_rejects_invalid_json() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        InvestmentScorecardParser.parse(
            "{not valid json}"
        )


def test_parser_rejects_score_above_100() -> None:
    payload = valid_payload()
    payload["score"] = 101

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_negative_confidence() -> None:
    payload = valid_payload()
    payload["confidence"] = -1

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


@pytest.mark.parametrize(
    "severity",
    ["unknown", "severe", "urgent", ""],
)
def test_parser_rejects_invalid_risk_severity(
    severity: str,
) -> None:
    payload = valid_payload()
    payload["risk_observations"][0]["severity"] = severity

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_unknown_risk_evidence_reference() -> None:
    payload = valid_payload()

    payload["risk_observations"][0]["evidence_refs"] = [
        "does_not_exist"
    ]

    with pytest.raises(
        ValueError,
        match="Risk evidence_refs",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_weight() -> None:
    payload = valid_payload()
    payload["weight"] = 15

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_weighted_score() -> None:
    payload = valid_payload()
    payload["weighted_score"] = 10.8

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_overall_score() -> None:
    payload = valid_payload()
    payload["overall_score"] = 72

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_recommendation() -> None:
    payload = valid_payload()
    payload["recommendation"] = "invest"

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )


def test_parser_rejects_missing_reasoning() -> None:
    payload = valid_payload()
    del payload["reasoning"]

    with pytest.raises(
        ValueError,
        match="Invalid investment dimension evaluation",
    ):
        InvestmentScorecardParser.parse(
            json.dumps(payload)
        )

def test_parser_accepts_qwen_thinking_wrapper():
    response = """
    <think>

    </think>

    {
      "dimension_id": "commercial_traction",
      "score": 72,
      "confidence": 84,
      "evidence": [],
      "positive_observations": [
        "Meaningful revenue traction."
      ],
      "risk_observations": [],
      "missing_information": [
        "Customer retention"
      ],
      "reasoning": "Revenue provides evidence of traction."
    }
    """

    result = InvestmentScorecardParser.parse(
        response
    )

    assert result.dimension_id == (
        "commercial_traction"
    )

    assert result.score == 72
    assert result.confidence == 84

def test_parser_rejects_prose_around_json():
    response = """
    Here is my investment analysis:

    {
      "dimension_id": "commercial_traction",
      "score": 72,
      "confidence": 84,
      "evidence": [],
      "positive_observations": [],
      "risk_observations": [],
      "missing_information": [],
      "reasoning": "Revenue provides evidence of traction."
    }
    """

    with pytest.raises(ValueError):
        InvestmentScorecardParser.parse(
            response
        )


def test_parser_accepts_qwen_thinking_wrapper():
    response = """
    <think>

    </think>

    {
      "dimension_id": "commercial_traction",
      "score": 72,
      "confidence": 84,
      "evidence": [],
      "positive_observations": [
        "Meaningful revenue traction."
      ],
      "risk_observations": [],
      "missing_information": [
        "Customer retention"
      ],
      "reasoning": "Revenue provides evidence of traction."
    }
    """

    result = InvestmentScorecardParser.parse(
        response
    )

    assert result.dimension_id == (
        "commercial_traction"
    )

    assert result.score == 72
    assert result.confidence == 84

def test_parser_rejects_prose_around_json():
    response = """
    Here is my investment analysis:

    {
      "dimension_id": "commercial_traction",
      "score": 72,
      "confidence": 84,
      "evidence": [],
      "positive_observations": [],
      "risk_observations": [],
      "missing_information": [],
      "reasoning": "Revenue provides evidence of traction."
    }
    """

    with pytest.raises(ValueError):
        InvestmentScorecardParser.parse(response)
