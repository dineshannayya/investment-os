"""Tests for the startup analysis service."""

from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.llm.models import LLMResponse
from app.core.config import settings
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialAnalysis,
    FinancialMetrics,
    FundraisingAnalysis,
    StartupAnalysisInput,
    StartupAnalysisResult,
)

from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis import (
    StartupAnalysisGenerationError,
    StartupAnalysisService,
)
from app.services.startup_analysis_parser import StartupAnalysisParseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_input() -> StartupAnalysisInput:
    """Create a representative startup analysis input."""

    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example Startup",
        ),
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
            revenue_growth_yoy=Decimal("40"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )


def make_llm_response(
    text: str,
    *,
    finish_reason: str = "stop",
) -> LLMResponse:
    """Create a minimal successful LLM response."""

    return LLMResponse(
        text=text,
        finish_reason=finish_reason,
    )


def make_valid_analysis_json() -> str:
    """Create a valid structured qualitative analysis response."""

    return """
    {
        "company_overview": "B2B SaaS startup.",
        "founder_assessment": "Strong domain expertise.",
        "product_assessment": "Clear product value proposition.",
        "market_assessment": "Large addressable market.",
        "traction_assessment": "Early but encouraging traction.",
        "financial_assessment": "Healthy financial profile.",
        "valuation_assessment": "Valuation requires further diligence.",
        "business_model_assessment": "Scalable recurring revenue model.",
        "competitive_assessment": "Competitive position appears strong.",
        "strengths": [
            "Strong founding team",
            "Good revenue growth"
        ],
        "risks": [
            "Valuation requires validation"
        ],
        "missing_information": [
            "Customer concentration"
        ],
        "key_observations": [
            "Revenue is growing strongly"
        ],
        "investment_thesis": "Promising opportunity subject to diligence.",
        "preliminary_recommendation": "promising"
    }
    """


class FakeLLMProvider:
    """Minimal provider double for service-level tests."""

    def __init__(self, response: LLMResponse):
        self.response = response
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self.response


def make_service(
    *,
    llm_response: LLMResponse | None = None,
    financial_metrics_service=None,
    parser=None,
):
    """Build the service with test doubles."""

    provider = FakeLLMProvider(
        llm_response
        or make_llm_response(make_valid_analysis_json())
    )

    service = StartupAnalysisService(
        financial_metrics_service=(
            financial_metrics_service
            or FinancialMetricsService
        ),
        llm_provider=provider,
        parser=parser,
    )

    return service, provider


# ---------------------------------------------------------------------------
# Basic analysis
# ---------------------------------------------------------------------------


def test_analyze_returns_startup_analysis():
    analysis_input = make_input()

    service, _ = make_service()

    result = service.analyze(analysis_input)

    assert result.input is analysis_input
    assert result.startup_id == analysis_input.startup_id


def test_analyze_preserves_input():
    analysis_input = make_input()

    service, _ = make_service()

    result = service.analyze(analysis_input)

    assert result.input == analysis_input


def test_analyze_produces_financial_metrics():
    analysis_input = make_input()

    service, _ = make_service()

    result = service.analyze(analysis_input)

    assert result.metrics.revenue_multiple == Decimal("4")
    assert result.metrics.ebitda_multiple == Decimal("20")
    assert result.metrics.valuation_to_growth == Decimal("0.1")


def test_analyze_sets_default_analysis_version():
    service, _ = make_service()

    result = service.analyze(make_input())

    assert result.analysis_version == "1.0"


# ---------------------------------------------------------------------------
# Qualitative analysis
# ---------------------------------------------------------------------------


def test_analyze_returns_parsed_qualitative_result():
    service, _ = make_service()

    result = service.analyze(make_input())

    assert result.result.company_overview == "B2B SaaS startup."
    assert result.result.founder_assessment == (
        "Strong domain expertise."
    )
    assert result.result.product_assessment == (
        "Clear product value proposition."
    )

    assert result.result.strengths == [
        "Strong founding team",
        "Good revenue growth",
    ]

    assert result.result.risks == [
        "Valuation requires validation",
    ]

    assert result.result.investment_thesis == (
        "Promising opportunity subject to diligence."
    )

    assert result.result.preliminary_recommendation == "promising"


def test_analyze_calls_llm_provider():
    service, provider = make_service()

    service.analyze(make_input())

    assert len(provider.requests) == 1


def test_analyze_sends_structured_llm_request():
    analysis_input = make_input()

    service, provider = make_service()

    test_settings = settings.model_copy(
        update={
            "startup_analysis_max_tokens": 256,
            "startup_analysis_temperature": 0.0,
        }
    )
    
    service = StartupAnalysisService(
        config=test_settings,
        llm_provider=provider,
    )
    
    service.analyze(analysis_input)
    
    request = provider.requests[0]
    
    assert request.max_tokens == 256
    assert request.temperature == 0.0
    assert len(request.messages) >= 1


def test_analyze_prompt_contains_startup_information():
    analysis_input = make_input()

    service, provider = make_service()

    service.analyze(analysis_input)

    request = provider.requests[0]

    prompt_text = "\n".join(
        message.content
        for message in request.messages
    )

    assert "Example Startup" in prompt_text
    assert "400000000" in prompt_text
    assert "100000000" in prompt_text


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def test_analyze_uses_injected_financial_metrics_service():
    analysis_input = make_input()

    metrics = FinancialMetrics(
        revenue_multiple=Decimal("7"),
        ebitda_multiple=Decimal("30"),
        valuation_to_growth=Decimal("0.2"),
    )

    financial_metrics_service = Mock(
        spec=FinancialMetricsService,
    )

    financial_metrics_service.calculate.return_value = metrics

    service, _ = make_service(
        financial_metrics_service=financial_metrics_service,
    )

    result = service.analyze(analysis_input)

    assert result.metrics is metrics

    financial_metrics_service.calculate.assert_called_once_with(
        financials=analysis_input.financials,
        fundraising=analysis_input.fundraising,
        business_model=analysis_input.business_model,
    )



def test_analyze_uses_injected_parser():
    analysis_input = make_input()

    parsed_result = StartupAnalysisResult(
        company_overview="Test startup",
        founder_assessment="Strong founders",
        product_assessment="Good product",
        market_assessment="Large market",
        traction_assessment="Strong traction",
        financial_assessment="Healthy financials",
        valuation_assessment="Reasonable valuation",
        business_model_assessment="Scalable model",
        competitive_assessment="Strong position",
        strengths=["Strong team"],
        risks=["Execution risk"],
        missing_information=["Customer concentration"],
        key_observations=["Good growth"],
        investment_thesis="Promising opportunity",
        preliminary_recommendation="promising",
    )

    parser = Mock()
    parser.parse.return_value = parsed_result

    service, provider = make_service(
        parser=parser,
    )

    result = service.analyze(analysis_input)

    assert result.result is parsed_result

    parser.parse.assert_called_once_with(
        provider.response.text,
    )

# ---------------------------------------------------------------------------
# LLM request / response handling
# ---------------------------------------------------------------------------


def test_analyze_rejects_truncated_llm_response():
    response = make_llm_response(
        make_valid_analysis_json(),
        finish_reason="length",
    )

    service, _ = make_service(
        llm_response=response,
    )

    with pytest.raises(
        StartupAnalysisGenerationError,
        match="truncated",
    ):
        service.analyze(make_input())


def test_analyze_rejects_llm_generation_failure():
    provider = Mock()

    provider.generate.side_effect = RuntimeError(
        "Qwen generation failed"
    )

    service = StartupAnalysisService(
        llm_provider=provider,
    )

    with pytest.raises(
        StartupAnalysisGenerationError,
        match="Failed to generate startup analysis",
    ):
        service.analyze(make_input())


def test_analyze_propagates_parser_error():
    parser = Mock()

    parser.parse.side_effect = StartupAnalysisParseError(
        "invalid JSON"
    )

    service, _ = make_service(
        parser=parser,
    )

    with pytest.raises(
        StartupAnalysisParseError,
        match="invalid JSON",
    ):
        service.analyze(make_input())


# ---------------------------------------------------------------------------
# Missing financial information
# ---------------------------------------------------------------------------


def test_analyze_without_financials():
    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Pre-Revenue Startup",
        ),
    )

    service, _ = make_service()

    result = service.analyze(analysis_input)

    assert result.metrics.revenue_multiple is None
    assert result.metrics.ebitda_multiple is None
    assert result.metrics.valuation_to_growth is None


def test_analyze_without_fundraising():
    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Bootstrapped Startup",
        ),
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
        ),
    )

    service, _ = make_service()

    result = service.analyze(analysis_input)

    assert result.metrics.revenue_multiple is None
    assert result.metrics.ebitda_multiple is None
