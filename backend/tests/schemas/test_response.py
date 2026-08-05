"""
Unit tests for API response schemas.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.config.error_codes import ErrorCode
from app.schemas.error import ErrorDetail
from app.schemas.pagination import PaginationMeta
from app.schemas.response import ApiResponse, ResponseMeta

# ---------------------------------------------------------------------------
# ResponseMeta
# ---------------------------------------------------------------------------


def test_create_response_meta() -> None:
    """A valid ResponseMeta should be created successfully."""

    pagination = PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )

    meta = ResponseMeta(
        request_id="req-123",
        pagination=pagination,
    )

    assert meta.request_id == "req-123"
    assert meta.pagination == pagination
    assert isinstance(meta.timestamp, datetime)
    assert meta.timestamp.tzinfo == UTC


def test_response_meta_defaults() -> None:
    """Optional fields should default correctly."""

    meta = ResponseMeta()

    assert meta.request_id is None
    assert meta.pagination is None
    assert isinstance(meta.timestamp, datetime)


# ---------------------------------------------------------------------------
# ApiResponse - Success
# ---------------------------------------------------------------------------


def test_create_success_response() -> None:
    """Create a successful response."""

    response = ApiResponse[dict](
        success=True,
        message="Request completed successfully.",
        data={"id": 1, "name": "Camera"},
    )

    assert response.success is True
    assert response.message == "Request completed successfully."
    assert response.data == {"id": 1, "name": "Camera"}
    assert response.meta is None
    assert response.errors == []


def test_success_response_with_meta() -> None:
    """Success response with metadata."""

    meta = ResponseMeta(request_id="req-123")

    response = ApiResponse[dict](
        success=True,
        message="OK",
        data={"id": 1},
        meta=meta,
    )

    assert response.meta == meta
    assert response.errors == []


# ---------------------------------------------------------------------------
# ApiResponse - Error
# ---------------------------------------------------------------------------


def test_create_error_response() -> None:
    """Create an error response."""

    error = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Startup not found.",
    )

    response = ApiResponse[None](
        success=False,
        message="Request failed.",
        errors=[error],
    )

    assert response.success is False
    assert response.message == "Request failed."
    assert response.data is None
    assert len(response.errors) == 1
    assert response.errors[0] == error


def test_multiple_errors() -> None:
    """Multiple errors should be supported."""

    errors = [
        ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid email.",
            field="email",
        ),
        ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Password too short.",
            field="password",
        ),
    ]

    response = ApiResponse[None](
        success=False,
        message="Validation failed.",
        errors=errors,
    )

    assert len(response.errors) == 2


# ---------------------------------------------------------------------------
# Generic Payloads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"id": 1},
        ["a", "b", "c"],
        "completed",
        123,
        True,
    ],
)
def test_generic_payload_types(payload) -> None:
    """ApiResponse should support different payload types."""

    response = ApiResponse(
        success=True,
        message="OK",
        data=payload,
    )

    assert response.data == payload


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_missing_success() -> None:
    """Missing success should raise ValidationError."""

    with pytest.raises(ValidationError):
        ApiResponse(
            message="OK",
        )


def test_missing_message() -> None:
    """Missing message should raise ValidationError."""

    with pytest.raises(ValidationError):
        ApiResponse(
            success=True,
        )


def test_extra_field_forbidden() -> None:
    """Unexpected fields should raise ValidationError."""

    with pytest.raises(ValidationError):
        ApiResponse(
            success=True,
            message="OK",
            unknown_field=True,
        )


# ---------------------------------------------------------------------------
# Assignment Validation
# ---------------------------------------------------------------------------


def test_assignment_validation_success() -> None:
    """Valid assignment should succeed."""

    response = ApiResponse(
        success=True,
        message="OK",
    )

    response.message = "Updated"

    assert response.message == "Updated"


def test_assignment_validation_failure() -> None:
    """Invalid assignment should raise ValidationError."""

    response = ApiResponse(
        success=True,
        message="OK",
    )

    with pytest.raises(ValidationError):
        response.success = object()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_model_dump() -> None:
    """model_dump() should return expected structure."""

    response = ApiResponse[dict](
        success=True,
        message="OK",
        data={"id": 1},
    )

    data = response.model_dump()

    assert data["success"] is True
    assert data["message"] == "OK"
    assert data["data"] == {"id": 1}
    assert data["errors"] == []


def test_model_dump_json() -> None:
    """model_dump_json() should serialize correctly."""

    response = ApiResponse[dict](
        success=True,
        message="OK",
        data={"id": 1},
    )

    data = json.loads(response.model_dump_json())

    assert data["success"] is True
    assert data["message"] == "OK"
    assert data["data"] == {"id": 1}


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_response_objects() -> None:
    """Equivalent responses should serialize identically."""

    response1 = ApiResponse(
        success=True,
        message="OK",
        data={"id": 1},
    )

    response2 = ApiResponse(
        success=True,
        message="OK",
        data={"id": 1},
    )

    assert response1.model_dump() == response2.model_dump()


def test_fail_without_errors():
    response = ApiResponse.fail(
        message="Boom",
    )

    assert response.errors == []
