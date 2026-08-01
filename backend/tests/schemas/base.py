"""
Unit tests for BaseSchema.

These tests verify the common Pydantic configuration inherited by all
API schemas.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.base import BaseSchema


class SampleSchema(BaseSchema):
    """Concrete schema used for BaseSchema testing."""

    name: str
    age: int


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_create_valid_schema() -> None:
    """A valid model should be created successfully."""

    model = SampleSchema(
        name="Alice",
        age=30,
    )

    assert model.name == "Alice"
    assert model.age == 30


# ---------------------------------------------------------------------------
# Extra Fields
# ---------------------------------------------------------------------------


def test_extra_fields_are_forbidden() -> None:
    """Unknown fields should raise ValidationError."""

    with pytest.raises(ValidationError):
        SampleSchema(
            name="Alice",
            age=30,
            city="Bangalore",
        )


# ---------------------------------------------------------------------------
# Assignment Validation
# ---------------------------------------------------------------------------


def test_assignment_validation_success() -> None:
    """Valid assignment should succeed."""

    model = SampleSchema(
        name="Alice",
        age=30,
    )

    model.age = 31

    assert model.age == 31


def test_assignment_validation_failure() -> None:
    """Invalid assignment should raise ValidationError."""

    model = SampleSchema(
        name="Alice",
        age=30,
    )

    with pytest.raises(ValidationError):
        model.age = "thirty"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_model_dump() -> None:
    """model_dump() should return expected dictionary."""

    model = SampleSchema(
        name="Alice",
        age=30,
    )

    assert model.model_dump() == {
        "name": "Alice",
        "age": 30,
    }


def test_model_dump_json() -> None:
    """model_dump_json() should serialize correctly."""

    model = SampleSchema(
        name="Alice",
        age=30,
    )

    json_data = model.model_dump_json()

    assert '"name":"Alice"' in json_data
    assert '"age":30' in json_data
