"""Tests for StartupAnalysisOrchestrator."""

from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from app.models.analysis import StartupAnalysisMode
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialMetrics,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.startup_analysis_config import StartupAnalysisConfig
from app.services.startup_analysis_execution import (
    EXECUTION_STATUS_COMPLETED,
    StartupAnalysisExecution,
)
from app.services.startup_analysis_input_builder import (
    StartupAnalysisInputBuilder,
)
from app.services.startup_analysis_orchestrator import (
    StartupAnalysisOrchestrator,
)

from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis import StartupAnalysisService


@pytest.fixture
def input_builder():
    return Mock(spec=StartupAnalysisInputBuilder)


@pytest.fixture
def metrics_service():
    return Mock(spec=FinancialMetricsService)


@pytest.fixture
def analysis_service():
    return Mock(spec=StartupAnalysisService)


@pytest.fixture
def startup():
    startup = Mock()
    startup.id = uuid4()
    return startup

@pytest.fixture
def analysis_input(startup):
    return StartupAnalysisInput(
        startup_id=startup.id,
        company=CompanyAnalysis(
            name="Example Startup",
            description="Example startup",
            industry="SaaS",
            sector="Technology",
        ),
    )

@pytest.fixture
def metrics():
    return FinancialMetrics(
        revenue_multiple=3.4,
        ebitda_multiple=17,
        valuation_to_growth=10,
        ebitda_margin=20,
        runway_months=18,
    )

@pytest.fixture
def result():
    return StartupAnalysisResult(
        company_overview="Strong company",
        founder_assessment="Experienced team",
        product_assessment="Good product",
        market_assessment="Large market",
        traction_assessment="Strong traction",
        financial_assessment="Healthy financials",
        valuation_assessment="Reasonable valuation",
        business_model_assessment="Scalable model",
        competitive_assessment="Strong position",
        strengths=["Strong team"],
        risks=["Competition"],
        missing_information=["Customer concentration"],
        key_observations=["Strong growth"],
        investment_thesis="Promising investment opportunity",
        preliminary_recommendation="promising",
    )

# 2. Configuration helpers
# Create distinct configs for standard and deep mode.

@pytest.fixture
def standard_config():
    return StartupAnalysisConfig(
        mode=StartupAnalysisMode.STANDARD,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=False,
        max_tokens=768,
        temperature=0.0,
    )

@pytest.fixture
def deep_config():
    return StartupAnalysisConfig(
        mode=StartupAnalysisMode.DEEP,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=True,
        max_tokens=1024,
        temperature=0.0,
    )

# 3. LLM response

@pytest.fixture
def response():
    response = Mock()
    response.text = '{"preliminary_recommendation": "promising"}'
    response.model = "Qwen3-8B-Q4_K_M"
    response.finish_reason = "stop"
    return response


@pytest.fixture
def orchestrator(
    input_builder,
    metrics_service,
    analysis_service,
):
    return StartupAnalysisOrchestrator(
        input_builder=input_builder,
        financial_metrics_service=metrics_service,
        analysis_service=analysis_service,
    )

# Test 1 — Builds input and calculates metrics
def test_orchestrator_builds_input_and_calculates_metrics(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    standard_config,
    response,
):
    input_builder.build.return_value = analysis_input

    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        standard_config,
        response,
    )

    execution = orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )

    input_builder.build.assert_called_once_with(startup)

    metrics_service.calculate.assert_called_once_with(
        financials=analysis_input.financials,
        fundraising=analysis_input.fundraising,
        business_model=analysis_input.business_model,
    )

    assert execution.metrics is metrics

# Test 2 — Passes exact input + metrics to analysis service
def test_orchestrator_passes_input_and_metrics_to_analysis_service(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    standard_config,
    response,
):
    input_builder.build.return_value = analysis_input
    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        standard_config,
        response,
    )

    orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )

    analysis_service.analyze_qualitative.assert_called_once_with(
        analysis_input=analysis_input,
        metrics=metrics,
        mode=StartupAnalysisMode.STANDARD,
    )

#Test 3 — Standard mode
def test_orchestrator_preserves_standard_mode(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    standard_config,
    response,
):
    input_builder.build.return_value = analysis_input
    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        standard_config,
        response,
    )

    execution = orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )

    analysis_service.analyze_qualitative.assert_called_once_with(
        analysis_input=analysis_input,
        metrics=metrics,
        mode=StartupAnalysisMode.STANDARD,
    )

    assert execution.config is standard_config
    assert execution.mode == StartupAnalysisMode.STANDARD

# Test 4 — Deep mode
def test_orchestrator_preserves_deep_mode(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    deep_config,
    response,
):
    input_builder.build.return_value = analysis_input
    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        deep_config,
        response,
    )

    execution = orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.DEEP,
    )

    analysis_service.analyze_qualitative.assert_called_once_with(
        analysis_input=analysis_input,
        metrics=metrics,
        mode=StartupAnalysisMode.DEEP,
    )

    assert execution.config is deep_config
    assert execution.mode == StartupAnalysisMode.DEEP

# Test 5 — Returns complete execution envelope
def test_orchestrator_returns_complete_execution(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    standard_config,
    response,
):
    input_builder.build.return_value = analysis_input
    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        standard_config,
        response,
    )

    execution = orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )

    # 6. Returns StartupAnalysisExecution
    assert isinstance(
        execution,
        StartupAnalysisExecution,
    )

    # 7. Exact input
    assert execution.input is analysis_input

    # 8. Exact metrics
    assert execution.metrics is metrics

    # 9. Exact result
    assert execution.result is result

    # 10. Exact config
    assert execution.config is standard_config

    # 11. Exact response
    assert execution.response is response

    # 12. Completed status
    assert execution.status == EXECUTION_STATUS_COMPLETED
    assert execution.is_completed is True


# 6. Verify call ordering
def test_orchestrator_executes_stages_in_order(
    orchestrator,
    startup,
    analysis_input,
    metrics,
    input_builder,
    metrics_service,
    analysis_service,
    result,
    standard_config,
    response,
):
    input_builder.build.return_value = analysis_input
    metrics_service.calculate.return_value = metrics

    analysis_service.analyze_qualitative.return_value = (
        result,
        standard_config,
        response,
    )

    parent = Mock()

    parent.attach_mock(
        input_builder.build,
        "build_input",
    )
    parent.attach_mock(
        metrics_service.calculate,
        "calculate_metrics",
    )
    parent.attach_mock(
        analysis_service.analyze_qualitative,
        "analyze_qualitative",
    )

    orchestrator.analyze(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )

    calls = [
        call.build_input(startup),
        call.calculate_metrics(
            financials=analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=analysis_input.business_model,
        ),
        call.analyze_qualitative(
            analysis_input=analysis_input,
            metrics=metrics,
            mode=StartupAnalysisMode.STANDARD,
        ),
    ]


    assert parent.mock_calls == calls

