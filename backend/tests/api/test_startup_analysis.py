"""
Tests for Startup Analysis API.

Sprint 3.7.5.4
----------------

The API tests verify only the HTTP boundary:

    HTTP request
        ->
    StartupAnalysisApplicationService
        ->
    StartupAnalysisResponse

They intentionally do not test:

    - financial calculations
    - input construction
    - prompt construction
    - Qwen execution
    - structured parsing
    - persistence mapping
    - repository behavior
    - database transactions
"""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest

from datetime import datetime, timezone

from app.api.startup_analysis import (
    get_startup_analysis_application_service,
)
from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def startup_id():
    """Representative startup identifier."""
    return uuid4()

@pytest.fixture
def persisted_analysis(startup_id):
    """
    Representative persisted StartupAnalysis returned by the
    application service.

    The API consumes the persisted ORM representation, not the
    StartupAnalysisExecution domain envelope.
    """
    now = datetime.now(timezone.utc)

    return StartupAnalysis(
        id=uuid4(),
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
        analysis_version="1.0",
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=False,
        max_tokens=512,
        temperature=0.0,
        status=StartupAnalysisStatus.COMPLETED,
        input_snapshot={},
        metrics_snapshot={},
        result_snapshot={},
        finish_reason="stop",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        inference_time_seconds=1.0,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def analysis_application_service(app):
    """
    Mock the application-service dependency.

    The API test must not invoke the real orchestrator or persistence
    layer.
    """

    service = Mock(
        spec=StartupAnalysisApplicationService,
    )

    app.dependency_overrides[
        get_startup_analysis_application_service
    ] = lambda: service

    yield service

    app.dependency_overrides.pop(
        get_startup_analysis_application_service,
        None,
    )


# =============================================================================
# Successful analysis
# =============================================================================


def test_analyze_startup_success(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    Successful startup analysis returns HTTP 201.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={},
    )

    assert response.status_code == 201

    analysis_application_service.analyze.assert_called_once_with(
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )


# =============================================================================
# STANDARD mode
# =============================================================================


def test_analyze_startup_defaults_to_standard_mode(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    Missing mode defaults to STANDARD.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={},
    )

    assert response.status_code == 201

    analysis_application_service.analyze.assert_called_once_with(
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )


def test_analyze_startup_accepts_standard_mode(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    Explicit STANDARD mode is forwarded unchanged.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={
            "mode": "standard",
        },
    )

    assert response.status_code == 201

    analysis_application_service.analyze.assert_called_once_with(
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )


# =============================================================================
# DEEP mode
# =============================================================================


def test_analyze_startup_accepts_deep_mode(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    DEEP mode is forwarded unchanged to the application service.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={
            "mode": "deep",
        },
    )

    assert response.status_code == 201

    analysis_application_service.analyze.assert_called_once_with(
        startup_id=startup_id,
        mode=StartupAnalysisMode.DEEP,
    )


# =============================================================================
# Request validation
# =============================================================================


def test_analyze_startup_rejects_invalid_mode(
    client,
    startup_id,
    analysis_application_service,
):
    """
    Invalid analysis mode is rejected by request validation.

    The application service must not be called.
    """

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={
            "mode": "invalid",
        },
    )

    assert response.status_code == 422

    analysis_application_service.analyze.assert_not_called()


def test_analyze_startup_rejects_invalid_startup_id(
    client,
    analysis_application_service,
):
    """
    startup_id must be a valid UUID.
    """

    response = client.post(
        "/api/v1/startups/not-a-uuid/analysis",
        json={},
    )

    assert response.status_code == 422

    analysis_application_service.analyze.assert_not_called()


# =============================================================================
# Response contract
# =============================================================================


def test_analyze_startup_returns_api_response(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    The persisted StartupAnalysis is serialized into the standard
    ApiResponse envelope.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Startup analysis completed"
    assert body["data"] is not None


def test_analyze_startup_response_contains_persisted_identity(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    Response identity comes from the persisted StartupAnalysis record.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={},
    )

    assert response.status_code == 201

    data = response.json()["data"]

    assert data["id"] == str(persisted_analysis.id)
    assert data["startup_id"] == str(startup_id)
    assert data["mode"] == "standard"
    assert data["status"] == "completed"


# =============================================================================
# Generation configuration boundary
# =============================================================================


def test_analyze_startup_does_not_forward_generation_configuration(
    client,
    startup_id,
    persisted_analysis,
    analysis_application_service,
):
    """
    Generation configuration is not part of the application-service
    API contract.

    Only startup_id and mode are forwarded.
    """

    analysis_application_service.analyze.return_value = (
        persisted_analysis
    )

    response = client.post(
        f"/api/v1/startups/{startup_id}/analysis",
        json={
            "mode": "deep",
            "model": "some-model",
            "temperature": 0.7,
            "max_tokens": 4096,
            "thinking_enabled": True,
        },
    )

    # This assertion intentionally depends on the request schema's
    # extra-field policy.
    #
    # If StartupAnalysisRequest uses extra="ignore", the request succeeds.
    # If it uses extra="forbid", FastAPI returns 422.
    #
    # The important architectural rule is that these fields are never
    # forwarded to the application service.
    if response.status_code == 201:
        analysis_application_service.analyze.assert_called_once_with(
            startup_id=startup_id,
            mode=StartupAnalysisMode.DEEP,
        )
    else:
        assert response.status_code == 422
        analysis_application_service.analyze.assert_not_called()


# =============================================================================
# Application-service failure
# =============================================================================


def test_analyze_startup_propagates_application_error(
    client,
    startup_id,
    analysis_application_service,
):
    """
    Unexpected application-service errors are not silently converted
    into a successful API response.

    Exact exception-to-HTTP mapping belongs to the centralized
    exception-handler layer.
    """

    analysis_application_service.analyze.side_effect = RuntimeError(
        "analysis failed"
    )

    with pytest.raises(
        RuntimeError,
        match="analysis failed",
    ):
        client.post(
            f"/api/v1/startups/{startup_id}/analysis",
            json={},
        )

    analysis_application_service.analyze.assert_called_once_with(
        startup_id=startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )
