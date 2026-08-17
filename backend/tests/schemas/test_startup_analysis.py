"""
Tests for startup-analysis API schemas.

3.7.5.4.2
----------

Validate the HTTP contract for:

    StartupAnalysisRequest
    StartupAnalysisResponse

These tests intentionally verify the API boundary only.

They do not test:
    - StartupAnalysisOrchestrator
    - FinancialMetricsService
    - LLM execution
    - StartupAnalysisPersistenceService
    - database persistence
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.analysis import (
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.schemas.startup_analysis import (
    StartupAnalysisRequest,
    StartupAnalysisResponse,
    StartupAnalysisHistoryItem,
    StartupAnalysisHistoryPage,
    StartupAnalysisResponse,
    StartupAnalysisHistoryResponse,
)

from app.schemas.pagination import PaginationMeta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def startup_id():
    """Stable startup identifier."""
    return uuid4()


@pytest.fixture
def analysis_id():
    """Stable analysis identifier."""
    return uuid4()


@pytest.fixture
def created_at():
    """Representative creation timestamp."""
    return datetime(
        2026,
        8,
        16,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )


@pytest.fixture
def updated_at():
    """Representative update timestamp."""
    return datetime(
        2026,
        8,
        16,
        10,
        2,
        30,
        tzinfo=timezone.utc,
    )


@pytest.fixture
def response_data(
    startup_id,
    analysis_id,
    created_at,
    updated_at,
):
    """
    Representative persisted StartupAnalysis response payload.
    """
    return {
        "id": analysis_id,
        "startup_id": startup_id,
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
        "created_at": created_at,
        "updated_at": updated_at,
    }


# ---------------------------------------------------------------------------
# StartupAnalysisRequest
# ---------------------------------------------------------------------------


def test_request_defaults_to_standard_mode():
    """
    Omitting mode must select STANDARD.

    The API controls analysis depth through mode only. Generation
    parameters are resolved internally by StartupAnalysisConfig.
    """
    request = StartupAnalysisRequest()

    assert request.mode == StartupAnalysisMode.STANDARD


def test_request_accepts_standard_mode():
    """STANDARD mode is accepted explicitly."""
    request = StartupAnalysisRequest(
        mode=StartupAnalysisMode.STANDARD,
    )

    assert request.mode == StartupAnalysisMode.STANDARD


def test_request_accepts_deep_mode():
    """DEEP mode is accepted explicitly."""
    request = StartupAnalysisRequest(
        mode=StartupAnalysisMode.DEEP,
    )

    assert request.mode == StartupAnalysisMode.DEEP


def test_request_accepts_enum_value_strings():
    """
    API clients normally send JSON strings rather than Python enums.
    """
    standard = StartupAnalysisRequest(mode="standard")
    deep = StartupAnalysisRequest(mode="deep")

    assert standard.mode == StartupAnalysisMode.STANDARD
    assert deep.mode == StartupAnalysisMode.DEEP


def test_request_rejects_invalid_mode():
    """Unsupported analysis modes must be rejected."""
    with pytest.raises(ValidationError):
        StartupAnalysisRequest(
            mode="invalid",
        )


def test_request_rejects_unknown_fields():
    """
    The API request must not allow clients to inject generation
    configuration or other unsupported parameters.
    """
    with pytest.raises(ValidationError):
        StartupAnalysisRequest(
            mode=StartupAnalysisMode.STANDARD,
            model_name="some-other-model",
        )


def test_request_does_not_expose_generation_configuration():
    """
    Generation parameters belong to StartupAnalysisConfig, not the API
    request contract.
    """
    fields = StartupAnalysisRequest.model_fields

    assert "mode" in fields

    assert "model_name" not in fields
    assert "thinking_enabled" not in fields
    assert "max_tokens" not in fields
    assert "temperature" not in fields
    assert "analysis_version" not in fields


# ---------------------------------------------------------------------------
# StartupAnalysisResponse
# ---------------------------------------------------------------------------


def test_response_accepts_complete_payload(response_data):
    """A complete persisted analysis can be represented by the API schema."""
    response = StartupAnalysisResponse(**response_data)

    assert response.id == response_data["id"]
    assert response.startup_id == response_data["startup_id"]

    assert response.mode == StartupAnalysisMode.STANDARD
    assert response.status == StartupAnalysisStatus.COMPLETED

    assert response.analysis_version == "3.7.5"

    assert response.model_name == "Qwen3-8B-Q4_K_M"
    assert response.thinking_enabled is False
    assert response.max_tokens == 768
    assert response.temperature == 0.0

    assert response.finish_reason == "stop"

    assert response.prompt_tokens == 1400
    assert response.completion_tokens == 500
    assert response.total_tokens == 1900
    assert response.inference_time_seconds == 150.0

    assert response.recommendation == "promising"
    assert response.investment_thesis == (
        "Strong growth and traction, subject to further diligence."
    )

    assert response.created_at == response_data["created_at"]
    assert response.updated_at == response_data["updated_at"]


def test_response_accepts_deep_mode(response_data):
    """DEEP mode is represented correctly."""
    response_data.update(
        {
            "mode": StartupAnalysisMode.DEEP,
            "thinking_enabled": True,
            "max_tokens": 1024,
        }
    )

    response = StartupAnalysisResponse(**response_data)

    assert response.mode == StartupAnalysisMode.DEEP
    assert response.thinking_enabled is True
    assert response.max_tokens == 1024


def test_response_accepts_failed_status(response_data):
    """The response schema supports the persisted FAILED lifecycle state."""
    response_data["status"] = StartupAnalysisStatus.FAILED

    response = StartupAnalysisResponse(**response_data)

    assert response.status == StartupAnalysisStatus.FAILED


def test_response_accepts_nullable_execution_metadata(response_data):
    """
    Provider metadata may be unavailable and is therefore nullable.
    """
    response_data.update(
        {
            "finish_reason": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "inference_time_seconds": None,
            "recommendation": None,
            "investment_thesis": None,
        }
    )

    response = StartupAnalysisResponse(**response_data)

    assert response.finish_reason is None
    assert response.prompt_tokens is None
    assert response.completion_tokens is None
    assert response.total_tokens is None
    assert response.inference_time_seconds is None
    assert response.recommendation is None
    assert response.investment_thesis is None


def test_response_accepts_string_enum_values(response_data):
    """
    JSON responses use persisted enum values rather than Python enum
    objects.
    """
    response_data.update(
        {
            "mode": "deep",
            "status": "completed",
        }
    )

    response = StartupAnalysisResponse(**response_data)

    assert response.mode == StartupAnalysisMode.DEEP
    assert response.status == StartupAnalysisStatus.COMPLETED


def test_response_rejects_invalid_mode(response_data):
    """Invalid persisted mode values must not enter the API contract."""
    response_data["mode"] = "invalid"

    with pytest.raises(ValidationError):
        StartupAnalysisResponse(**response_data)


def test_response_rejects_invalid_status(response_data):
    """Invalid persisted status values must not enter the API contract."""
    response_data["status"] = "running"

    with pytest.raises(ValidationError):
        StartupAnalysisResponse(**response_data)


def test_response_rejects_unknown_fields(response_data):
    """
    API responses must have a controlled contract.

    Historical snapshots are deliberately not part of this response.
    """
    response_data["input_snapshot"] = {
        "company": {
            "name": "Example Startup",
        }
    }

    with pytest.raises(ValidationError):
        StartupAnalysisResponse(**response_data)


def test_response_does_not_expose_snapshots():
    """
    Historical snapshots belong to persistence/history, not the summary
    response returned by the initial analysis API.
    """
    fields = StartupAnalysisResponse.model_fields

    assert "input_snapshot" not in fields
    assert "metrics_snapshot" not in fields
    assert "result_snapshot" not in fields


def test_response_contains_only_api_contract_fields(response_data):
    """
    Protect against accidental expansion of the HTTP response contract.
    """
    response = StartupAnalysisResponse(**response_data)

    expected_fields = {
        "id",
        "startup_id",
        "mode",
        "status",
        "analysis_version",
        "model_name",
        "thinking_enabled",
        "max_tokens",
        "temperature",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "inference_time_seconds",
        "recommendation",
        "investment_thesis",
        "created_at",
        "updated_at",
    }

    assert set(response.model_dump().keys()) == expected_fields


# ---------------------------------------------------------------------------
# ORM compatibility
# ---------------------------------------------------------------------------


def test_response_supports_from_attributes():
    """
    BaseSchema enables ORM-compatible serialization.

    This is important because StartupAnalysisResponse will eventually be
    created directly from the StartupAnalysis ORM object.
    """

    class FakeAnalysis:
        id = uuid4()
        startup_id = uuid4()
        mode = StartupAnalysisMode.STANDARD
        status = StartupAnalysisStatus.COMPLETED
        analysis_version = "3.7.5"

        model_name = "Qwen3-8B-Q4_K_M"
        thinking_enabled = False
        max_tokens = 768
        temperature = 0.0

        finish_reason = "stop"
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150
        inference_time_seconds = 10.5

        recommendation = "promising"
        investment_thesis = "Promising startup."

        created_at = datetime(
            2026,
            8,
            16,
            10,
            0,
            tzinfo=timezone.utc,
        )
        updated_at = datetime(
            2026,
            8,
            16,
            10,
            1,
            tzinfo=timezone.utc,
        )

    response = StartupAnalysisResponse.model_validate(
        FakeAnalysis(),
        from_attributes=True,
    )

    assert response.id == FakeAnalysis.id
    assert response.startup_id == FakeAnalysis.startup_id
    assert response.mode == StartupAnalysisMode.STANDARD
    assert response.status == StartupAnalysisStatus.COMPLETED
    assert response.model_name == "Qwen3-8B-Q4_K_M"
    assert response.recommendation == "promising"


# ---------------------------------------------------------------------------
# Assignment validation
# ---------------------------------------------------------------------------


def test_request_assignment_validation():
    """
    BaseSchema enables validate_assignment=True.
    """
    request = StartupAnalysisRequest()

    request.mode = StartupAnalysisMode.DEEP

    assert request.mode == StartupAnalysisMode.DEEP

    with pytest.raises(ValidationError):
        request.mode = "invalid"


def test_response_assignment_validation(response_data):
    """
    Invalid assignments must be rejected after model creation as well.
    """
    response = StartupAnalysisResponse(**response_data)

    with pytest.raises(ValidationError):
        response.mode = "invalid"

    with pytest.raises(ValidationError):
        response.status = "invalid"

def test_history_item_accepts_summary_payload(response_data):
    item = StartupAnalysisHistoryItem(
        **{
            key: response_data[key]
            for key in (
                "id",
                "startup_id",
                "mode",
                "status",
                "analysis_version",
                "model_name",
                "thinking_enabled",
                "max_tokens",
                "temperature",
                "recommendation",
                "created_at",
                "updated_at",
            )
        }
    )

    assert item.id == response_data["id"]
    assert item.startup_id == response_data["startup_id"]
    assert item.mode == StartupAnalysisMode.STANDARD
    assert item.status == StartupAnalysisStatus.COMPLETED

def test_history_response_accepts_snapshots(response_data):
    data = {
        **response_data,
        "input_snapshot": {
            "startup_id": str(response_data["startup_id"]),
            "company": {
                "name": "Example Startup",
            },
        },
        "metrics_snapshot": {
            "revenue": 1000000,
            "revenue_growth": 0.35,
        },
        "result_snapshot": {
            "preliminary_recommendation": "promising",
            "investment_thesis": "Strong growth potential.",
        },
        "error_message": None,
    }

    response = StartupAnalysisHistoryResponse(**data)

    assert response.input_snapshot["company"]["name"] == "Example Startup"
    assert response.metrics_snapshot["revenue"] == 1000000
    assert (
        response.result_snapshot["preliminary_recommendation"]
        == "promising"
    )
    assert response.error_message is None

def test_history_page_accepts_pagination(response_data):
    item = StartupAnalysisHistoryItem(
        id=response_data["id"],
        startup_id=response_data["startup_id"],
        mode=response_data["mode"],
        status=response_data["status"],
        analysis_version=response_data["analysis_version"],
        model_name=response_data["model_name"],
        thinking_enabled=response_data["thinking_enabled"],
        max_tokens=response_data["max_tokens"],
        temperature=response_data["temperature"],
        recommendation=response_data["recommendation"],
        created_at=response_data["created_at"],
        updated_at=response_data["updated_at"],
    )

    page = StartupAnalysisHistoryPage(
        items=[item],
        pagination=PaginationMeta(
            page=1,
            per_page=20,
            total_items=1,
            total_pages=1,
            has_previous=False,
            has_next=False,
        ),
    )

    assert len(page.items) == 1
    assert page.pagination.total_items == 1

def test_history_item_does_not_expose_snapshots():
    fields = StartupAnalysisHistoryItem.model_fields

    assert "input_snapshot" not in fields
    assert "metrics_snapshot" not in fields
    assert "result_snapshot" not in fields
