"""
Persistent source extraction record.

This model represents a persisted extraction artifact generated from
one exact version of a SourceDocument.

SourceDocument owns:
    - source identity
    - source location
    - source classification
    - source authority
    - source file identity

SourceExtractionRecord owns:
    - extracted content
    - extraction provenance
    - extraction quality
    - OCR fallback provenance
    - extraction configuration
    - extraction timestamps

It does NOT contain:
    - investment interpretation
    - financial analysis
    - investment risks
    - scores
    - LLM output
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.extraction_quality import ExtractionQuality
from app.models.source_document import ExtractionStatus


class ExtractionMethod(str, Enum):
    """
    Method used to generate the extraction artifact.
    """

    NATIVE = "native"
    OCR = "ocr"


class ExtractionProvenance(BaseModel):
    """
    Provenance describing how an extraction was generated.
    """

    model_config = ConfigDict(extra="forbid")

    method: ExtractionMethod

    processor_name: str = Field(
        min_length=1,
    )

    fallback_used: bool = False

    fallback_reason: str | None = None

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )


class SourceExtractionRecord(BaseModel):
    """
    Persisted extraction artifact for one exact source version.

    The source file itself remains the source of truth.

    The persisted extraction is a derived artifact identified by:

        source_id + source_sha256
    """

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    extraction_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this extraction record.",
    )

    source_id: UUID = Field(
        description="SourceDocument identifier.",
    )

    source_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
        description=(
            "SHA256 of the exact source bytes used for this extraction."
        ),
    )

    # ------------------------------------------------------------------
    # Extraction state
    # ------------------------------------------------------------------

    status: ExtractionStatus = Field(
        description="Status of this extraction operation.",
    )

    # ------------------------------------------------------------------
    # Extracted content
    # ------------------------------------------------------------------

    title: str | None = None

    page_count: int | None = Field(
        default=None,
        ge=0,
    )

    text: str = ""

    segments: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    # ------------------------------------------------------------------
    # Extraction quality
    # ------------------------------------------------------------------

    quality: ExtractionQuality

    quality_warnings: list[str] = Field(
        default_factory=list,
    )

    # ------------------------------------------------------------------
    # Extraction provenance
    # ------------------------------------------------------------------

    provenance: ExtractionProvenance

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: datetime

    updated_at: datetime
