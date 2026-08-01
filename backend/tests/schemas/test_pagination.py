"""
Unit tests for PaginationMeta schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.pagination import PaginationMeta

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_create_pagination_meta() -> None:
    """A valid PaginationMeta should be created successfully."""

    pagination = PaginationMeta(
        page=2,
        per_page=25,
        total_items=125,
        total_pages=5,
        has_previous=True,
        has_next=True,
    )

    assert pagination.page == 2
    assert pagination.per_page == 25
    assert pagination.total_items == 125
    assert pagination.total_pages == 5
    assert pagination.has_previous is True
    assert pagination.has_next is True


# ---------------------------------------------------------------------------
# Field Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("page", 0),
        ("page", -1),
        ("per_page", 0),
        ("per_page", -10),
        ("total_items", -1),
        ("total_pages", -1),
    ],
)
def test_numeric_constraints(field: str, value: int) -> None:
    """Numeric fields should enforce their minimum values."""

    payload = {
        "page": 1,
        "per_page": 20,
        "total_items": 100,
        "total_pages": 5,
        "has_previous": False,
        "has_next": True,
    }

    payload[field] = value

    with pytest.raises(ValidationError):
        PaginationMeta(**payload)


# ---------------------------------------------------------------------------
# Required Fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    [
        "page",
        "per_page",
        "total_items",
        "total_pages",
        "has_previous",
        "has_next",
    ],
)
def test_missing_required_fields(missing_field: str) -> None:
    """Every PaginationMeta field is required."""

    payload = {
        "page": 1,
        "per_page": 20,
        "total_items": 100,
        "total_pages": 5,
        "has_previous": False,
        "has_next": True,
    }

    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        PaginationMeta(**payload)


# ---------------------------------------------------------------------------
# Extra Fields
# ---------------------------------------------------------------------------


def test_extra_field_is_forbidden() -> None:
    """Unexpected fields should raise ValidationError."""

    with pytest.raises(ValidationError):
        PaginationMeta(
            page=1,
            per_page=20,
            total_items=100,
            total_pages=5,
            has_previous=False,
            has_next=True,
            current_offset=20,
        )


# ---------------------------------------------------------------------------
# Assignment Validation
# ---------------------------------------------------------------------------


def test_assignment_validation_success() -> None:
    """Valid assignment should succeed."""

    pagination = PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )

    pagination.page = 2

    assert pagination.page == 2


def test_assignment_validation_failure() -> None:
    """Invalid assignment should raise ValidationError."""

    pagination = PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )

    with pytest.raises(ValidationError):
        pagination.page = 0


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_model_dump() -> None:
    """model_dump() should produce the expected dictionary."""

    pagination = PaginationMeta(
        page=2,
        per_page=25,
        total_items=125,
        total_pages=5,
        has_previous=True,
        has_next=True,
    )

    assert pagination.model_dump() == {
        "page": 2,
        "per_page": 25,
        "total_items": 125,
        "total_pages": 5,
        "has_previous": True,
        "has_next": True,
    }


def test_model_dump_json() -> None:
    """model_dump_json() should serialize correctly."""

    pagination = PaginationMeta(
        page=2,
        per_page=25,
        total_items=125,
        total_pages=5,
        has_previous=True,
        has_next=True,
    )

    json_data = pagination.model_dump_json()

    assert '"page":2' in json_data
    assert '"per_page":25' in json_data
    assert '"total_items":125' in json_data
    assert '"total_pages":5' in json_data


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_pagination_objects() -> None:
    """Equivalent models should have identical dumped representation."""

    pagination1 = PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )

    pagination2 = PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )

    assert pagination1.model_dump() == pagination2.model_dump()
