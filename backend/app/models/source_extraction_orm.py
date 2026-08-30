"""
SQLAlchemy ORM model for persisted source extraction artifacts.

This model is the database representation of
app.models.source_extraction_record.SourceExtractionRecord.

SourceDocument remains the source-of-truth for source/file metadata.
SourceExtractionORM stores the derived extraction artifact and its
provenance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Boolean,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from app.models.base import Base

class SourceExtractionORM(Base):
    """
    Persisted extraction artifact for one exact source version.

    Idempotency identity:

        (source_id, source_sha256)

    A different SHA256 represents a different version of the source
    and therefore requires a separate extraction record.
    """

    __tablename__ = "source_extractions"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_sha256",
            name="uq_source_extractions_source_version",
        ),
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    source_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Extraction state
    # ------------------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    extraction_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    processor_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Extracted content
    # ------------------------------------------------------------------

    title: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

    segments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=list,
    )
    
    # ------------------------------------------------------------------
    # Extraction quality
    # ------------------------------------------------------------------

    quality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    quality_warnings: Mapped[list[str]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=list,
    )

    # ------------------------------------------------------------------
    # Extraction provenance
    # ------------------------------------------------------------------

    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    fallback_reason: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    extraction_config: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=dict,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )
