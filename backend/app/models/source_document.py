"""
Source document model.

Represents a source file discovered for a startup.

This model describes:
    - source identity
    - source location
    - source classification
    - extraction state
    - provenance metadata

It intentionally does NOT contain:
    - extracted investment facts
    - financial metrics
    - investment risks
    - investment dimensions
    - scores
    - LLM output

Those concerns belong to downstream layers.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """
    Physical/source document format.
    """

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    HTML = "html"
    TXT = "txt"
    OTHER = "other"


class SourceCategory(str, Enum):
    """
    Broad business meaning/category of a source.

    This is classification metadata, not a statement about
    the truth of the information contained in the source.
    """

    BUSINESS = "business"
    COMPANY_DOCUMENT = "company_document"
    FINANCIAL = "financial"
    LEGAL = "legal"
    WEB = "web"
    OTHER = "other"


class SourceAuthority(str, Enum):
    """
    Authority/provenance classification of the source.

    Authority describes where the source originates and how it
    should generally be treated during later reconciliation.

    It does NOT mean that every claim in the source is true.
    """

    UNKNOWN = "unknown"

    COMPANY_PROVIDED = "company_provided"
    FOUNDER_PROVIDED = "founder_provided"

    AUDITED_FINANCIAL = "audited_financial"
    PROVISIONAL_FINANCIAL = "provisional_financial"
    MANAGEMENT_REPORT = "management_report"
    MANAGEMENT_PROJECTION = "management_projection"

    LEGAL_AGREEMENT = "legal_agreement"
    CORPORATE_REGISTRATION = "corporate_registration"

    PLATFORM_PUBLISHED = "platform_published"
    THIRD_PARTY = "third_party"


class ExtractionStatus(str, Enum):
    """
    Current processing state of a source document.
    """

    DISCOVERED = "discovered"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class SourceDocument(BaseModel):
    """
    Metadata and provenance record for one startup source.

    SourceDocument is deliberately separate from DocumentContent.

    SourceDocument answers:
        "What source do we have?"

    DocumentContent answers:
        "What did the processor extract from that source?"
    """

    model_config = ConfigDict(extra="forbid")

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    source_id: UUID = Field(
        description="Stable identifier for the discovered source record."
    )

    startup_id: str = Field(
        min_length=1,
        description="Startup identifier owning this source."
    )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    relative_path: str = Field(
        min_length=1,
        description="Path relative to the startup source root."
    )

    filename: str = Field(
        min_length=1,
        description="Original source filename."
    )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    source_type: SourceType

    source_category: SourceCategory = SourceCategory.OTHER

    source_authority: SourceAuthority = SourceAuthority.UNKNOWN

    # ------------------------------------------------------------------
    # Basic metadata
    # ------------------------------------------------------------------

    mime_type: str | None = None

    title: str | None = None

    document_date: date | None = None

    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
    )

    # ------------------------------------------------------------------
    # File identity / change detection
    # ------------------------------------------------------------------

    sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )

    # ------------------------------------------------------------------
    # Extraction state
    # ------------------------------------------------------------------

    extraction_status: ExtractionStatus = (
        ExtractionStatus.DISCOVERED
    )

    processor_name: str | None = None

    error: str | None = None
