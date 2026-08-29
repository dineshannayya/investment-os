"""
Source extraction result models.

These models describe the deterministic result of processing one
discovered source.

They do not contain investment interpretation or LLM output.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.source_document import (
    ExtractionStatus,
    SourceDocument,
)


class SourceExtractionResult(BaseModel):
    """
    Result of extracting one SourceDocument.
    """

    model_config = ConfigDict(extra="forbid")

    source: SourceDocument

    content: object | None = None

    status: ExtractionStatus

    processor_name: str | None = None

    error: str | None = None
