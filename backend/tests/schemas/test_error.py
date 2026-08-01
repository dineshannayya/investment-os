"""
Unit tests for ErrorDetail schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config.error_codes import ErrorCode
from app.schemas.error import ErrorDetail

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_create_error_detail() -> None:
    """A valid ErrorDetail should be created successfully."""

    error = ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid email address.",
        field="email",
    )

    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.message == "Invalid email address."
    assert error.field == "email"


def test_create_error_detail_without_field() -> None:
    """Field is optional."""

    error = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Startup not found.",
    )

    assert error.code == ErrorCode.RESOURCE_NOT_FOUND
    assert error.message == "Startup not found."
    assert error.field is None


# ---------------------------------------------------------------------------
# Required Fields
# ---------------------------------------------------------------------------


def test_missing_error_code() -> None:
    """Missing code should raise ValidationError."""

    with pytest.raises(ValidationError):
        ErrorDetail(
            message="Validation failed.",
        )


def test_missing_error_message() -> None:
    """Missing message should raise ValidationError."""

    with pytest.raises(ValidationError):
        ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
        )


# ---------------------------------------------------------------------------
# Enum Validation
# ---------------------------------------------------------------------------


def test_invalid_error_code() -> None:
    """Unknown error code should raise ValidationError."""

    with pytest.raises(ValidationError):
        ErrorDetail(
            code="invalid_error_code",
            message="Failure",
        )


# ---------------------------------------------------------------------------
# Extra Fields
# ---------------------------------------------------------------------------


def test_extra_field_is_forbidden() -> None:
    """Unexpected fields should not be accepted."""

    with pytest.raises(ValidationError):
        ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Failure",
            extra_field="unexpected",
        )


# ---------------------------------------------------------------------------
# Assignment Validation
# ---------------------------------------------------------------------------


def test_assignment_validation_success() -> None:
    """Valid assignment should succeed."""

    error = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Not found",
    )

    error.message = "Resource not found"

    assert error.message == "Resource not found"


def test_assignment_validation_failure() -> None:
    """Invalid assignment should raise ValidationError."""

    error = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Not found",
    )

    with pytest.raises(ValidationError):
        error.message = 123


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_model_dump() -> None:
    """model_dump() should produce the expected dictionary."""

    error = ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid email",
        field="email",
    )

    data = error.model_dump()

    assert data == {
        "code": ErrorCode.VALIDATION_ERROR,
        "message": "Invalid email",
        "field": "email",
    }


def test_model_dump_json() -> None:
    """model_dump_json() should serialize correctly."""

    error = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Startup not found",
    )

    json_data = error.model_dump_json()

    assert "Startup not found" in json_data
    assert "not_found" in json_data


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_error_objects() -> None:
    """Equivalent models should have identical dumped representation."""

    error1 = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Not found",
    )

    error2 = ErrorDetail(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message="Not found",
    )

    assert error1.model_dump() == error2.model_dump()
