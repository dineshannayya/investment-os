"""
Unit tests for ResponseFactory.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config.error_codes import ErrorCode
from app.core.response import ResponseFactory
from app.schemas.pagination import PaginationMeta

# =============================================================================
# Success
# =============================================================================


def test_success_default_response() -> None:
    """Default success response."""

    response = ResponseFactory.success()

    assert response.success is True
    assert response.message == "Request completed successfully."
    assert response.data is None
    assert response.errors == []

    assert response.meta is not None
    assert response.meta.request_id is None
    assert isinstance(response.meta.timestamp, datetime)
    assert response.meta.timestamp.tzinfo == UTC


def test_success_with_data(sample_dict) -> None:
    """Success response containing payload."""

    response = ResponseFactory.success(
        data=sample_dict,
    )

    assert response.success is True
    assert response.data == sample_dict


def test_success_custom_message() -> None:
    """Custom success message."""

    response = ResponseFactory.success(
        message="Completed.",
    )

    assert response.message == "Completed."


def test_success_request_id(request_id) -> None:
    """Request id should propagate into metadata."""

    response = ResponseFactory.success(
        request_id=request_id,
    )

    assert response.meta.request_id == request_id


# =============================================================================
# Created
# =============================================================================


def test_created_default(sample_dict) -> None:
    """Created response."""

    response = ResponseFactory.created(
        data=sample_dict,
    )

    assert response.success is True
    assert response.message == "Resource created successfully."
    assert response.data == sample_dict
    assert response.errors == []


def test_created_custom_message(sample_dict) -> None:
    """Custom created message."""

    response = ResponseFactory.created(
        data=sample_dict,
        message="Startup created.",
    )

    assert response.message == "Startup created."


def test_created_request_id(sample_dict, request_id) -> None:
    """Created response should preserve request id."""

    response = ResponseFactory.created(
        data=sample_dict,
        request_id=request_id,
    )

    assert response.meta.request_id == request_id


# =============================================================================
# Paginated
# =============================================================================


def test_paginated_response(
    sample_list,
    sample_pagination,
) -> None:
    """Paginated response."""

    response = ResponseFactory.paginated(
        data=sample_list,
        pagination=sample_pagination,
    )

    assert response.success is True
    assert response.data == sample_list
    assert response.meta.pagination == sample_pagination


def test_paginated_request_id(
    sample_list,
    sample_pagination,
    request_id,
) -> None:
    """Paginated response should include request id."""

    response = ResponseFactory.paginated(
        data=sample_list,
        pagination=sample_pagination,
        request_id=request_id,
    )

    assert response.meta.request_id == request_id


def test_paginated_custom_message(
    sample_list,
    sample_pagination,
) -> None:
    """Custom paginated message."""

    response = ResponseFactory.paginated(
        data=sample_list,
        pagination=sample_pagination,
        message="Retrieved page.",
    )

    assert response.message == "Retrieved page."


# =============================================================================
# Error
# =============================================================================


def test_error_response() -> None:
    """Standard error response."""

    response = ResponseFactory.error(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Startup not found.",
    )

    assert response.success is False
    assert response.message == "Startup not found."
    assert response.data is None

    assert len(response.errors) == 1

    error = response.errors[0]

    assert error.code == ErrorCode.RESOURCE_NOT_FOUND
    assert error.message == "Startup not found."
    assert error.field is None


def test_error_with_field() -> None:
    """Field-specific validation error."""

    response = ResponseFactory.error(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid email.",
        field="email",
    )

    assert response.errors[0].field == "email"


def test_error_request_id(request_id) -> None:
    """Error response should preserve request id."""

    response = ResponseFactory.error(
        code=ErrorCode.INTERNAL_ERROR,
        message="Unexpected error.",
        request_id=request_id,
    )

    assert response.meta.request_id == request_id


# =============================================================================
# Metadata
# =============================================================================


def test_every_response_contains_metadata(sample_dict) -> None:
    """Every factory method should create metadata."""

    responses = [
        ResponseFactory.success(),
        ResponseFactory.created(data=sample_dict),
        ResponseFactory.paginated(
            data=[],
            pagination=PaginationMeta(
                page=1,
                per_page=20,
                total_items=0,
                total_pages=0,
                has_previous=False,
                has_next=False,
            ),
        ),
        ResponseFactory.error(
            code=ErrorCode.INTERNAL_ERROR,
            message="Error",
        ),
    ]

    for response in responses:
        assert response.meta is not None
        assert isinstance(response.meta.timestamp, datetime)
