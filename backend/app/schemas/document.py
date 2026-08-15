"""
Document schemas.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field

from app.models.enums import (
    DocumentStatus,
    DocumentType,
)
from app.schemas.base import BaseSchema


class DocumentBase(BaseSchema):
    """Shared document fields."""

    startup_id: UUID

    document_type: DocumentType

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    filename: str = Field(
        min_length=1,
        max_length=255,
    )

    original_filename: str = Field(
        min_length=1,
        max_length=255,
    )

    mime_type: str = Field(
        min_length=1,
        max_length=100,
    )

    file_size: int = Field(
        ge=0,
    )

    file_hash: str = Field(
        min_length=1,
        max_length=128,
    )

    storage_path: str = Field(
        min_length=1,
        max_length=1024,
    )


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""


class DocumentUpdate(BaseSchema):
    """Schema for updating a document."""

    document_type: DocumentType | None = None

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    original_filename: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    mime_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    file_size: int | None = Field(
        default=None,
        ge=0,
    )

    file_hash: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )

    storage_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=1024,
    )

    status: DocumentStatus | None = None

    version: int | None = Field(
        default=None,
        ge=1,
    )


class DocumentSummary(BaseSchema):
    """Lightweight document representation."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    document_type: DocumentType

    title: str

    status: DocumentStatus

    version: int


class DocumentResponse(DocumentBase):
    """Document response."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    status: DocumentStatus

    version: int
