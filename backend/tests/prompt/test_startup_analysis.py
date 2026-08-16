"""
Tests for startup analysis prompt construction.

These tests validate the prompt contract only.

They must not:
    - invoke an LLM,
    - load a model,
    - perform financial calculations,
    - depend on a concrete LLM provider.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

from app.llm.models import LLMMessage
from app.prompt.startup_analysis import (
    OUTPUT_SCHEMA,
    STARTUP_ANALYSIS_SYSTEM_PROMPT,
    build_startup_analysis_messages,
)
from app.schemas.analysis import (
    BusinessModelAnalysis,
    CompanyAnalysis,
    FinancialAnalysis,
    FinancialMetrics,
    FundraisingAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupAnalysisInput,
    TractionAnalysis,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_analysis_input() -> StartupAnalysisInput:
    """Create a representative startup analysis input."""

    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example AI Technologies",
        ),
        product=ProductAnalysis(
            target_customer="Enterprise surveillance companies",
            value_proposition="AI-powered edge analytics",
            product_stage="commercial",
            technology="Edge AI",
            differentiation="Low-power real-time inference",
        ),
        market=MarketAnalysis(
            market_description="Edge AI surveillance market",
            tam=Decimal("100000000000"),
            sam=Decimal("30000000000"),
            som=Decimal("3000000000"),
            market_growth_rate=Decimal("25"),
            geographic_market="India",
            competitors=["Competitor A", "Competitor B"],
        ),
        traction=TractionAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("40"),
            customers=100,
            paying_customers=80,
            active_users=120,
            repeat_customer_rate=Decimal("70"),
            key_traction_notes="Growing enterprise customer base.",
        ),
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("40"),
            gross_profit=Decimal("60000000"),
            gross_margin=Decimal("60"),
            ebitda=Decimal("20000000"),
            ebitda_margin=Decimal("20"),
            net_profit=Decimal("10000000"),
            cash=Decimal("50000000"),
            debt=Decimal("10000000"),
            burn_rate=Decimal("2000000"),
            runway_months=Decimal("25"),
        ),
        fundraising=FundraisingAnalysis(
            current_round="Seed",
            amount_raising=Decimal("40000000"),
            amount_raised=Decimal("20000000"),
            pre_money_valuation=Decimal("300000000"),
            post_money_valuation=Decimal("340000000"),
            valuation_cap=Decimal("300000000"),
            instrument="CCPS",
            investor_commitments=Decimal("25000000"),
        ),
        business_model=BusinessModelAnalysis(
            business_model="B2B SaaS",
            revenue_streams=["Software subscription", "Analytics"],
            pricing_model="Annual subscription",
            gross_margin=Decimal("60"),
            customer_acquisition_cost=Decimal("100000"),
            lifetime_value=Decimal("500000"),
            ltv_to_cac=Decimal("5"),
        ),
    )


def make_metrics() -> FinancialMetrics:
    """Create deterministic metrics supplied to the prompt."""

    return FinancialMetrics(
        revenue_multiple=Decimal("3.40"),
        ebitda_multiple=Decimal("17.00"),
        valuation_to_growth=Decimal("0.085"),
    )


def build_messages() -> tuple[LLMMessage, ...]:
    """Build a standard startup analysis prompt."""

    return build_startup_analysis_messages(
        analysis_input=make_analysis_input(),
        metrics=make_metrics(),
    )


def extract_input_payload(user_prompt: str) -> dict:
    """Extract the JSON startup payload from the user prompt."""

    start_marker = "STARTUP INPUT\n=============\n\n"
    end_marker = "\n\nOUTPUT REQUIREMENTS\n==================="

    assert start_marker in user_prompt
    assert end_marker in user_prompt

    payload_text = user_prompt.split(
        start_marker,
        maxsplit=1,
    )[1].split(
        end_marker,
        maxsplit=1,
    )[0]

    return json.loads(payload_text)


# ---------------------------------------------------------------------------
# Message structure
# ---------------------------------------------------------------------------


def test_returns_system_and_user_messages():
    """Prompt builder must return exactly one system and one user message."""

    messages = build_messages()

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"


def test_messages_are_llm_messages():
    """Prompt builder must use the provider-independent LLM message model."""

    messages = build_messages()

    assert all(
        isinstance(message, LLMMessage)
        for message in messages
    )


# ---------------------------------------------------------------------------
# System prompt contract
# ---------------------------------------------------------------------------


def test_system_prompt_is_used():
    """The configured startup analysis system prompt must be forwarded."""

    messages = build_messages()

    assert messages[0].content == STARTUP_ANALYSIS_SYSTEM_PROMPT


def test_system_prompt_prevents_hallucinated_information():
    """The model must be explicitly instructed not to invent facts."""

    prompt = build_messages()[0].content.lower()

    assert "do not invent" in prompt
    assert "not provided" in prompt


def test_system_prompt_requires_json():
    """The model must be instructed to return JSON only."""

    prompt = build_messages()[0].content.lower()

    assert "return only valid json" in prompt
    assert "markdown code fences" in prompt


def test_system_prompt_preserves_deterministic_metrics():
    """The LLM must not recalculate application-generated metrics."""

    prompt = build_messages()[0].content.lower()

    assert "already been calculated deterministically" in prompt
    assert "do not recalculate" in prompt


# ---------------------------------------------------------------------------
# Input payload
# ---------------------------------------------------------------------------


def test_user_prompt_contains_startup_input():
    """The user prompt must contain the structured startup input."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    assert "startup" in payload
    assert "deterministic_financial_metrics" in payload


def test_company_information_is_preserved():
    """Company information must reach the prompt unchanged."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    assert (
        payload["startup"]["company"]["name"]
        == "Example AI Technologies"
    )


def test_financial_information_is_preserved():
    """Financial information must reach the prompt."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    financials = payload["startup"]["financials"]

    assert financials["revenue"] == "100000000"
    assert financials["ebitda"] == "20000000"
    assert financials["gross_margin"] == "60"


def test_fundraising_information_is_preserved():
    """Fundraising information must reach the prompt."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    fundraising = payload["startup"]["fundraising"]

    assert fundraising["current_round"] == "Seed"
    assert fundraising["amount_raising"] == "40000000"
    assert fundraising["instrument"] == "CCPS"


def test_market_and_competitor_information_is_preserved():
    """Market and competitor information must reach the prompt."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    market = payload["startup"]["market"]

    assert market["market_description"] == (
        "Edge AI surveillance market"
    )
    assert market["geographic_market"] == "India"
    assert market["competitors"] == [
        "Competitor A",
        "Competitor B",
    ]


def test_business_model_information_is_preserved():
    """Business model information must reach the prompt."""

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    business_model = payload["startup"]["business_model"]

    assert business_model["business_model"] == "B2B SaaS"
    assert business_model["revenue_streams"] == [
        "Software subscription",
        "Analytics",
    ]
    assert business_model["ltv_to_cac"] == "5"


# ---------------------------------------------------------------------------
# Deterministic metrics
# ---------------------------------------------------------------------------


def test_deterministic_metrics_are_passed_separately():
    """
    Deterministic metrics must be supplied in their own payload section.
    """

    messages = build_messages()
    payload = extract_input_payload(messages[1].content)

    metrics = payload["deterministic_financial_metrics"]

    assert metrics["revenue_multiple"] == "3.40"
    assert metrics["ebitda_multiple"] == "17.00"
    assert metrics["valuation_to_growth"] == "0.085"


def test_prompt_does_not_ask_llm_to_calculate_metrics():
    """The prompt must treat financial metrics as supplied facts."""

    user_prompt = build_messages()[1].content.lower()

    assert "recalculate" not in user_prompt
    assert "calculate the revenue multiple" not in user_prompt
    assert "calculate the ebitda multiple" not in user_prompt


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_output_schema_contains_all_startup_analysis_result_fields():
    """
    OUTPUT_SCHEMA must stay aligned with StartupAnalysisResult.
    """

    expected_fields = {
        "company_overview",
        "founder_assessment",
        "product_assessment",
        "market_assessment",
        "traction_assessment",
        "financial_assessment",
        "valuation_assessment",
        "business_model_assessment",
        "competitive_assessment",
        "strengths",
        "risks",
        "missing_information",
        "key_observations",
        "investment_thesis",
        "preliminary_recommendation",
    }

    assert set(OUTPUT_SCHEMA) == expected_fields


def test_output_schema_contains_all_recommendation_values():
    """The prompt contract must expose all supported recommendations."""

    recommendation = OUTPUT_SCHEMA["preliminary_recommendation"]

    assert "insufficient_information" in recommendation
    assert "promising" in recommendation
    assert "needs_further_diligence" in recommendation
    assert "concerns" in recommendation


def test_output_schema_is_included_in_user_prompt():
    """The actual requested output contract must reach the LLM."""

    user_prompt = build_messages()[1].content

    assert '"company_overview"' in user_prompt
    assert '"founder_assessment"' in user_prompt
    assert '"financial_assessment"' in user_prompt
    assert '"valuation_assessment"' in user_prompt
    assert '"strengths"' in user_prompt
    assert '"risks"' in user_prompt
    assert '"missing_information"' in user_prompt
    assert '"investment_thesis"' in user_prompt
    assert '"preliminary_recommendation"' in user_prompt


# ---------------------------------------------------------------------------
# Missing information / optional fields
# ---------------------------------------------------------------------------


def test_none_values_are_not_serialized_into_input_payload():
    """
    Optional fields with None values should not clutter the LLM payload.
    """

    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Minimal Startup",
        ),
    )

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=FinancialMetrics(),
    )

    payload = extract_input_payload(messages[1].content)

    startup = payload["startup"]

    assert startup["company"]["name"] == "Minimal Startup"
    assert "product" not in startup
    assert "market" not in startup
    assert "traction" not in startup
    assert "financials" not in startup
    assert "fundraising" not in startup
    assert "business_model" not in startup


def test_empty_optional_collections_are_preserved_as_empty_lists():
    """
    Collection fields with their default empty lists should remain valid
    structured input.
    """

    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Minimal Startup",
        ),
    )

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=FinancialMetrics(),
    )

    payload = extract_input_payload(messages[1].content)

    startup = payload["startup"]

    assert startup["founders"] == []
    assert startup["evidence"] == []


# ---------------------------------------------------------------------------
# Unicode / serialization
# ---------------------------------------------------------------------------


def test_unicode_and_currency_values_are_preserved():
    """Prompt serialization must preserve Unicode startup information."""

    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="भारत AI",
        ),
        fundraising=FundraisingAnalysis(
            current_round="Seed",
            instrument="CCPS",
        ),
    )

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=FinancialMetrics(),
    )

    payload = extract_input_payload(messages[1].content)

    assert payload["startup"]["company"]["name"] == "भारत AI"
