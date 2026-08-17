"""
Tests for StartupAnalysisRepository.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
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

def test_get_by_startup_and_id_rejects_other_startup(
    repository: StartupAnalysisRepository,
    analysis: StartupAnalysis,
):
    """
    An analysis belonging to another startup must not be returned.
    """

    result = repository.get_by_startup_and_id(
        uuid4(),
        analysis.id,
    )

    assert result is None

# 3.7.5.5.2.C — Pagination tests

@pytest.fixture
def analysis_history(
    db_session: Session,
):
    """Create multiple analyses for two startups."""


    startup_id = uuid4()
    other_startup_id = uuid4()


    now = datetime.now(timezone.utc)


    analyses = [
        StartupAnalysis(
            id=uuid4(),
            startup_id=startup_id,
            created_at=now - timedelta(minutes=30),
            mode=StartupAnalysisMode.STANDARD,
            status=StartupAnalysisStatus.COMPLETED,
            model_name="Qwen3-8B-Q4_K_M",
            max_tokens=768,
            temperature=0.0,
        ),
        StartupAnalysis(
            id=uuid4(),
            startup_id=startup_id,
            created_at=now - timedelta(minutes=20),
            mode=StartupAnalysisMode.DEEP,
            status=StartupAnalysisStatus.COMPLETED,
            model_name="Qwen3-8B-Q4_K_M",
            max_tokens=1024,
            temperature=0.0,
        ),
        StartupAnalysis(
            id=uuid4(),
            startup_id=startup_id,
            created_at=now - timedelta(minutes=10),
            mode=StartupAnalysisMode.STANDARD,
            status=StartupAnalysisStatus.COMPLETED,
            model_name="Qwen3-8B-Q4_K_M",
            max_tokens=768,
            temperature=0.0,
        ),
        StartupAnalysis(
            id=uuid4(),
            startup_id=other_startup_id,
            created_at=now,
            mode=StartupAnalysisMode.STANDARD,
            status=StartupAnalysisStatus.COMPLETED,
            model_name="Qwen3-8B-Q4_K_M",
            max_tokens=768,
            temperature=0.0,
        ),
    ]


    db_session.add_all(analyses)
    db_session.commit()


    for item in analyses:
        db_session.refresh(item)


    return {
        "startup_id": startup_id,
        "other_startup_id": other_startup_id,
        "analyses": analyses,
    }

# Test filtering + ordering
def test_list_by_startup_returns_newest_first(
    repository: StartupAnalysisRepository,
    analysis_history,
):
    """History should be filtered by startup and ordered newest first."""


    startup_id = analysis_history["startup_id"]


    items, total_items = repository.list_by_startup(
        startup_id,
    )


    assert total_items == 3
    assert len(items) == 3


    assert items[0].created_at > items[1].created_at
    assert items[1].created_at > items[2].created_at


    assert all(
        item.startup_id == startup_id
        for item in items
    )

# Test page size
def test_list_by_startup_applies_per_page(
    repository: StartupAnalysisRepository,
    analysis_history,
):
    """History should limit the number of returned records."""


    startup_id = analysis_history["startup_id"]


    items, total_items = repository.list_by_startup(
        startup_id,
        page=1,
        per_page=2,
    )


    assert total_items == 3
    assert len(items) == 2

# Test second page
def test_list_by_startup_applies_page_offset(
    repository: StartupAnalysisRepository,
    analysis_history,
):
    """Page two should return records after page one."""


    startup_id = analysis_history["startup_id"]


    items, total_items = repository.list_by_startup(
        startup_id,
        page=2,
        per_page=2,
    )


    assert total_items == 3
    assert len(items) == 1

# Test empty history
def test_list_by_startup_returns_empty_history(
    repository: StartupAnalysisRepository,
):
    """A startup with no analyses should return an empty list."""


    items, total_items = repository.list_by_startup(
        uuid4(),
    )


    assert items == []
    assert total_items == 0

# Test another startup's history is excluded
def test_list_by_startup_excludes_other_startups(
    repository: StartupAnalysisRepository,
    analysis_history,
):
    """History must never include another startup's analyses."""


    startup_id = analysis_history["startup_id"]
    other_startup_id = analysis_history["other_startup_id"]


    items, total_items = repository.list_by_startup(
        startup_id,
    )


    assert total_items == 3
    assert len(items) == 3


    assert all(
        item.startup_id != other_startup_id
        for item in items
    )

