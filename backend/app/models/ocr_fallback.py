from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OcrFallbackReason(str, Enum):
    """
    Reason why OCR fallback was requested.
    """

    NATIVE_EXTRACTION_EMPTY = "native_extraction_empty"
    NATIVE_EXTRACTION_SUSPICIOUSLY_SHORT = (
        "native_extraction_suspiciously_short"
    )
    FINANCIAL_PDF_TEXT_SUSPICIOUSLY_SHORT = (
        "financial_pdf_text_suspiciously_short"
    )
    NATIVE_EXTRACTION_FAILED = "native_extraction_failed"


class OcrFallbackDecision(BaseModel):
    """
    Decision describing whether OCR fallback should be attempted.
    """

    model_config = ConfigDict(extra="forbid")

    should_run: bool

    reason: OcrFallbackReason | None = None

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
