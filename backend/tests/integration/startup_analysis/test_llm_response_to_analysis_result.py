"""
C.7.7.6.4 — LLM Response -> StartupAnalysisResult Handshake

Validates the production response boundary:

    LLMResponse.text
        -> StartupAnalysisParser
        -> StartupAnalysisResult

These tests intentionally do NOT invoke Qwen.

The real production StartupAnalysisParser is used.
"""

from __future__ import annotations

import json

import pytest

from app.schemas.analysis import StartupAnalysisResult
from app.services.startup_analysis_parser import StartupAnalysisParser


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _build_parser() -> StartupAnalysisParser:
    """Create the real production parser."""
    return StartupAnalysisParser()


def _valid_result_payload() -> dict:
    """
    Representative response matching the production startup-analysis
    output contract.
    """
    return {
        "company_overview": (
            "RestoMart is a B2B food-supply and restaurant "
            "technology company operating in India."
        ),
        "founder_assessment": (
            "The founding team has CEO, COO, and CBO roles, "
            "but detailed backgrounds are not provided."
        ),
        "product_assessment": (
            "The company operates a procurement marketplace "
            "with supply-chain and rapid-delivery capabilities."
        ),
        "market_assessment": (
            "The company targets the Indian B2B food-supply market, "
            "while market-size and competitor information remain limited."
        ),
        "traction_assessment": (
            "Reported revenue demonstrates early commercial traction."
        ),
        "financial_assessment": (
            "The available information indicates positive operating "
            "traction and a stated 24-month runway."
        ),
        "valuation_assessment": (
            "The available source material contains valuation information "
            "that requires verification."
        ),
        "business_model_assessment": (
            "The business model is B2B food supply and restaurant procurement."
        ),
        "competitive_assessment": (
            "Competitive positioning cannot be fully assessed from "
            "the supplied information."
        ),
        "strengths": [
            "Early revenue generation",
            "B2B procurement marketplace",
            "Established operating model",
        ],
        "risks": [
            "Customer concentration",
            "Limited competitor information",
            "Unclear unit economics",
        ],
        "missing_information": [
            "Founder backgrounds",
            "Market size",
            "Detailed competitive positioning",
        ],
        "key_observations": [
            "The company has early commercial traction.",
            "The procurement model has operational complexity.",
            "Further diligence is required on market and economics.",
        ],
        "investment_thesis": (
            "RestoMart demonstrates early traction and a defined B2B "
            "business model, but additional diligence is required."
        ),
        "preliminary_recommendation": "needs_further_diligence",
    }


def _response_text(payload: dict | None = None) -> str:
    """Serialize a response payload exactly as an LLM would return it."""
    return json.dumps(
        payload if payload is not None else _valid_result_payload(),
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Basic response -> result handshake
# ---------------------------------------------------------------------------


def test_valid_llm_response_produces_startup_analysis_result() -> None:
    """
    A valid provider response must cross the parser boundary and produce
    the canonical StartupAnalysisResult.
    """
    parser = _build_parser()

    result = parser.parse(
        _response_text()
    )

    assert isinstance(result, StartupAnalysisResult)


def test_all_result_fields_survive_response_boundary() -> None:
    """
    Verify that every canonical result field survives parsing.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    result = parser.parse(
        _response_text(payload)
    )

    assert result.company_overview == payload["company_overview"]
    assert result.founder_assessment == payload["founder_assessment"]
    assert result.product_assessment == payload["product_assessment"]
    assert result.market_assessment == payload["market_assessment"]
    assert result.traction_assessment == payload["traction_assessment"]
    assert result.financial_assessment == payload["financial_assessment"]
    assert result.valuation_assessment == payload["valuation_assessment"]
    assert result.business_model_assessment == payload[
        "business_model_assessment"
    ]
    assert result.competitive_assessment == payload[
        "competitive_assessment"
    ]

    assert result.strengths == payload["strengths"]
    assert result.risks == payload["risks"]
    assert result.missing_information == payload[
        "missing_information"
    ]
    assert result.key_observations == payload[
        "key_observations"
    ]

    assert result.investment_thesis == payload[
        "investment_thesis"
    ]

    assert result.preliminary_recommendation == (
        payload["preliminary_recommendation"]
    )


# ---------------------------------------------------------------------------
# Null handling
# ---------------------------------------------------------------------------


def test_null_narrative_fields_survive_as_none() -> None:
    """
    The LLM is explicitly allowed to return null where information is
    insufficient.

    The parser must preserve that semantic rather than manufacturing text.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    nullable_fields = (
        "company_overview",
        "founder_assessment",
        "product_assessment",
        "market_assessment",
        "traction_assessment",
        "financial_assessment",
        "valuation_assessment",
        "business_model_assessment",
        "competitive_assessment",
        "investment_thesis",
    )

    for field in nullable_fields:
        payload[field] = None

    result = parser.parse(
        _response_text(payload)
    )

    for field in nullable_fields:
        assert getattr(result, field) is None


def test_empty_lists_are_preserved() -> None:
    """
    Empty structured lists are valid response values and must remain empty.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    payload["strengths"] = []
    payload["risks"] = []
    payload["missing_information"] = []
    payload["key_observations"] = []

    result = parser.parse(
        _response_text(payload)
    )

    assert result.strengths == []
    assert result.risks == []
    assert result.missing_information == []
    assert result.key_observations == []


# ---------------------------------------------------------------------------
# Recommendation contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recommendation",
    (
        "insufficient_information",
        "promising",
        "needs_further_diligence",
        "concerns",
    ),
)
def test_allowed_recommendations_cross_response_boundary(
    recommendation: str,
) -> None:
    """
    Every recommendation explicitly allowed by the production contract
    must parse successfully.
    """
    parser = _build_parser()

    payload = _valid_result_payload()
    payload["preliminary_recommendation"] = recommendation

    result = parser.parse(
        _response_text(payload)
    )

    assert result.preliminary_recommendation == recommendation


def test_invalid_recommendation_is_rejected() -> None:
    """
    The parser/result contract must reject an unsupported recommendation
    rather than silently accepting arbitrary model output.
    """
    parser = _build_parser()

    payload = _valid_result_payload()
    payload["preliminary_recommendation"] = "invest_now"

    with pytest.raises(Exception):
        parser.parse(
            _response_text(payload)
        )


# ---------------------------------------------------------------------------
# JSON boundary
# ---------------------------------------------------------------------------


def test_markdown_code_fence_response_is_rejected_or_normalized() -> None:
    """
    The production prompt explicitly asks the LLM not to return Markdown
    code fences.

    This test documents the actual parser behavior rather than assuming
    that fences are supported.
    """
    parser = _build_parser()

    response = (
        "```json\n"
        f"{_response_text()}\n"
        "```"
    )

    try:
        result = parser.parse(response)
    except Exception:
        # Rejection is acceptable because the prompt contract requires
        # raw JSON rather than Markdown.
        return

    # If the production parser deliberately normalizes fences, ensure the
    # resulting object is still canonical.
    assert isinstance(result, StartupAnalysisResult)


def test_malformed_json_is_rejected() -> None:
    """
    A malformed provider response must never become a partially populated
    StartupAnalysisResult.
    """
    parser = _build_parser()

    malformed = """
    {
        "company_overview": "RestoMart",
        "preliminary_recommendation":
    """

    with pytest.raises(Exception):
        parser.parse(malformed)


def test_non_object_json_is_rejected() -> None:
    """
    Arrays, strings, and scalar JSON values are not valid startup-analysis
    responses.
    """
    parser = _build_parser()

    invalid_responses = (
        "[]",
        '"startup analysis"',
        "123",
        "true",
        "null",
    )

    for response in invalid_responses:
        with pytest.raises(Exception):
            parser.parse(response)


# ---------------------------------------------------------------------------
# No fabricated information
# ---------------------------------------------------------------------------


def test_missing_information_remains_explicit() -> None:
    """
    The response parser must preserve the model's explicit
    missing_information list.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    payload["missing_information"] = [
        "Founder experience",
        "Market size",
        "Competitor analysis",
    ]

    result = parser.parse(
        _response_text(payload)
    )

    assert result.missing_information == [
        "Founder experience",
        "Market size",
        "Competitor analysis",
    ]


def test_parser_does_not_create_missing_information() -> None:
    """
    If the model returns an empty missing_information list, the parser must
    not invent additional diligence items.
    """
    parser = _build_parser()

    payload = _valid_result_payload()
    payload["missing_information"] = []

    result = parser.parse(
        _response_text(payload)
    )

    assert result.missing_information == []


# ---------------------------------------------------------------------------
# Structured list preservation
# ---------------------------------------------------------------------------


def test_strengths_are_preserved_in_order() -> None:
    """
    Ordered model output must remain ordered after parsing.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    payload["strengths"] = [
        "Strength A",
        "Strength B",
        "Strength C",
    ]

    result = parser.parse(
        _response_text(payload)
    )

    assert result.strengths == [
        "Strength A",
        "Strength B",
        "Strength C",
    ]


def test_risks_are_preserved_in_order() -> None:
    """
    Ordered risk output must remain ordered after parsing.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    payload["risks"] = [
        "Risk A",
        "Risk B",
        "Risk C",
    ]

    result = parser.parse(
        _response_text(payload)
    )

    assert result.risks == [
        "Risk A",
        "Risk B",
        "Risk C",
    ]


def test_key_observations_are_preserved_in_order() -> None:
    """
    Ordered observations must remain ordered after parsing.
    """
    parser = _build_parser()

    payload = _valid_result_payload()

    payload["key_observations"] = [
        "Observation A",
        "Observation B",
        "Observation C",
    ]

    result = parser.parse(
        _response_text(payload)
    )

    assert result.key_observations == [
        "Observation A",
        "Observation B",
        "Observation C",
    ]
