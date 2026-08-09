"""
Founder schemas.
"""

from __future__ import annotations

from uuid import UUID
from pydantic import HttpUrl
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field

from app.schemas.base import BaseSchema


class FounderBase(BaseSchema):
    """Shared Founder fields."""

    startup_id: UUID

    full_name: str = Field(
        min_length=1,
        max_length=255,
    )

    designation: str = Field(
        min_length=1,
        max_length=100,
    )

    email: EmailStr | None = None

    linkedin_url: HttpUrl | None = Field(
        default=None,
        max_length=500,
    )


class FounderCreate(FounderBase):
    """Create Founder request."""


class FounderUpdate(BaseSchema):
    """Update Founder request."""

    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    designation: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    email: EmailStr | None = None

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )


class FounderResponse(FounderBase):
    """Founder response."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID


class FounderSummary(BaseSchema):
    """Founder summary."""

    id: UUID
    full_name: str
    designation: str

    model_config = ConfigDict(
        from_attributes=True,
    )
