"""
OCR fallback service.

Determines whether native document extraction is insufficient and,
when required, invokes the OCR processor.

Responsibilities:
    - decide whether OCR fallback is required
    - invoke OCR processing
    - provide deterministic fallback decisions

Non-responsibilities:
    - source discovery
    - source classification
    - extraction quality scoring
    - evidence generation
    - financial interpretation
    - investment scoring
    - LLM invocation
    - final startup analysis
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.models.ocr_fallback import (
    OcrFallbackDecision,
    OcrFallbackReason,
)
from app.models.source_document import SourceDocument, SourceType
from app.processors.base import DocumentContent
from app.processors.ocr import OcrProcessor
from app.services.extraction_quality import (
    ExtractionQuality,
    ExtractionQualityReport,
)


class OcrProcessorProtocol(Protocol):
    """Protocol implemented by OCR processors."""

    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        ...


class OcrFallbackService:
    """
    Decide whether OCR is required and invoke OCR when appropriate.

    This service does not modify SourceDocument and does not mutate
    the original source file.
    """

    def __init__(
        self,
        ocr_processor: OcrProcessorProtocol | None = None,
        *,
        short_text_threshold: int = 100,
        financial_pdf_short_text_threshold: int = 500,
    ) -> None:

        if short_text_threshold < 0:
            raise ValueError(
                "short_text_threshold must be greater than or equal to zero"
            )

        if financial_pdf_short_text_threshold < 0:
            raise ValueError(
                "financial_pdf_short_text_threshold must be greater than "
                "or equal to zero"
            )

        self._ocr_processor = (
            ocr_processor
            if ocr_processor is not None
            else OcrProcessor()
        )

        self._short_text_threshold = short_text_threshold

        self._financial_pdf_short_text_threshold = (
            financial_pdf_short_text_threshold
        )

    @property
    def processor_name(self) -> str:
        """Return the configured OCR processor class name."""

        return type(self._ocr_processor).__name__

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def should_fallback(
        self,
        *,
        source: SourceDocument,
        content: DocumentContent | None,
        quality: ExtractionQualityReport,
    ) -> OcrFallbackDecision:
        """
        Determine whether OCR fallback should be attempted.

        OCR is currently applicable only to PDF sources.

        Decision order:

            1. Non-PDF source
                -> no OCR

            2. Native processor failed
                -> native_extraction_failed

            3. Native extraction returned empty/blank text
                -> native_extraction_empty

            4. Financial PDF has suspiciously short text
                -> financial_pdf_text_suspiciously_short

            5. Other PDF has suspiciously short text
                -> native_extraction_suspiciously_short

            6. Otherwise
                -> no fallback

        Important distinction:

            content is None
                means the native processor itself failed.

            content exists but text is empty
                means native extraction completed but produced
                no usable text.

        This distinction is important for fallback provenance.
        """

        # --------------------------------------------------------------
        # 1. OCR currently applies only to PDFs.
        # --------------------------------------------------------------

        if source.source_type != SourceType.PDF:
            return OcrFallbackDecision(
                should_run=False,
            )

        # --------------------------------------------------------------
        # 2. Native processor actually failed.
        #
        # This is the ONLY case that should produce:
        #
        #     native_extraction_failed
        # --------------------------------------------------------------

        if content is None:
            return OcrFallbackDecision(
                should_run=True,
                reason=OcrFallbackReason.NATIVE_EXTRACTION_FAILED,
                confidence=1.0,
            )

        # --------------------------------------------------------------
        # 3. Native processor succeeded but returned empty/blank text.
        #
        # Check content itself before generic FAIL quality.
        #
        # PAN.pdf reaches this branch:
        #
        #     content != None
        #     content.text == ""
        #     quality == FAIL
        #
        # Therefore the correct reason is:
        #
        #     native_extraction_empty
        # --------------------------------------------------------------

        text = content.text or ""

        if not text.strip():
            return OcrFallbackDecision(
                should_run=True,
                reason=OcrFallbackReason.NATIVE_EXTRACTION_EMPTY,
                confidence=1.0,
            )

        # --------------------------------------------------------------
        # 4. Financial PDF suspiciously short.
        #
        # This check must happen before the generic short-text rule
        # because financial PDFs use a higher threshold.
        # --------------------------------------------------------------

        if self._is_financial_pdf(source):

            if (
                quality.text_length
                < self._financial_pdf_short_text_threshold
            ):
                return OcrFallbackDecision(
                    should_run=True,
                    reason=(
                        OcrFallbackReason
                        .FINANCIAL_PDF_TEXT_SUSPICIOUSLY_SHORT
                    ),
                    confidence=0.95,
                )

        # --------------------------------------------------------------
        # 5. Other PDF suspiciously short.
        # --------------------------------------------------------------

        if quality.text_length < self._short_text_threshold:
            return OcrFallbackDecision(
                should_run=True,
                reason=(
                    OcrFallbackReason
                    .NATIVE_EXTRACTION_SUSPICIOUSLY_SHORT
                ),
                confidence=0.90,
            )

        # --------------------------------------------------------------
        # 6. Native extraction is sufficiently populated.
        # --------------------------------------------------------------

        return OcrFallbackDecision(
            should_run=False,
        )

    # ------------------------------------------------------------------
    # OCR execution
    # ------------------------------------------------------------------

    def extract(
        self,
        *,
        source: SourceDocument,
        path: Path,
    ) -> DocumentContent:
        """
        Execute OCR for a source document.

        OCR execution is deliberately separate from the fallback
        decision so callers can explicitly control when OCR runs.
        """

        if source.source_type != SourceType.PDF:
            raise ValueError(
                "OCR fallback currently supports PDF sources only: "
                f"{source.relative_path}"
            )

        return self._ocr_processor.process(
            source.source_id,
            path,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_financial_pdf(
        source: SourceDocument,
    ) -> bool:
        """
        Return True when the source is a financial PDF.
        """

        return (
            source.source_type == SourceType.PDF
            and source.source_category.value == "financial"
        )
