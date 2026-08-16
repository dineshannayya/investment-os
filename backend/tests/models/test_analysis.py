"""
Tests for StartupAnalysis ORM model.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
    StartupAnalysisStatus,
)


def make_analysis(
    *,
    startup,
    **overrides,
) -> StartupAnalysis:
    """
    Build a valid StartupAnalysis instance.

    Keep defaults here intentionally aligned with the model contract.
    Individual tests can override fields as required.
    """

    defaults = {
        "startup": startup,
        "startup_id": startup.id,
        "mode": StartupAnalysisMode.STANDARD,
        "status": StartupAnalysisStatus.COMPLETED,
        "analysis_version": "3.7.5",
        "model_name": "Qwen3-8B-Q4_K_M",
        "thinking_enabled": False,
        "max_tokens": 768,
        "temperature": 0.0,
        "finish_reason": "stop",
        "prompt_tokens": 1400,
        "completion_tokens": 500,
        "total_tokens": 1900,
        "inference_time_seconds": 150.0,
        "recommendation": "promising",
        "investment_thesis": (
            "Strong growth and traction, subject to further diligence."
        ),
        "input_snapshot": {
            "company": {
                "name": startup.name,
            },
        },
        "metrics_snapshot": {
            "revenue_multiple": 3.4,
            "ebitda_multiple": 17,
        },
        "result_snapshot": {
            "strengths": [
                "Strong revenue growth",
                "Healthy margins",
                "Good customer traction",
            ],
            "risks": [
                "High valuation",
                "Competition",
                "Founder information incomplete",
            ],
            "missing_information": [
                "Founder track record",
                "Competitive details",
                "Customer concentration",
            ],
            "key_observations": [
                "Strong growth",
                "Positive EBITDA",
                "Healthy runway",
            ],
            "preliminary_recommendation": "promising",
        },
        "error_message": None,
    }

    defaults.update(overrides)

    return StartupAnalysis(**defaults)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


def test_analysis_mode_values():
    """Analysis modes have stable persisted values."""

    assert StartupAnalysisMode.STANDARD.value == "standard"
    assert StartupAnalysisMode.DEEP.value == "deep"


def test_analysis_status_values():
    """Analysis statuses have stable persisted values."""

    assert StartupAnalysisStatus.COMPLETED.value == "completed"
    assert StartupAnalysisStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# Factory / defaults
# ---------------------------------------------------------------------------


def test_analysis_defaults(startup_factory):
    """StartupAnalysis can be created with the expected defaults."""

    startup = startup_factory()

    analysis = StartupAnalysis(
        startup=startup,
        startup_id=startup.id,
        model_name="Qwen3-8B-Q4_K_M",
        max_tokens=768,
        temperature=0.0,
    )

    assert analysis.startup == startup
    assert analysis.mode == StartupAnalysisMode.STANDARD
    assert analysis.status == StartupAnalysisStatus.COMPLETED
    assert analysis.analysis_version == "3.7.5"
    assert analysis.thinking_enabled is False


def test_analysis_deep_mode(startup_factory):
    """Deep analysis stores thinking-enabled configuration."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        mode=StartupAnalysisMode.DEEP,
        thinking_enabled=True,
        max_tokens=1024,
    )

    assert analysis.mode == StartupAnalysisMode.DEEP
    assert analysis.thinking_enabled is True
    assert analysis.max_tokens == 1024


def test_analysis_failed_status(startup_factory):
    """Failed analyses can store failure status and error information."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        status=StartupAnalysisStatus.FAILED,
        finish_reason="length",
        recommendation=None,
        investment_thesis=None,
        error_message="Startup analysis response was truncated.",
    )

    assert analysis.status == StartupAnalysisStatus.FAILED
    assert analysis.finish_reason == "length"
    assert analysis.recommendation is None
    assert (
        analysis.error_message
        == "Startup analysis response was truncated."
    )


# ---------------------------------------------------------------------------
# UUID / timestamps
# ---------------------------------------------------------------------------


def test_analysis_uuid(db_session, startup_factory):
    """Analysis receives a UUID primary key."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    db_session.add(analysis)
    db_session.flush()

    assert analysis.id is not None


def test_analysis_created_at(db_session, startup_factory):
    """Analysis receives created_at."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    db_session.add(analysis)
    db_session.flush()

    assert analysis.created_at is not None
    assert isinstance(analysis.created_at, datetime)


def test_analysis_updated_at(db_session, startup_factory):
    """Analysis receives updated_at."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    db_session.add(analysis)
    db_session.flush()

    assert analysis.updated_at is not None
    assert isinstance(analysis.updated_at, datetime)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_insert(db_session, startup_factory):
    """StartupAnalysis can be persisted."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    db_session.add(analysis)
    db_session.flush()

    assert analysis.id is not None
    assert analysis.startup_id == startup.id


def test_query(db_session, startup_factory):
    """Persisted analysis can be queried."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    db_session.add(analysis)
    db_session.flush()

    result = (
        db_session.query(StartupAnalysis)
        .filter(StartupAnalysis.id == analysis.id)
        .one()
    )

    assert result.id == analysis.id
    assert result.startup_id == startup.id
    assert result.recommendation == "promising"


# ---------------------------------------------------------------------------
# Startup relationship
# ---------------------------------------------------------------------------


def test_startup_relationship(
    startup_factory,
):
    """Analysis points back to its startup."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    assert analysis.startup == startup
    assert analysis.startup_id == startup.id


def test_startup_analyses_relationship(
    startup_factory,
):
    """Startup exposes its analyses through the reverse relationship."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    assert analysis in startup.analyses


def test_multiple_analyses_for_startup(
    startup_factory,
):
    """A startup can have multiple historical analyses."""

    startup = startup_factory()

    analysis_1 = make_analysis(
        startup=startup,
        analysis_version="3.7.5",
    )

    analysis_2 = make_analysis(
        startup=startup,
        analysis_version="3.7.5",
    )

    assert analysis_1.startup == startup
    assert analysis_2.startup == startup

    assert analysis_1 in startup.analyses
    assert analysis_2 in startup.analyses
    assert len(startup.analyses) == 2


# ---------------------------------------------------------------------------
# LLM execution metadata
# ---------------------------------------------------------------------------


def test_llm_execution_metadata(startup_factory):
    """LLM execution metadata is stored correctly."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=True,
        max_tokens=1024,
        temperature=0.0,
        finish_reason="stop",
    )

    assert analysis.model_name == "Qwen3-8B-Q4_K_M"
    assert analysis.thinking_enabled is True
    assert analysis.max_tokens == 1024
    assert analysis.temperature == 0.0
    assert analysis.finish_reason == "stop"


def test_llm_usage_metadata(startup_factory):
    """Token usage and inference timing are persisted."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        prompt_tokens=1402,
        completion_tokens=1008,
        total_tokens=2410,
        inference_time_seconds=300.25,
    )

    assert analysis.prompt_tokens == 1402
    assert analysis.completion_tokens == 1008
    assert analysis.total_tokens == 2410
    assert analysis.inference_time_seconds == 300.25


# ---------------------------------------------------------------------------
# Analysis result
# ---------------------------------------------------------------------------


def test_result_snapshot(startup_factory):
    """Structured qualitative analysis is preserved."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    assert analysis.result_snapshot is not None
    assert len(analysis.result_snapshot["strengths"]) == 3
    assert len(analysis.result_snapshot["risks"]) == 3
    assert len(analysis.result_snapshot["missing_information"]) == 3


def test_input_snapshot(startup_factory):
    """Original analysis input is preserved."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    assert analysis.input_snapshot is not None
    assert analysis.input_snapshot["company"]["name"] == startup.name


def test_metrics_snapshot(startup_factory):
    """Deterministic financial metrics are preserved."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
    )

    assert analysis.metrics_snapshot is not None
    assert analysis.metrics_snapshot["revenue_multiple"] == 3.4
    assert analysis.metrics_snapshot["ebitda_multiple"] == 17


def test_investment_conclusion(startup_factory):
    """Investment conclusion is stored separately for queryability."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        recommendation="needs_further_diligence",
        investment_thesis=(
            "Strong traction, but valuation and founder information "
            "require further diligence."
        ),
    )

    assert analysis.recommendation == "needs_further_diligence"
    assert "further diligence" in analysis.investment_thesis


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_error_message_nullable_for_success(startup_factory):
    """Successful analyses do not require an error message."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        status=StartupAnalysisStatus.COMPLETED,
        error_message=None,
    )

    assert analysis.error_message is None


def test_error_message_for_failed_analysis(startup_factory):
    """Failed analyses can preserve the generation error."""

    startup = startup_factory()

    analysis = make_analysis(
        startup=startup,
        status=StartupAnalysisStatus.FAILED,
        error_message="Qwen generation failed.",
    )

    assert analysis.error_message == "Qwen generation failed."
