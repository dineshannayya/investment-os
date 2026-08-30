"""
Source extraction orchestrator.

Coordinates the production source-extraction flow.

Normal extraction:

    SourceDocument
        |
        v
    persisted extraction lookup
        |
        +---- found ----> return persisted record
        |
        +---- not found
                  |
                  v
          SourceExtractionService
                  |
                  v
          DocumentContent
                  |
                  v
          SourceExtractionRecord
                  |
                  v
      SourceExtractionPersistenceService
                  |
                  v
              database


Refresh extraction:

    SourceDocument
        |
        v
    SourceExtractionService
        |
        v
    DocumentContent
        |
        v
    SourceExtractionRecord
        |
        v
    SourceExtractionPersistenceService.refresh()
        |
        +---- existing -> update
        |
        +---- missing  -> create


Responsibilities:
    - Validate source identity required for persistence.
    - Check the extraction cache for normal extraction.
    - Invoke SourceExtractionService.
    - Convert DocumentContent into SourceExtractionRecord.
    - Persist new extraction results.
    - Explicitly refresh an existing extraction.
    - Preserve extraction provenance.

Non-responsibilities:
    - Source discovery.
    - File hashing.
    - Native extraction implementation.
    - OCR implementation.
    - OCR fallback decisions.
    - Financial interpretation.
    - LLM invocation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.source_document import (
    ExtractionStatus,
    SourceDocument,
)
from app.models.source_extraction_record import (
    ExtractionMethod,
    ExtractionProvenance,
    SourceExtractionRecord,
)
from app.processors.base import (
    DocumentContent,
    DocumentSegment,
)
from app.services.extraction_quality import (
    ExtractionQualityService,
)
from app.services.source_extraction import (
    SourceExtractionError,
    SourceExtractionService,
)
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)


class SourceExtractionOrchestrationError(RuntimeError):
    """Raised when the complete source extraction flow cannot complete."""


class SourceExtractionOutcome(str, Enum):
    """Outcome of a normal cache-aware extraction request."""

    CACHE_HIT = "cache_hit"
    EXTRACTED = "extracted"


@dataclass(slots=True, frozen=True)
class SourceExtractionResult:
    """Execution result for a normal source extraction request."""

    record: SourceExtractionRecord
    outcome: SourceExtractionOutcome

    @property
    def cached(self) -> bool:
        """Return True when the persistent extraction cache was used."""

        return self.outcome is SourceExtractionOutcome.CACHE_HIT

    @property
    def extracted(self) -> bool:
        """Return True when extraction was executed during this request."""

        return self.outcome is SourceExtractionOutcome.EXTRACTED

    def __getattr__(self, name: str) -> Any:
        """Delegate record attributes for backward-compatible callers."""

        return getattr(self.record, name)


class SourceExtractionOrchestrator:
    """
    Production orchestration boundary for source extraction.

    The orchestrator adds persistence and cache behavior around
    SourceExtractionService without making the extraction service
    database-aware.

    Public operations:

        extract()
            Normal cache-aware extraction.

        refresh()
            Explicit re-extraction that bypasses the cache.
    """

    def __init__(
        self,
        *,
        session: Session,
        extraction_service: SourceExtractionService | None = None,
        persistence_service: (
            SourceExtractionPersistenceService | None
        ) = None,
        quality_service: ExtractionQualityService | None = None,
    ) -> None:
        self._session = session

        self._extraction_service = (
            extraction_service
            or SourceExtractionService()
        )

        self._persistence_service = (
            persistence_service
            or SourceExtractionPersistenceService(
                session=session,
            )
        )

        self._quality_service = (
            quality_service
            or ExtractionQualityService()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_text(
        value: str | None,
    ) -> str | None:
        """
        Sanitize text before it enters the persistence boundary.

        PostgreSQL text/jsonb values cannot contain NUL (0x00)
        characters. Some PDF metadata and OCR pipelines can
        produce embedded NUL bytes.

        Preserve all other content exactly.
        """

        if value is None:
            return None

        return value.replace("\x00", "")


    def extract(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> SourceExtractionRecord:
        """Extract and persist a source using the normal cache-aware flow.

        This compatibility API returns only the persistent record.
        Call :meth:`extract_with_result` when the caller also needs to
        distinguish a cache hit from a newly executed extraction.
        """

        return self.extract_with_result(
            source=source,
            source_root=source_root,
        ).record

    def extract_with_result(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> SourceExtractionResult:
        """Run normal cache-aware extraction with an explicit outcome.

        The persistent extraction record intentionally does not contain
        request-level cache state. That state belongs to this execution
        result and is therefore safe for production batch accounting.
        """

        self._validate_source(source)

        assert source.sha256 is not None

        existing = self._persistence_service.get_by_source_version(
            source_id=source.source_id,
            source_sha256=source.sha256,
        )

        if existing is not None:
            print(
                "[EXTRACT] CACHE_HIT "
                f"file={source.filename} "
                f"source_id={source.source_id} "
                f"sha256={source.sha256[:12]}...",
                flush=True,
            )

            return SourceExtractionResult(
                record=existing,
                outcome=SourceExtractionOutcome.CACHE_HIT,
            )

        print(
            "[EXTRACT] CACHE_MISS "
            f"file={source.filename} "
            f"source_id={source.source_id} "
            f"sha256={source.sha256[:12]}...",
            flush=True,
        )

        record = self._execute_extraction(
            source=source,
            source_root=source_root,
        )

        persisted = self._persistence_service.persist(record)

        return SourceExtractionResult(
            record=persisted,
            outcome=SourceExtractionOutcome.EXTRACTED,
        )

    # ------------------------------------------------------------------
    # Explicit refresh
    # ------------------------------------------------------------------

    def refresh(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> SourceExtractionRecord:
        """
        Explicitly re-extract and refresh a source version.

        Unlike extract(), this method intentionally bypasses the
        persisted extraction cache.

        Behavior:

            1. Validate source SHA256.
            2. Execute extraction unconditionally.
            3. Build a fresh SourceExtractionRecord.
            4. Refresh the persisted source-version record.
            5. Return the refreshed record.

        The source version remains:

            source.source_id + source.sha256

        If an existing record is present, the persistence layer
        preserves its extraction ID and original creation timestamp.

        The updated timestamp is refreshed.
        """

        self._validate_source(source)

        assert source.sha256 is not None

        print(
            "[EXTRACT] REFRESH "
            f"file={source.filename} "
            f"source_id={source.source_id} "
            f"sha256={source.sha256[:12]}...",
            flush=True,
        )

        # --------------------------------------------------------------
        # 1. Always execute extraction.
        #
        # There is deliberately NO cache lookup here.
        # --------------------------------------------------------------

        record = self._execute_extraction(
            source=source,
            source_root=source_root,
        )

        # --------------------------------------------------------------
        # 2. Refresh persistence.
        #
        # Existing record:
        #     update
        #
        # Missing record:
        #     create
        # --------------------------------------------------------------

        return self._persistence_service.refresh(record)

    # ------------------------------------------------------------------
    # Shared extraction pipeline
    # ------------------------------------------------------------------

    def _execute_extraction(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> SourceExtractionRecord:
        """
        Execute the actual extraction pipeline.

        This method contains no cache logic.

        Both extract() and refresh() use this exact pipeline so
        that refresh cannot accidentally diverge from normal
        extraction.

        Pipeline:

            SourceExtractionService
                |
                v
            DocumentContent
                |
                v
            SourceExtractionRecord
        """

        try:
            content = self._extraction_service.extract(
                source=source,
                source_root=source_root,
            )

        except SourceExtractionError:
            # Preserve the original domain extraction exception.
            raise

        except Exception as exc:
            raise SourceExtractionOrchestrationError(
                "Source extraction failed: "
                f"{source.relative_path}"
            ) from exc

        return self._build_record(
            source=source,
            content=content,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_source(
        source: SourceDocument,
    ) -> None:
        """
        Validate information required for persistent extraction.

        SourceDocument.sha256 is optional at the model level because
        discovery metadata may be incomplete.

        Persistent extraction, however, requires the exact source
        file SHA256.
        """

        if not source.sha256:
            raise SourceExtractionOrchestrationError(
                "Source SHA256 is required for persistent extraction: "
                f"{source.relative_path}"
            )

        if len(source.sha256) != 64:
            raise SourceExtractionOrchestrationError(
                "Invalid source SHA256 length: "
                f"{source.relative_path}"
            )

        if any(
            character not in "0123456789abcdefABCDEF"
            for character in source.sha256
        ):
            raise SourceExtractionOrchestrationError(
                "Invalid source SHA256 value: "
                f"{source.relative_path}"
            )

    # ------------------------------------------------------------------
    # Record construction
    # ------------------------------------------------------------------

    def _build_record(
        self,
        *,
        source: SourceDocument,
        content: DocumentContent,
    ) -> SourceExtractionRecord:
        """
        Convert final DocumentContent into SourceExtractionRecord.

        SourceDocument supplies:

            - source_id
            - source SHA256

        DocumentContent supplies:

            - title
            - page count
            - text
            - segments
            - extraction metadata

        The extraction processor remains the source of truth for
        extraction provenance.
        """

        assert source.sha256 is not None

        metadata = dict(content.metadata or {})

        # --------------------------------------------------------------
        # Extraction method
        # --------------------------------------------------------------

        method = self._resolve_method(metadata)

        # --------------------------------------------------------------
        # Processor
        # --------------------------------------------------------------

        processor_name = self._resolve_processor_name(
            metadata=metadata,
            method=method,
        )

        # --------------------------------------------------------------
        # Fallback provenance
        # --------------------------------------------------------------

        fallback_used = bool(
            metadata.get("fallback_used", False)
        )

        fallback_reason = metadata.get(
            "fallback_reason",
        )

        if fallback_reason is not None:
            fallback_reason = str(fallback_reason)

        # --------------------------------------------------------------
        # Quality
        #
        # SourceExtractionService performs extraction and fallback.
        # The final DocumentContent is assessed here for the
        # persistence-quality contract.
        # --------------------------------------------------------------

        quality_report = self._quality_service.assess(
            source=source,
            content=content,
            processor_name=processor_name,
        )

        # --------------------------------------------------------------
        # Extraction configuration / provenance
        # --------------------------------------------------------------

        configuration = self._extract_configuration(
            metadata,
        )

        provenance = ExtractionProvenance(
            method=method,
            processor_name=processor_name,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            configuration=configuration,
        )

        # --------------------------------------------------------------
        # Timestamps
        # --------------------------------------------------------------

        now = datetime.now(timezone.utc)

        # --------------------------------------------------------------
        # Extraction identity
        # --------------------------------------------------------------

        extraction_id = uuid4()

        # --------------------------------------------------------------
        # Domain persistence record
        # --------------------------------------------------------------

        return SourceExtractionRecord(
            extraction_id=extraction_id,
            source_id=source.source_id,
            source_sha256=source.sha256,
            status=ExtractionStatus.EXTRACTED,
            title=self._sanitize_text(content.title),
            page_count=content.page_count,
            text=self._sanitize_text(content.text) or "",
            segments=self._normalize_segments(
                content.segments,
            ),
            quality=quality_report.quality,
            quality_warnings=quality_report.warnings,
            provenance=provenance,
            created_at=now,
            updated_at=now,
        )


    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_method(
        metadata: dict[str, Any],
    ) -> ExtractionMethod:
        """
        Determine the final extraction method.

        Resolution order:

            1. Explicit extraction_method.
            2. OCR engine metadata.
            3. fallback_used.
            4. Native extraction.

        OCR fallback processors report extraction_method='ocr',
        so the explicit metadata normally determines the result.
        """

        extraction_method = metadata.get(
            "extraction_method",
        )

        if extraction_method:
            try:
                return ExtractionMethod(
                    str(extraction_method).lower(),
                )
            except ValueError:
                # Unknown metadata should not make the extraction
                # record unusable. Continue with deterministic
                # fallback resolution below.
                pass

        if metadata.get("ocr_engine"):
            return ExtractionMethod.OCR

        if metadata.get("fallback_used"):
            return ExtractionMethod.OCR

        return ExtractionMethod.NATIVE

    @staticmethod
    def _resolve_processor_name(
        *,
        metadata: dict[str, Any],
        method: ExtractionMethod,
    ) -> str:
        """
        Resolve the processor responsible for the final artifact.

        Resolution order:

            1. processor_name
            2. processor
            3. OCR engine for OCR extraction
            4. OcrProcessor
            5. SourceExtractionService
        """

        processor_name = metadata.get(
            "processor_name",
        )

        if processor_name:
            return str(processor_name)

        processor_name = metadata.get(
            "processor",
        )

        if processor_name:
            return str(processor_name)

        if method == ExtractionMethod.OCR:
            ocr_engine = metadata.get(
                "ocr_engine",
            )

            if ocr_engine:
                return str(ocr_engine)

            return "OcrProcessor"

        return "SourceExtractionService"

    @staticmethod
    def _extract_configuration(
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract processor-reported execution configuration.

        The processor is the source of truth for execution parameters.

        The orchestrator only persists metadata that the processor
        reports. It does not independently define OCR settings.

        An explicit extraction_config dictionary is preserved first,
        then known provenance fields are overlaid when present.
        """

        configuration: dict[str, Any] = {}

        # --------------------------------------------------------------
        # Explicit processor configuration
        # --------------------------------------------------------------

        explicit = metadata.get(
            "extraction_config",
        )

        if isinstance(explicit, dict):
            configuration.update(explicit)

        # --------------------------------------------------------------
        # Standard provenance fields
        # --------------------------------------------------------------

        provenance_fields = (
            "extraction_method",
            "ocr_engine",
            "ocr_language",
            "ocr_dpi",
            "ocr_workers",
            "ocr_timeout_seconds",
        )

        for field in provenance_fields:
            value = metadata.get(field)

            if value is not None:
                configuration[field] = value

        return configuration

    # ------------------------------------------------------------------
    # Segment normalization
    # ------------------------------------------------------------------

    def _normalize_segments(
        self,
        segments: tuple[DocumentSegment, ...],
    ) -> list[dict[str, Any]]:
        """
        Convert DocumentSegment objects into JSONB-compatible
        dictionaries.

        DocumentSegment is the processor-layer representation.

        SourceExtractionRecord stores segments as plain serializable
        dictionaries so they can be persisted in PostgreSQL JSONB.
        """

        return [
            {
                "index": segment.index,
                "text": self._sanitize_text(segment.text) or "",
                "start_offset": segment.start_offset,
                "end_offset": segment.end_offset,
                "metadata": dict(
                    segment.metadata or {},
                ),
            }
            for segment in segments
        ]
