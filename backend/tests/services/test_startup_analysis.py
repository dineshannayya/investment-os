"""Tests for the startup analysis service."""

from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
    StartupAnalysisInput,
    FinancialMetrics,
)
from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis import StartupAnalysisService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_input() -> StartupAnalysisInput:
    """Create a minimal startup analysis input."""

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


# ---------------------------------------------------------------------------
# Basic analysis
# ---------------------------------------------------------------------------


def test_analyze_returns_startup_analysis():
    analysis_input = make_input()

    service = StartupAnalysisService()

    result = service.analyze(analysis_input)

    assert result.input is analysis_input
    assert result.startup_id == analysis_input.startup_id


def test_analyze_preserves_input():
    analysis_input = make_input()

    result = StartupAnalysisService().analyze(analysis_input)

    assert result.input == analysis_input


def test_analyze_produces_financial_metrics():
    analysis_input = make_input()

    result = StartupAnalysisService().analyze(analysis_input)

    assert result.metrics.revenue_multiple == Decimal("4")
    assert result.metrics.ebitda_multiple == Decimal("20")
    assert result.metrics.valuation_to_growth == Decimal("0.1")


def test_analyze_sets_default_analysis_version():
    result = StartupAnalysisService().analyze(
        make_input(),
    )

    assert result.analysis_version == "1.0"


# ---------------------------------------------------------------------------
# Qualitative result
# ---------------------------------------------------------------------------


def test_analyze_creates_default_qualitative_result():
    result = StartupAnalysisService().analyze(
        make_input(),
    )

    assert result.result.company_overview is None
    assert result.result.founder_assessment is None
    assert result.result.product_assessment is None

    assert result.result.strengths == []
    assert result.result.risks == []
    assert result.result.missing_information == []
    assert result.result.key_observations == []

    assert result.result.investment_thesis is None
    assert result.result.preliminary_recommendation == (
        "insufficient_information"
    )


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

    result = StartupAnalysisService().analyze(
        analysis_input,
    )

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

    result = StartupAnalysisService().analyze(
        analysis_input,
    )

    assert result.metrics.revenue_multiple is None
    assert result.metrics.ebitda_multiple is None


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

    service = StartupAnalysisService(
        financial_metrics_service=financial_metrics_service,
    )

    result = service.analyze(analysis_input)

    assert result.metrics is metrics

    financial_metrics_service.calculate.assert_called_once_with(
        financials=analysis_input.financials,
        fundraising=analysis_input.fundraising,
        business_model=analysis_input.business_model,
    )


def test_analyze_does_not_call_llm():
    """
    3.7.3 is deterministic orchestration only.

    Qualitative LLM analysis will be introduced in a later milestone.
    """

    analysis_input = make_input()

    result = StartupAnalysisService().analyze(
        analysis_input,
    )

    assert result.result.preliminary_recommendation == (
        "insufficient_information"
    )
