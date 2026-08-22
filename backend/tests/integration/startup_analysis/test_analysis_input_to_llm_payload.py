"""
Integration tests for the:

    StartupAnalysisInput + FinancialMetrics
        -> build_startup_analysis_messages()
        -> LLM messages / payload

handshake.

These tests intentionally do NOT invoke Qwen or any other LLM provider.

The purpose is to verify that canonical analysis data survives the boundary
into the provider-independent LLM prompt builder.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

from app.prompt.startup_analysis import (
    build_startup_analysis_messages,
)
from app.schemas.analysis import (
    BusinessModelAnalysis,
    CompanyAnalysis,
    FinancialAnalysis,
    FinancialMetrics,
    FundraisingAnalysis,
    MarketAnalysis,
    StartupAnalysisInput,
    TractionAnalysis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_analysis_input() -> StartupAnalysisInput:
    """
    Build a representative canonical StartupAnalysisInput.

    The values intentionally exercise the fields that were previously lost
    during the RestoMart downstream trace.
    """
    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="RestoMart",
            description=(
                "B2B food-supply and restaurant technology company."
            ),
            industry="B2B Food Supply",
            sector="Food Supply / Restaurant Technology",
            stage="early_revenue",
            founded_year=2023,
            headquarters="India",
        ),
        founders=[],
        market=MarketAnalysis(
            geographic_market="India",
            competitors=[],
        ),
        traction=TractionAnalysis(
            revenue=Decimal("26800000"),
        ),
        financials=FinancialAnalysis(
            revenue=Decimal("26800000"),
            gross_profit=Decimal("8000000"),
            gross_margin=Decimal("0.2985"),
            ebitda=Decimal("1500000"),
            ebitda_margin=Decimal("0.0560"),
            net_profit=Decimal("500000"),
            cash=Decimal("5000000"),
            debt=Decimal("1000000"),
            burn_rate=Decimal("200000"),
            runway_months=24,
        ),
        fundraising=FundraisingAnalysis(
            current_round="Seed",
            amount_raising=Decimal("50000000"),
            amount_raised=Decimal("20000000"),
            pre_money_valuation=Decimal("75000000"),
            post_money_valuation=Decimal("125000000"),
            valuation_cap=None,
            instrument="CCD",
            investor_commitments=Decimal("10000000"),
        ),
        business_model=BusinessModelAnalysis(
            business_model="b2b, marketplace",
            revenue_streams=[
                "procurement margin",
                "delivery services",
            ],
        ),
    )


def _build_metrics() -> FinancialMetrics:
    """
    Build deterministic metrics supplied to the prompt builder.

    These values must remain separate from the source financial inputs.
    """
    return FinancialMetrics(
        revenue_multiple=Decimal("4.20"),
        ebitda_multiple=Decimal("8.33"),
        valuation_to_growth=Decimal("2.50"),
        ebitda_margin=Decimal("0.0560"),
        gross_margin=Decimal("0.2985"),
        ltv_to_cac=Decimal("3.20"),
        runway_months=24,
    )


def _extract_user_payload(messages) -> dict:
    """
    Extract and JSON-decode the STARTUP INPUT payload from the user message.

    We intentionally parse the actual production prompt rather than
    reconstructing the expected payload from private implementation
    details.
    """
    assert len(messages) == 2

    user_message = messages[1]

    assert user_message.role == "user"

    content = user_message.content

    marker = "STARTUP INPUT\n=============\n\n"

    assert marker in content

    payload_start = content.index(marker) + len(marker)

    payload_end_marker = "\n\nOUTPUT REQUIREMENTS\n==================="

    assert payload_end_marker in content

    payload_end = content.index(
        payload_end_marker,
        payload_start,
    )

    payload_text = content[payload_start:payload_end].strip()

    return json.loads(payload_text)


# ---------------------------------------------------------------------------
# Basic contract
# ---------------------------------------------------------------------------


def test_analysis_input_to_llm_payload_preserves_message_contract() -> None:
    """
    The production builder must produce exactly the provider-independent
    two-message contract expected by StartupAnalysisService.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=metrics,
    )

    assert len(messages) == 2

    assert messages[0].role == "system"
    assert messages[1].role == "user"

    assert messages[0].content
    assert messages[1].content

    payload = _extract_user_payload(messages)

    assert set(payload) == {
        "startup",
        "deterministic_financial_metrics",
    }


# ---------------------------------------------------------------------------
# Startup input preservation
# ---------------------------------------------------------------------------


def test_startup_company_data_reaches_llm_payload() -> None:
    """
    Company information must survive:

        StartupAnalysisInput
            -> prompt payload
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    startup = payload["startup"]
    company = startup["company"]

    assert company["name"] == "RestoMart"
    assert company["industry"] == "B2B Food Supply"
    assert company["sector"] == "Food Supply / Restaurant Technology"
    assert company["stage"] == "early_revenue"
    assert company["founded_year"] == 2023
    assert company["headquarters"] == "India"


def test_fundraising_data_reaches_llm_payload() -> None:
    """
    This is the critical regression test for the earlier RestoMart trace.

    Fundraising information must not disappear between the canonical
    StartupAnalysisInput and the LLM payload.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    fundraising = payload["startup"]["fundraising"]

    assert fundraising["current_round"] == "Seed"
    assert fundraising["amount_raising"] == "50000000"
    assert fundraising["amount_raised"] == "20000000"
    assert fundraising["pre_money_valuation"] == "75000000"
    assert fundraising["post_money_valuation"] == "125000000"
    assert fundraising["instrument"] == "CCD"
    assert fundraising["investor_commitments"] == "10000000"


def test_financial_input_reaches_llm_payload() -> None:
    """
    Financial source inputs must remain distinct from deterministic metrics.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    financials = payload["startup"]["financials"]

    assert financials["revenue"] == "26800000"
    assert financials["gross_profit"] == "8000000"
    assert financials["gross_margin"] == "0.2985"
    assert financials["ebitda"] == "1500000"
    assert financials["ebitda_margin"] == "0.0560"
    assert financials["net_profit"] == "500000"
    assert financials["cash"] == "5000000"
    assert financials["debt"] == "1000000"
    assert financials["burn_rate"] == "200000"
    assert financials["runway_months"] == "24"


def test_business_model_reaches_llm_payload() -> None:
    """
    Business-model information must survive the input -> prompt boundary.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    business_model = payload["startup"]["business_model"]

    assert business_model["business_model"] == "b2b, marketplace"
    assert business_model["revenue_streams"] == [
        "procurement margin",
        "delivery services",
    ]


def test_traction_reaches_llm_payload() -> None:
    """
    Traction data must survive the input -> prompt boundary.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    traction = payload["startup"]["traction"]

    assert traction["revenue"] == "26800000"


def test_market_reaches_llm_payload() -> None:
    """
    Market information must survive the input -> prompt boundary.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    market = payload["startup"]["market"]

    assert market["geographic_market"] == "India"
    assert market["competitors"] == []


# ---------------------------------------------------------------------------
# Deterministic metrics preservation
# ---------------------------------------------------------------------------


def test_deterministic_financial_metrics_reach_llm_payload() -> None:
    """
    Deterministic FinancialMetrics must appear under the dedicated
    deterministic_financial_metrics payload section.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    deterministic = payload[
        "deterministic_financial_metrics"
    ]

    assert deterministic["revenue_multiple"] == "4.20"
    assert deterministic["ebitda_multiple"] == "8.33"
    assert deterministic["valuation_to_growth"] == "2.50"
    assert deterministic["ebitda_margin"] == "0.0560"
    assert deterministic["gross_margin"] == "0.2985"
    assert deterministic["ltv_to_cac"] == "3.20"
    assert deterministic["runway_months"] == "24"


def test_source_financials_and_deterministic_metrics_remain_separate() -> None:
    """
    Prevent a particularly dangerous handshake regression:

        source financial inputs
        !=
        deterministic financial metrics

    Both are allowed to contain overlapping values, but they must remain
    represented in their respective payload sections.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    assert "financials" in payload["startup"]
    assert "deterministic_financial_metrics" in payload

    startup_financials = payload["startup"]["financials"]
    deterministic = payload["deterministic_financial_metrics"]

    assert startup_financials["revenue"] == "26800000"
    assert deterministic["revenue_multiple"] == "4.20"

    # Deterministic metrics must not replace the source financial object.
    assert "revenue_multiple" not in startup_financials

    # Source financial values must not be silently promoted into the
    # deterministic metrics object.
    assert "cash" not in deterministic
    assert "debt" not in deterministic


# ---------------------------------------------------------------------------
# Null / omission contract
# ---------------------------------------------------------------------------


def test_none_fields_are_not_serialized_into_llm_payload() -> None:
    """
    The production builder uses exclude_none=True.

    Therefore absent optional fields must not appear as explicit null values
    in the serialized startup payload.
    """
    analysis_input = _build_analysis_input()
    metrics = FinancialMetrics(
        runway_months=24,
    )

    # Remove fundraising and business model explicitly for this contract test.
    analysis_input = analysis_input.model_copy(
        update={
            "fundraising": None,
            "business_model": None,
        }
    )

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    payload = _extract_user_payload(messages)

    startup = payload["startup"]

    assert "fundraising" not in startup
    assert "business_model" not in startup

    deterministic = payload[
        "deterministic_financial_metrics"
    ]

    assert deterministic == {
        "runway_months": "24",
    }


# ---------------------------------------------------------------------------
# Prompt output contract
# ---------------------------------------------------------------------------


def test_output_requirements_remain_in_user_prompt() -> None:
    """
    The handshake is not complete if the input reaches the prompt but the
    output contract disappears.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    user_prompt = messages[1].content

    assert "OUTPUT REQUIREMENTS" in user_prompt
    assert "Return ONLY a JSON object" in user_prompt
    assert "Use null when there is insufficient information." in user_prompt
    assert "Do not invent missing information." in user_prompt


def test_system_prompt_is_present_and_non_empty() -> None:
    """
    Verify the provider-independent system prompt remains part of the
    handshake.
    """
    analysis_input = _build_analysis_input()
    metrics = _build_metrics()

    messages = build_startup_analysis_messages(
        analysis_input,
        metrics,
    )

    system_prompt = messages[0]

    assert system_prompt.role == "system"
    assert system_prompt.content.strip()

    assert "investment analysis assistant" in (
        system_prompt.content.lower()
    )
    assert "do not invent facts" in (
        system_prompt.content.lower()
    )
