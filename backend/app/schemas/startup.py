"""
Startup API schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.models.enums import StartupStage, StartupStatus
from app.schemas.base import BaseSchema


# StartupCreate
class StartupCreate(BaseSchema):
    """Schema for creating a startup."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    legal_name: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    sector: str | None = Field(
        default=None,
        max_length=100,
    )

    industry: str | None = Field(
        default=None,
        max_length=100,
    )

    stage: StartupStage

    founded_year: int | None = None

    website: str | None = Field(
        default=None,
        max_length=255,
    )

    headquarters: str | None = Field(
        default=None,
        max_length=255,
    )

    status: StartupStatus = StartupStatus.ACTIVE

# StartupUpdate

class StartupUpdate(BaseSchema):
    """Schema for updating a startup."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    legal_name: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    sector: str | None = Field(
        default=None,
        max_length=100,
    )

    industry: str | None = Field(
        default=None,
        max_length=100,
    )

    stage: StartupStage | None = None

    founded_year: int | None = None

    website: str | None = None

    headquarters: str | None = None

    status: StartupStatus | None = None


# StartupResponse
class StartupResponse(BaseSchema):
    """Startup response."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    name: str

    legal_name: str | None

    description: str | None

    sector: str | None

    industry: str | None

    stage: StartupStage

    founded_year: int | None

    website: str | None

    headquarters: str | None

    status: StartupStatus

    created_at: datetime

    updated_at: datetime


# StartupSummary

class StartupSummary(BaseSchema):
    """Lightweight startup response."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    name: str

    sector: str | None

    stage: StartupStage

    status: StartupStatus


_all__ = [
    "StartupCreate",
    "StartupUpdate",
    "StartupResponse",
    "StartupSummary",
]
