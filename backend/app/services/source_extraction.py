"""
Source extraction service.

Native-first document extraction with deterministic OCR fallback.

Responsibilities:
    - validate source extraction eligibility
    - resolve source paths safely
    - resolve the native processor
    - perform native extraction
    - assess native extraction quality
    - decide whether OCR fallback is required
    - execute OCR when required
    - annotate OCR fallback provenance
    - assess OCR extraction quality
    - deterministically select the final DocumentContent

Non-responsibilities:
    - source discovery
    - source classification
    - evidence generation
    - financial interpretation
    - investment scoring
    - LLM invocation
    - persistence
"""

from __future__ import annotations

from pathlib import Path

from app.models.source_document import (
    ExtractionStatus,
    SourceDocument,
)
from app.models.source_extraction import SourceExtractionResult
from app.processors.base import DocumentContent
from app.processors.factory import create_processor_factory
from app.services.extraction_quality import (
    ExtractionQuality,
    ExtractionQualityReport,
    ExtractionQualityService,
)
from app.services.ocr_fallback import (
    OcrFallbackDecision,
    OcrFallbackService,
)


class SourceExtractionError(RuntimeError):
    """Raised when source extraction cannot be completed."""


class SourceExtractionService:
    """
    Native-first source extraction service.

    Flow:

        SourceDocument
            |
            v
        Native Processor
            |
            v
        Native DocumentContent
            |
            v
        ExtractionQualityService
            |
            v
        OcrFallbackService
            |
        +---+---+
        |       |
       NO      YES
        |       |
        v       v
      Native   OCR
                |
                v
          OCR quality
                |
                v
          final selection

    Public contract:

        extract(...) -> DocumentContent
    """

    def __init__(
        self,
        processor_factory=None,
        quality_service: ExtractionQualityService | None = None,
        ocr_fallback_service: OcrFallbackService | None = None,
    ) -> None:

        self._processor_factory = (
            processor_factory
            or create_processor_factory()
        )

        self._quality_service = (
            quality_service
            or ExtractionQualityService()
        )

        self._ocr_fallback_service = (
            ocr_fallback_service
            or OcrFallbackService()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> DocumentContent:
        """
        Extract a source using native extraction followed by
        optional OCR fallback.

        Important semantic distinction:

            Native processor raises exception
                -> native_extraction_failed

            Native processor succeeds but produces empty text
                -> native_extraction_empty

            Native processor succeeds but produces suspicious text
                -> corresponding suspicious extraction reason

        Returns:
            Final DocumentContent.

        Raises:
            SourceExtractionError:
                If no usable extraction can be produced.
        """

        self._validate_source_status(source)

        path = self._resolve_source_path(
            source=source,
            source_root=source_root,
        )

        processor = self._resolve_processor(
            source=source,
            path=path,
        )

        # --------------------------------------------------------------
        # 1. Native extraction
        # --------------------------------------------------------------

        native_content: DocumentContent | None = None
        native_error: Exception | None = None

        try:
            native_content = processor.process(
                source.source_id,
                path,
            )
        except Exception as exc:
            native_error = exc

        # --------------------------------------------------------------
        # 2. Native quality assessment
        #
        # IMPORTANT:
        #
        # If the processor successfully returns DocumentContent,
        # ALWAYS assess that content -- even if the text is empty.
        #
        # This preserves:
        #
        #     extracted_text_empty
        #
        # instead of incorrectly converting it into:
        #
        #     native_extraction_failed
        # --------------------------------------------------------------

        native_quality: ExtractionQualityReport | None = None

        if native_content is not None:

            native_quality = self._quality_service.assess(
                source=source,
                content=native_content,
                processor_name=type(processor).__name__,
            )

        else:

            # Native processor actually raised an exception.
            native_quality = self._failed_quality_report(
                source=source,
            )

        # --------------------------------------------------------------
        # 3. OCR fallback decision
        # --------------------------------------------------------------

        fallback_decision = (
            self._ocr_fallback_service.should_fallback(
                source=source,
                content=native_content,
                quality=native_quality,
            )
        )

        # --------------------------------------------------------------
        # 4. Native extraction is good enough
        # --------------------------------------------------------------

        if not fallback_decision.should_run:

            if native_content is None:
                raise SourceExtractionError(
                    self._native_failure_message(
                        source=source,
                        native_error=native_error,
                    )
                )

            return self._annotate_native_content(
                native_content,
            )

        # --------------------------------------------------------------
        # 5. OCR fallback
        # --------------------------------------------------------------

        try:

            ocr_content = self._ocr_fallback_service.extract(
                source=source,
                path=path,
            )

        except Exception as ocr_error:

            # If native extraction contains usable information,
            # retain it rather than failing the entire source.
            if (
                native_content is not None
                and self._is_usable_quality(native_quality)
            ):
                return self._annotate_native_content(
                    native_content,
                )

            raise SourceExtractionError(
                self._ocr_failure_message(
                    source=source,
                    native_error=native_error,
                    ocr_error=ocr_error,
                )
            ) from ocr_error

        # --------------------------------------------------------------
        # 6. Annotate OCR fallback provenance
        # --------------------------------------------------------------

        self._annotate_ocr_fallback(
            content=ocr_content,
            fallback_decision=fallback_decision,
        )

        # --------------------------------------------------------------
        # 7. Assess OCR quality
        # --------------------------------------------------------------

        ocr_quality = self._quality_service.assess(
            source=source,
            content=ocr_content,
            processor_name=self._ocr_fallback_service.processor_name,
        )

        # --------------------------------------------------------------
        # 8. Select final content
        # --------------------------------------------------------------

        return self._select_final_content(
            native_content=native_content,
            native_quality=native_quality,
            ocr_content=ocr_content,
            ocr_quality=ocr_quality,
        )

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    @staticmethod
    def _annotate_native_content(
        content: DocumentContent,
    ) -> DocumentContent:
        """
        Annotate a result returned through the native path.
        """

        content.metadata["fallback_used"] = False

        # Remove stale fallback reason if a mutable DocumentContent
        # instance is reused by a processor/test.
        content.metadata.pop(
            "fallback_reason",
            None,
        )

        return content

    @staticmethod
    def _annotate_ocr_fallback(
        *,
        content: DocumentContent,
        fallback_decision: OcrFallbackDecision,
    ) -> DocumentContent:
        """
        Annotate OCR result with fallback provenance.

        OcrProcessor itself does not need to know why it was invoked.
        SourceExtractionService owns this provenance.
        """

        content.metadata["fallback_used"] = True

        reason = getattr(
            fallback_decision,
            "reason",
            None,
        )

        if reason is not None:

            content.metadata["fallback_reason"] = (
                reason.value
                if hasattr(reason, "value")
                else str(reason)
            )

        return content

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_source_status(
        source: SourceDocument,
    ) -> None:
        """
        Validate that the source is eligible for extraction.
        """

        if source.extraction_status not in (
            ExtractionStatus.DISCOVERED,
            ExtractionStatus.FAILED,
        ):
            raise SourceExtractionError(
                "Source is not eligible for extraction: "
                f"{source.relative_path}; "
                f"status={source.extraction_status.value}"
            )

    # ------------------------------------------------------------------
    # Path handling
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_source_path(
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> Path:
        """
        Resolve source path safely.

        Prevents relative_path from escaping source_root.
        """

        root = source_root.resolve()

        path = (
            root / source.relative_path
        ).resolve()

        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SourceExtractionError(
                "Source path escapes source root: "
                f"{source.relative_path}"
            ) from exc

        if not path.exists():
            raise SourceExtractionError(
                f"Source file does not exist: {path}"
            )

        if not path.is_file():
            raise SourceExtractionError(
                f"Source path is not a file: {path}"
            )

        return path

    # ------------------------------------------------------------------
    # Processor resolution
    # ------------------------------------------------------------------

    def _resolve_processor(
        self,
        *,
        source: SourceDocument,
        path: Path,
    ):
        """
        Resolve the native processor through ProcessorFactory.
        """

        try:

            processor = self._processor_factory.get_processor(
                path,
                source.mime_type,
            )

        except Exception as exc:

            raise SourceExtractionError(
                "Failed to resolve processor for source "
                f"{source.relative_path}: {exc}"
            ) from exc

        if processor is None:

            raise SourceExtractionError(
                "No processor available for source: "
                f"{source.relative_path}"
            )

        return processor

    # ------------------------------------------------------------------
    # Quality helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _failed_quality_report(
        *,
        source: SourceDocument,
    ) -> ExtractionQualityReport:
        """
        Construct a quality report only when the native processor
        actually failed with an exception.
        """

        return ExtractionQualityReport(
            source_id=str(source.source_id),
            relative_path=source.relative_path,
            source_type=source.source_type.value,
            source_category=source.source_category.value,
            quality=ExtractionQuality.FAIL,
            text_length=0,
            segment_count=0,
            processor_name=None,
            warnings=[
                "native_extraction_failed",
            ],
        )

    @staticmethod
    def _is_usable_quality(
        quality: ExtractionQualityReport | None,
    ) -> bool:
        """
        Determine whether an extraction contains usable content.

        REVIEW is considered usable because content exists but has
        a quality concern.
        """

        if quality is None:
            return False

        if quality.text_length <= 0:
            return False

        return quality.quality in (
            ExtractionQuality.PASS,
            ExtractionQuality.REVIEW,
        )

    # ------------------------------------------------------------------
    # Final selection
    # ------------------------------------------------------------------

    @classmethod
    def _select_final_content(
        cls,
        *,
        native_content: DocumentContent | None,
        native_quality: ExtractionQualityReport | None,
        ocr_content: DocumentContent,
        ocr_quality: ExtractionQualityReport,
    ) -> DocumentContent:
        """
        Deterministically select the final extraction.

        Rules:

            Native PASS
                -> native

            Native REVIEW + OCR PASS
                -> OCR

            Native REVIEW + OCR REVIEW
                -> result with more text

            Native FAIL/empty + usable OCR
                -> OCR

            OCR FAIL + usable native
                -> native

            Both unusable
                -> error
        """

        ocr_usable = cls._is_usable_quality(
            ocr_quality,
        )

        native_usable = cls._is_usable_quality(
            native_quality,
        )

        # --------------------------------------------------------------
        # OCR is unusable
        # --------------------------------------------------------------

        if not ocr_usable:

            if (
                native_usable
                and native_content is not None
            ):
                return cls._annotate_native_content(
                    native_content,
                )

            raise SourceExtractionError(
                "Both native and OCR extraction results "
                "are unusable."
            )

        # --------------------------------------------------------------
        # Native is unavailable/unusable
        # --------------------------------------------------------------

        if (
            not native_usable
            or native_content is None
        ):
            return ocr_content

        # --------------------------------------------------------------
        # OCR PASS beats native REVIEW
        # --------------------------------------------------------------

        if (
            ocr_quality.quality
            == ExtractionQuality.PASS
            and native_quality is not None
            and native_quality.quality
            == ExtractionQuality.REVIEW
        ):
            return ocr_content

        # --------------------------------------------------------------
        # Native PASS
        # --------------------------------------------------------------

        if (
            native_quality is not None
            and native_quality.quality
            == ExtractionQuality.PASS
        ):
            return cls._annotate_native_content(
                native_content,
            )

        # --------------------------------------------------------------
        # Both REVIEW
        # --------------------------------------------------------------

        if (
            native_quality is not None
            and native_quality.quality
            == ExtractionQuality.REVIEW
            and ocr_quality.quality
            == ExtractionQuality.REVIEW
        ):

            if (
                ocr_quality.text_length
                > native_quality.text_length
            ):
                return ocr_content

            return cls._annotate_native_content(
                native_content,
            )

        # --------------------------------------------------------------
        # Defensive fallback
        # --------------------------------------------------------------

        return ocr_content

    # ------------------------------------------------------------------
    # Error messages
    # ------------------------------------------------------------------

    @staticmethod
    def _native_failure_message(
        *,
        source: SourceDocument,
        native_error: Exception | None,
    ) -> str:
        """
        Format native extraction failure.
        """

        if native_error is None:

            return (
                "Native extraction produced no content for "
                f"{source.relative_path}"
            )

        return (
            "Native extraction failed for "
            f"{source.relative_path}: {native_error}"
        )

    @staticmethod
    def _ocr_failure_message(
        *,
        source: SourceDocument,
        native_error: Exception | None,
        ocr_error: Exception,
    ) -> str:
        """
        Format combined native/OCR failure.
        """

        native_message = (
            str(native_error)
            if native_error is not None
            else "native extraction produced unusable content"
        )

        return (
            f"Source extraction failed for "
            f"{source.relative_path}; "
            f"native={native_message}; "
            f"ocr={ocr_error}"
        )
