"""
Tests for Startup Analysis History API.

Sprint 3.7.5.5.5
----------------

The API history tests verify only the HTTP boundary:

    HTTP request
        ->
    StartupAnalysisHistoryService
        ->
    History response schema

These tests intentionally do not test:

    - SQL queries
    - repository filtering
    - repository pagination
    - analysis orchestration
    - financial calculations
    - LLM execution
    - persistence
    - transaction management
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.api.startup_analysis import (
    get_startup_analysis_history_service,
)
from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.services.startup_analysis_history import (
    StartupAnalysisHistoryService,
)
from app.schemas.startup_analysis import (
    StartupAnalysisHistoryItem,
    StartupAnalysisHistoryPage,
    StartupAnalysisHistoryResponse,
    StartupAnalysisRequest,
    StartupAnalysisResponse,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def startup_id():
    """Representative startup identifier."""
    return uuid4()


@pytest.fixture
def analysis_id():
    """Representative analysis identifier."""
    return uuid4()


@pytest.fixture
def created_at():
    """Deterministic persisted-analysis timestamp."""
    return datetime(
        2026,
        8,
        17,
        7,
        0,
        0,
        tzinfo=timezone.utc,
    )


@pytest.fixture
def persisted_analysis(
    startup_id,
    analysis_id,
    created_at,
):
    """
    Representative persisted StartupAnalysis.

    This object intentionally contains the complete historical
    snapshots because the detail endpoint exposes them.
    """

    return StartupAnalysis(
        id=analysis_id,
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version="3.7.5",
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=False,
        max_tokens=768,
        temperature=0.0,
        finish_reason="stop",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        inference_time_seconds=1.0,
        recommendation="promising",
        investment_thesis="Strong growth potential.",
        input_snapshot={
            "startup_id": str(startup_id),
            "company": {
                "name": "Example Startup",
            },
        },
        metrics_snapshot={
            "revenue": 1_000_000,
            "revenue_growth": 0.35,
        },
        result_snapshot={
            "preliminary_recommendation": "promising",
            "investment_thesis": "Strong growth potential.",
        },
        error_message=None,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.fixture
def history_service(app):
    """
    Mock StartupAnalysisHistoryService at the FastAPI dependency
    boundary.
    """

    service = Mock(
        spec=StartupAnalysisHistoryService,
    )

    app.dependency_overrides[
        get_startup_analysis_history_service
    ] = lambda: service

    yield service

    app.dependency_overrides.pop(
        get_startup_analysis_history_service,
        None,
    )


# =============================================================================
# List history
# =============================================================================


def test_list_startup_analysis_history_success(
    client,
    startup_id,
    persisted_analysis,
    history_service,
):
    """
    History list endpoint returns HTTP 200 with a paginated result.
    """

    history_service.list_history.return_value = (
        [persisted_analysis],
        1,
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis",
    )

    assert response.status_code == 200

    history_service.list_history.assert_called_once_with(
        startup_id,
        page=1,
        per_page=20,
    )

    body = response.json()

    assert body["success"] is True
    assert body["message"] == (
        "Startup analysis history retrieved"
    )

    assert body["data"]["pagination"]["page"] == 1
    assert body["data"]["pagination"]["per_page"] == 20
    assert body["data"]["pagination"]["total_items"] == 1
    assert body["data"]["pagination"]["total_pages"] == 1
    assert body["data"]["pagination"]["has_previous"] is False
    assert body["data"]["pagination"]["has_next"] is False

    assert len(body["data"]["items"]) == 1


def test_list_startup_analysis_history_returns_summary_item(
    client,
    startup_id,
    persisted_analysis,
    history_service,
):
    """
    History list exposes the lightweight HistoryItem representation
    rather than historical snapshots.
    """

    history_service.list_history.return_value = (
        [persisted_analysis],
        1,
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis",
    )

    assert response.status_code == 200

    item = response.json()["data"]["items"][0]

    assert item["id"] == str(persisted_analysis.id)
    assert item["startup_id"] == str(startup_id)
    assert item["mode"] == "standard"
    assert item["status"] == "completed"
    assert item["analysis_version"] == "3.7.5"
    assert item["model_name"] == "Qwen3-8B-Q4_K_M"
    assert item["thinking_enabled"] is False
    assert item["max_tokens"] == 768
    assert item["temperature"] == 0.0
    assert item["recommendation"] == "promising"

    assert "input_snapshot" not in item
    assert "metrics_snapshot" not in item
    assert "result_snapshot" not in item


def test_list_startup_analysis_history_forwards_pagination(
    client,
    startup_id,
    history_service,
):
    """
    Query pagination parameters are forwarded unchanged.
    """

    history_service.list_history.return_value = (
        [],
        35,
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis"
        "?page=2&per_page=10",
    )

    assert response.status_code == 200

    history_service.list_history.assert_called_once_with(
        startup_id,
        page=2,
        per_page=10,
    )

    pagination = response.json()["data"]["pagination"]

    assert pagination["page"] == 2
    assert pagination["per_page"] == 10
    assert pagination["total_items"] == 35
    assert pagination["total_pages"] == 4
    assert pagination["has_previous"] is True
    assert pagination["has_next"] is True


def test_list_startup_analysis_history_last_page(
    client,
    startup_id,
    history_service,
):
    """
    Last page correctly reports has_next=False.
    """

    history_service.list_history.return_value = (
        [],
        25,
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis"
        "?page=3&per_page=10",
    )

    assert response.status_code == 200

    pagination = response.json()["data"]["pagination"]

    assert pagination["page"] == 3
    assert pagination["per_page"] == 10
    assert pagination["total_items"] == 25
    assert pagination["total_pages"] == 3
    assert pagination["has_previous"] is True
    assert pagination["has_next"] is False


def test_list_startup_analysis_history_empty(
    client,
    startup_id,
    history_service,
):
    """
    A startup with no history returns an empty page.
    """

    history_service.list_history.return_value = (
        [],
        0,
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["data"]["items"] == []

    pagination = body["data"]["pagination"]

    assert pagination["page"] == 1
    assert pagination["per_page"] == 20
    assert pagination["total_items"] == 0
    assert pagination["total_pages"] == 0
    assert pagination["has_previous"] is False
    assert pagination["has_next"] is False


# =============================================================================
# List validation
# =============================================================================


def test_list_startup_analysis_history_rejects_invalid_startup_id(
    client,
    history_service,
):
    """
    startup_id must be a valid UUID.
    """

    response = client.get(
        "/api/v1/startups/not-a-uuid/analysis",
    )

    assert response.status_code == 422

    history_service.list_history.assert_not_called()


def test_list_startup_analysis_history_rejects_invalid_page(
    client,
    startup_id,
    history_service,
):
    """
    page must be >= 1.
    """

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis"
        "?page=0",
    )

    assert response.status_code == 422

    history_service.list_history.assert_not_called()


def test_list_startup_analysis_history_rejects_invalid_per_page(
    client,
    startup_id,
    history_service,
):
    """
    per_page must be >= 1.
    """

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis"
        "?per_page=0",
    )

    assert response.status_code == 422

    history_service.list_history.assert_not_called()


# =============================================================================
# History detail
# =============================================================================


def test_get_startup_analysis_history_success(
    client,
    startup_id,
    analysis_id,
    persisted_analysis,
    history_service,
):
    """
    Historical analysis detail returns HTTP 200.
    """

    history_service.get_history.return_value = (
        persisted_analysis
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis/{analysis_id}",
    )

    assert response.status_code == 200

    history_service.get_history.assert_called_once_with(
        startup_id,
        analysis_id,
    )

    body = response.json()

    assert body["success"] is True
    assert body["message"] == (
        "Startup analysis history retrieved"
    )

    data = body["data"]

    assert data["id"] == str(analysis_id)
    assert data["startup_id"] == str(startup_id)
    assert data["mode"] == "standard"
    assert data["status"] == "completed"


def test_get_startup_analysis_history_returns_snapshots(
    client,
    startup_id,
    analysis_id,
    persisted_analysis,
    history_service,
):
    """
    Historical detail exposes the immutable execution snapshots.
    """

    history_service.get_history.return_value = (
        persisted_analysis
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis/{analysis_id}",
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["input_snapshot"] == (
        persisted_analysis.input_snapshot
    )

    assert data["metrics_snapshot"] == (
        persisted_analysis.metrics_snapshot
    )

    assert data["result_snapshot"] == (
        persisted_analysis.result_snapshot
    )

    assert data["error_message"] is None


def test_get_startup_analysis_history_preserves_execution_metadata(
    client,
    startup_id,
    analysis_id,
    persisted_analysis,
    history_service,
):
    """
    Historical detail preserves the persisted execution metadata.
    """

    history_service.get_history.return_value = (
        persisted_analysis
    )

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis/{analysis_id}",
    )

    assert response.status_code == 200

    data = response.json()["data"]

    assert data["model_name"] == "Qwen3-8B-Q4_K_M"
    assert data["thinking_enabled"] is False
    assert data["max_tokens"] == 768
    assert data["temperature"] == 0.0

    assert data["finish_reason"] == "stop"
    assert data["prompt_tokens"] == 100
    assert data["completion_tokens"] == 50
    assert data["total_tokens"] == 150
    assert data["inference_time_seconds"] == 1.0

    assert data["recommendation"] == "promising"
    assert data["investment_thesis"] == (
        "Strong growth potential."
    )


def test_get_startup_analysis_history_not_found(
    client,
    startup_id,
    analysis_id,
    history_service,
):
    """
    Missing or cross-startup history is returned as HTTP 404.
    """

    history_service.get_history.return_value = None

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis/{analysis_id}",
    )

    assert response.status_code == 404

    history_service.get_history.assert_called_once_with(
        startup_id,
        analysis_id,
    )

    body = response.json()

    assert body["detail"] == "Startup analysis not found"


# =============================================================================
# Detail validation
# =============================================================================


def test_get_startup_analysis_history_rejects_invalid_startup_id(
    client,
    analysis_id,
    history_service,
):
    """
    startup_id must be a valid UUID.
    """

    response = client.get(
        f"/api/v1/startups/not-a-uuid/analysis/{analysis_id}",
    )

    assert response.status_code == 422

    history_service.get_history.assert_not_called()


def test_get_startup_analysis_history_rejects_invalid_analysis_id(
    client,
    startup_id,
    history_service,
):
    """
    analysis_id must be a valid UUID.
    """

    response = client.get(
        f"/api/v1/startups/{startup_id}/analysis/not-a-uuid",
    )

    assert response.status_code == 422

    history_service.get_history.assert_not_called()
