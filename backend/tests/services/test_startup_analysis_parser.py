"""
Tests for structured startup-analysis response parsing.
"""

import json

import pytest

from app.schemas.analysis import StartupAnalysisResult
from app.services.startup_analysis_parser import (
    StartupAnalysisParseError,
    StartupAnalysisParser,
)


@pytest.fixture
def parser() -> StartupAnalysisParser:
    return StartupAnalysisParser()


def valid_payload() -> dict:
    return {
        "company_overview": "B2B SaaS startup.",
        "founder_assessment": "Strong domain expertise.",
        "product_assessment": "Clear product value proposition.",
        "market_assessment": "Large addressable market.",
        "traction_assessment": "Strong revenue growth.",
        "financial_assessment": "Positive EBITDA.",
        "valuation_assessment": "Valuation requires diligence.",
        "business_model_assessment": "Recurring revenue.",
        "competitive_assessment": "Differentiated offering.",
        "strengths": [
            "Strong founders",
            "Good growth",
        ],
        "risks": [
            "High valuation",
        ],
        "missing_information": [
            "Customer concentration",
        ],
        "key_observations": [
            "Growth is strong.",
        ],
        "investment_thesis": (
            "Promising opportunity subject to diligence."
        ),
        "preliminary_recommendation": "promising",
    }


def test_parse_plain_json(parser):
    text = json.dumps(valid_payload())

    result = parser.parse(text)

    assert isinstance(result, StartupAnalysisResult)
    assert result.company_overview == "B2B SaaS startup."
    assert result.preliminary_recommendation == "promising"


def test_parse_json_code_fence(parser):
    text = f"""```json
{json.dumps(valid_payload())}
```"""

    result = parser.parse(text)

    assert result.preliminary_recommendation == "promising"


def test_parse_json_code_fence_without_language(parser):
    text = f"""```
{json.dumps(valid_payload())}
```"""

    result = parser.parse(text)

    assert result.company_overview == "B2B SaaS startup."


def test_parse_qwen_thinking_block(parser):
    text = f"""<think>
I should evaluate the startup carefully.
</think>

{json.dumps(valid_payload())}
"""

    result = parser.parse(text)

    assert result.preliminary_recommendation == "promising"


def test_parse_empty_qwen_thinking_block(parser):
    text = f"""<think>

</think>

{json.dumps(valid_payload())}
"""

    result = parser.parse(text)

    assert result.preliminary_recommendation == "promising"


def test_parse_surrounding_text(parser):
    text = f"""Here is the structured analysis:

{json.dumps(valid_payload())}

End of analysis.
"""

    result = parser.parse(text)

    assert result.company_overview == "B2B SaaS startup."


def test_parse_preserves_unicode(parser):
    payload = valid_payload()
    payload["company_overview"] = "भारत AI startup"

    result = parser.parse(
        json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    assert result.company_overview == "भारत AI startup"


def test_parse_rejects_empty_response(parser):
    with pytest.raises(
        StartupAnalysisParseError,
        match="response is empty",
    ):
        parser.parse("")


def test_parse_rejects_whitespace_response(parser):
    with pytest.raises(
        StartupAnalysisParseError,
        match="response is empty",
    ):
        parser.parse("   \n\t")


def test_parse_rejects_invalid_json(parser):
    with pytest.raises(
        StartupAnalysisParseError,
        match="invalid JSON",
    ):
        parser.parse(
            '{"company_overview": "broken"'
        )


def test_parse_rejects_json_array(parser):
    text = json.dumps(
        [
            valid_payload(),
        ]
    )

    with pytest.raises(
        StartupAnalysisParseError,
        match="must be an object",
    ):
        parser.parse(text)


def test_parse_rejects_schema_validation_error(parser):
    payload = valid_payload()
    payload["preliminary_recommendation"] = "invest"

    with pytest.raises(
        StartupAnalysisParseError,
        match="does not match",
    ):
        parser.parse(json.dumps(payload))


def test_parse_rejects_unknown_fields(parser):
    payload = valid_payload()
    payload["llm_score"] = 95

    with pytest.raises(
        StartupAnalysisParseError,
        match="does not match",
    ):
        parser.parse(json.dumps(payload))


def test_parse_rejects_missing_json(parser):
    with pytest.raises(
        StartupAnalysisParseError,
        match="No JSON object found",
    ):
        parser.parse(
            "The startup analysis could not be generated."
        )
