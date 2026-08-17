"""Tests for StartupAnalysisExecution."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

import pytest

from app.llm.models import LLMResponse
from app.models.analysis import StartupAnalysisMode
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialAnalysis,
    FinancialMetrics,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.startup_analysis_config import StartupAnalysisConfig
from app.services.startup_analysis_execution import (
    EXECUTION_STATUS_COMPLETED,
    StartupAnalysisExecution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_input() -> StartupAnalysisInput:
    """Create a representative startup-analysis input."""

    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example Startup",
            description="Example startup for execution tests.",
            industry="SaaS",
            sector="Technology",
        ),
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
            revenue_growth_yoy=Decimal("40"),
        ),
    )


def make_metrics() -> FinancialMetrics:
    """Create representative deterministic financial metrics."""

    return FinancialMetrics(
        revenue_multiple=Decimal("3.4"),
        ebitda_multiple=Decimal("17"),
        valuation_to_growth=Decimal("10"),
        ebitda_margin=Decimal("20"),
        runway_months=Decimal("18"),
    )


def make_result() -> StartupAnalysisResult:
    """Create a representative qualitative analysis result."""

    return StartupAnalysisResult(
        company_overview="Strong B2B SaaS startup.",
        founder_assessment="Experienced founding team.",
        product_assessment="Clear product value proposition.",
        market_assessment="Large addressable market.",
        traction_assessment="Good early traction.",
        financial_assessment="Healthy financial profile.",
        valuation_assessment="Valuation requires diligence.",
        business_model_assessment="Scalable recurring revenue model.",
        competitive_assessment="Defensible market position.",
        strengths=[
            "Strong team",
            "Good growth",
        ],
        risks=[
            "Valuation risk",
        ],
        missing_information=[
            "Customer concentration",
        ],
        key_observations=[
            "Revenue growing strongly",
        ],
        investment_thesis=(
            "Promising opportunity subject to further diligence."
        ),
        preliminary_recommendation="promising",
    )


def make_config(
    *,
    mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
) -> StartupAnalysisConfig:
    """Create a representative execution configuration."""

    return StartupAnalysisConfig(
        mode=mode,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=(
            mode == StartupAnalysisMode.DEEP
        ),
        max_tokens=(
            1024
            if mode == StartupAnalysisMode.DEEP
            else 768
        ),
        temperature=0.0,
    )


def make_response() -> LLMResponse:
    """Create a representative successful LLM response."""

    return LLMResponse(
        text='{"preliminary_recommendation": "promising"}',
        model="Qwen3-8B-Q4_K_M",
        finish_reason="stop",
    )


def make_execution(
    *,
    status: str = EXECUTION_STATUS_COMPLETED,
    mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
) -> StartupAnalysisExecution:
    """Create a representative startup-analysis execution."""

    return StartupAnalysisExecution(
        input=make_input(),
        metrics=make_metrics(),
        result=make_result(),
        config=make_config(mode=mode),
        response=make_response(),
        status=status,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_execution_contains_all_artifacts():
    """Execution preserves every supplied artifact by identity."""

    analysis_input = make_input()
    metrics = make_metrics()
    result = make_result()
    config = make_config()
    response = make_response()

    execution = StartupAnalysisExecution(
        input=analysis_input,
        metrics=metrics,
        result=result,
        config=config,
        response=response,
    )

    assert execution.input is analysis_input
    assert execution.metrics is metrics
    assert execution.result is result
    assert execution.config is config
    assert execution.response is response


def test_execution_defaults_to_completed():
    """A successful execution defaults to completed status."""

    execution = make_execution()

    assert execution.status == EXECUTION_STATUS_COMPLETED
    assert execution.is_completed is True


def test_execution_accepts_explicit_status():
    """Execution preserves an explicitly supplied status."""

    execution = make_execution(status="failed")

    assert execution.status == "failed"
    assert execution.is_completed is False


# ---------------------------------------------------------------------------
# Derived properties
# ---------------------------------------------------------------------------


def test_startup_id_comes_from_input():
    """startup_id is derived from the normalized analysis input."""

    analysis_input = make_input()

    execution = StartupAnalysisExecution(
        input=analysis_input,
        metrics=make_metrics(),
        result=make_result(),
        config=make_config(),
        response=make_response(),
    )

    assert execution.startup_id == analysis_input.startup_id


def test_mode_comes_from_config():
    """mode is derived from the execution configuration."""

    execution = make_execution(
        mode=StartupAnalysisMode.DEEP,
    )

    assert execution.mode == StartupAnalysisMode.DEEP


def test_analysis_version_comes_from_config():
    """analysis_version is derived from execution configuration."""

    config = make_config()

    execution = StartupAnalysisExecution(
        input=make_input(),
        metrics=make_metrics(),
        result=make_result(),
        config=config,
        response=make_response(),
    )

    assert execution.analysis_version == config.analysis_version


def test_model_name_comes_from_config():
    """model_name is derived from execution configuration."""

    config = make_config()

    execution = StartupAnalysisExecution(
        input=make_input(),
        metrics=make_metrics(),
        result=make_result(),
        config=config,
        response=make_response(),
    )

    assert execution.model_name == config.model_name


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "input",
        "metrics",
        "result",
        "config",
        "response",
    ],
)
def test_execution_rejects_missing_required_artifact(field):
    """Required execution artifacts must not be None."""

    values = {
        "input": make_input(),
        "metrics": make_metrics(),
        "result": make_result(),
        "config": make_config(),
        "response": make_response(),
    }

    values[field] = None

    with pytest.raises(ValueError):
        StartupAnalysisExecution(**values)


def test_execution_rejects_empty_status():
    """Execution status must not be empty."""

    with pytest.raises(ValueError, match="status"):
        StartupAnalysisExecution(
            input=make_input(),
            metrics=make_metrics(),
            result=make_result(),
            config=make_config(),
            response=make_response(),
            status="",
        )


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_execution_is_immutable():
    """Execution artifacts cannot be modified after construction."""

    execution = make_execution()

    with pytest.raises(FrozenInstanceError):
        execution.status = "failed"


def test_execution_artifact_reference_cannot_be_replaced():
    """An existing execution artifact cannot be replaced."""

    execution = make_execution()

    with pytest.raises(FrozenInstanceError):
        execution.metrics = make_metrics()
