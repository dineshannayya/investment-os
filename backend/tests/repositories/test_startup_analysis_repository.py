"""
Tests for StartupAnalysisRepository.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.repositories.startup_analysis import StartupAnalysisRepository


@pytest.fixture
def repository(db_session: Session) -> StartupAnalysisRepository:
    """Return StartupAnalysisRepository instance."""

    return StartupAnalysisRepository(db_session)


@pytest.fixture
def analysis(db_session: Session) -> StartupAnalysis:
    """Create and persist a sample startup analysis."""

    analysis = StartupAnalysis(
        id=uuid4(),
        startup_id=uuid4(),
        mode=StartupAnalysisMode.STANDARD,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version="3.7.5",
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=False,
        max_tokens=768,
        temperature=0.0,
        finish_reason="stop",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        inference_time_seconds=10.5,
        recommendation="consider",
        investment_thesis="Strong opportunity with manageable risks.",
        input_snapshot={
            "startup_id": "test-startup",
            "company": {"name": "Test Startup"},
        },
        metrics_snapshot={
            "revenue_multiple": 3.4,
            "ebitda_multiple": 17,
        },
        result_snapshot={
            "preliminary_recommendation": "consider",
            "investment_thesis": "Strong opportunity with manageable risks.",
        },
        error_message=None,
    )

    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    return analysis


def test_get_by_id(
    repository: StartupAnalysisRepository,
    analysis: StartupAnalysis,
):
    """Should return startup analysis by ID."""

    result = repository.get_by_id(analysis.id)

    assert result is not None
    assert result.id == analysis.id
    assert result.startup_id == analysis.startup_id


def test_get_by_id_not_found(
    repository: StartupAnalysisRepository,
):
    """Unknown ID should return None."""

    result = repository.get_by_id(uuid4())

    assert result is None


def test_create(
    repository: StartupAnalysisRepository,
    db_session: Session,
):
    """Should create and persist a startup analysis."""

    analysis = StartupAnalysis(
        id=uuid4(),
        startup_id=uuid4(),
        mode=StartupAnalysisMode.STANDARD,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version="3.7.5",
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=False,
        max_tokens=768,
        temperature=0.0,
    )

    result = repository.create(analysis)

    assert result is analysis
    assert result.id == analysis.id

    db_session.commit()

    persisted = db_session.get(StartupAnalysis, analysis.id)

    assert persisted is not None
    assert persisted.startup_id == analysis.startup_id


def test_update(
    repository: StartupAnalysisRepository,
    analysis: StartupAnalysis,
):
    """Should update a startup analysis."""

    analysis.recommendation = "invest"
    analysis.investment_thesis = "Updated investment thesis."

    result = repository.update(analysis)

    assert result is analysis
    assert result.recommendation == "invest"
    assert result.investment_thesis == "Updated investment thesis."


def test_delete(
    repository: StartupAnalysisRepository,
    analysis: StartupAnalysis,
):
    """Should delete a startup analysis."""

    repository.delete(analysis)

    assert repository.get_by_id(analysis.id) is None
