"""Tests for startup-analysis persistence mapping."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import pytest

from app.llm.models import LLMResponse, LLMUsage
from app.models.analysis import StartupAnalysisMode, StartupAnalysisStatus
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialMetrics,
    StartupAnalysis,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.startup_analysis_config import StartupAnalysisConfig
from app.services.startup_analysis_mapper import (
    map_startup_analysis_to_model,
)


def make_analysis() -> StartupAnalysis:
    """Build a representative completed analysis result."""

    analysis_input = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example Startup",
            sector="SaaS",
        ),
    )

    return StartupAnalysis(
        startup_id=analysis_input.startup_id,
        mode=StartupAnalysisMode.DEEP,
        input=analysis_input,
        metrics=FinancialMetrics(
            revenue_multiple=Decimal("3.4"),
            ebitda_multiple=Decimal("17"),
        ),
        result=StartupAnalysisResult(
            strengths=["Strong growth"],
            risks=["Valuation"],
            missing_information=["Customer concentration"],
            key_observations=["Positive EBITDA"],
            investment_thesis="Promising subject to diligence.",
            preliminary_recommendation="promising",
        ),
        analysis_version="3.7.5",
    )


def make_config() -> StartupAnalysisConfig:
    """Build the deep execution configuration."""

    return StartupAnalysisConfig(
        mode=StartupAnalysisMode.DEEP,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=True,
        max_tokens=1024,
        temperature=0.0,
    )


def make_response(*, model: str | None = "Qwen3-8B-Q4_K_M") -> LLMResponse:
    """Build a normalized LLM response."""

    return LLMResponse(
        text='{"preliminary_recommendation":"promising"}',
        model=model,
        finish_reason="stop",
        usage=LLMUsage(
            prompt_tokens=1400,
            completion_tokens=500,
            total_tokens=1900,
        ),
    )


def test_maps_execution_identity():
    analysis = make_analysis()

    model = map_startup_analysis_to_model(
        analysis=analysis,
        config=make_config(),
        response=make_response(),
    )

    assert model.startup_id == analysis.startup_id
    assert model.mode == StartupAnalysisMode.DEEP
    assert model.status == StartupAnalysisStatus.COMPLETED
    assert model.analysis_version == "3.7.5"


def test_maps_llm_configuration_and_response_metadata():
    model = map_startup_analysis_to_model(
        analysis=make_analysis(),
        config=make_config(),
        response=make_response(),
        inference_time_seconds=300.25,
    )

    assert model.model_name == "Qwen3-8B-Q4_K_M"
    assert model.thinking_enabled is True
    assert model.max_tokens == 1024
    assert model.temperature == 0.0
    assert model.finish_reason == "stop"
    assert model.prompt_tokens == 1400
    assert model.completion_tokens == 500
    assert model.total_tokens == 1900
    assert model.inference_time_seconds == 300.25


def test_response_model_is_preferred_over_config_model():
    model = map_startup_analysis_to_model(
        analysis=make_analysis(),
        config=make_config(),
        response=make_response(model="qwen3-8b-runtime"),
    )

    assert model.model_name == "qwen3-8b-runtime"


def test_config_model_is_fallback_when_response_model_missing():
    model = map_startup_analysis_to_model(
        analysis=make_analysis(),
        config=make_config(),
        response=make_response(model=None),
    )

    assert model.model_name == "Qwen3-8B-Q4_K_M"


def test_maps_investment_conclusion():
    analysis = make_analysis()

    model = map_startup_analysis_to_model(
        analysis=analysis,
        config=make_config(),
        response=make_response(),
    )

    assert model.recommendation == "promising"
    assert model.investment_thesis == "Promising subject to diligence."


def test_maps_json_safe_snapshots():
    model = map_startup_analysis_to_model(
        analysis=make_analysis(),
        config=make_config(),
        response=make_response(),
    )

    assert model.input_snapshot["company"]["name"] == "Example Startup"
    assert model.metrics_snapshot["revenue_multiple"] == "3.4"
    assert model.metrics_snapshot["ebitda_multiple"] == "17"
    assert model.result_snapshot["preliminary_recommendation"] == "promising"

    # The exact snapshot structures must be JSON serializable before they are
    # assigned to SQLAlchemy JSON columns.
    json.dumps(model.input_snapshot)
    json.dumps(model.metrics_snapshot)
    json.dumps(model.result_snapshot)


def test_snapshots_are_independent_of_source_objects():
    analysis = make_analysis()

    model = map_startup_analysis_to_model(
        analysis=analysis,
        config=make_config(),
        response=make_response(),
    )

    analysis.result.strengths.append("Changed after mapping")
    analysis.metrics.revenue_multiple = Decimal("99")

    assert model.result_snapshot["strengths"] == ["Strong growth"]
    assert model.metrics_snapshot["revenue_multiple"] == "3.4"


def test_requires_startup_id():
    analysis = make_analysis()
    analysis.startup_id = None

    with pytest.raises(
        ValueError,
        match="requires startup_id",
    ):
        map_startup_analysis_to_model(
            analysis=analysis,
            config=make_config(),
            response=make_response(),
        )
