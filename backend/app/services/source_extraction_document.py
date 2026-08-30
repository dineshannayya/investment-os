"""
Adapter from persisted source extraction records to DocumentContent.

Responsibilities:
    - Reconstruct DocumentContent from SourceExtractionRecord.
    - Reconstruct DocumentSegment objects from persisted segment dictionaries.
    - Preserve extracted text, title, page count, and metadata.

Non-responsibilities:
    - Source extraction.
    - OCR.
    - File-system access.
    - Database persistence.
    - Chunking.
    - Investment analysis.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.source_extraction_record import (
    SourceExtractionRecord,
)
from app.processors.base import (
    DocumentContent,
    DocumentSegment,
)


class SourceExtractionDocumentError(RuntimeError):
    """Raised when a persisted extraction cannot be adapted."""


class SourceExtractionDocumentAdapter:
    """
    Convert a persisted SourceExtractionRecord into DocumentContent.

    SourceExtractionRecord is the persistence representation.

    DocumentContent is the processor/downstream-consumer representation.

    The adapter intentionally performs no extraction.
    """

    @staticmethod
    def to_document_content(
        extraction: SourceExtractionRecord,
        *,
        document_id: UUID | None = None,
    ) -> DocumentContent:
        """
        Convert a persisted extraction into DocumentContent.

        Args:
            extraction:
                Persisted source extraction artifact.

            document_id:
                Optional downstream Document UUID.

                When supplied, this becomes DocumentContent.document_id.
                Otherwise SourceExtractionRecord.source_id is used.

        Returns:
            DocumentContent reconstructed from the persisted extraction.

        Raises:
            SourceExtractionDocumentError:
                If a persisted segment is malformed.
        """

        resolved_document_id = (
            document_id
            if document_id is not None
            else extraction.source_id
        )

        segments = (
            SourceExtractionDocumentAdapter._restore_segments(
                extraction.segments,
            )
        )

        metadata = (
            SourceExtractionDocumentAdapter._build_metadata(
                extraction,
            )
        )

        return DocumentContent(
            document_id=resolved_document_id,
            text=extraction.text,
            title=extraction.title,
            page_count=extraction.page_count or 0,
            metadata=metadata,
            segments=tuple(segments),
        )

    # ------------------------------------------------------------------
    # Segment reconstruction
    # ------------------------------------------------------------------

    @staticmethod
    def _restore_segments(
        segments: list[dict[str, Any]],
    ) -> list[DocumentSegment]:
        """
        Reconstruct DocumentSegment objects from JSON-compatible data.
        """

        restored: list[DocumentSegment] = []

        for position, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise SourceExtractionDocumentError(
                    "Invalid persisted extraction segment at "
                    f"position {position}: expected dict."
                )

            try:
                index = int(segment["index"])
                text = str(segment.get("text", ""))
                start_offset = int(segment["start_offset"])
                end_offset = int(segment["end_offset"])

                raw_metadata = segment.get(
                    "metadata",
                    {},
                )

                if raw_metadata is None:
                    metadata: dict[str, Any] = {}

                elif isinstance(raw_metadata, dict):
                    metadata = dict(raw_metadata)

                else:
                    raise TypeError(
                        "metadata must be a dictionary"
                    )

            except (KeyError, TypeError, ValueError) as exc:
                raise SourceExtractionDocumentError(
                    "Invalid persisted extraction segment at "
                    f"position {position}: {exc}"
                ) from exc

            restored.append(
                DocumentSegment(
                    index=index,
                    text=text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    metadata=metadata,
                )
            )

        return restored

    # ------------------------------------------------------------------
    # Metadata reconstruction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_metadata(
        extraction: SourceExtractionRecord,
    ) -> dict[str, Any]:
        """
        Reconstruct downstream metadata from extraction provenance.

        The persisted extraction remains the source of truth for
        extraction provenance.
        """

        metadata: dict[str, Any] = {
            "source_id": str(extraction.source_id),
            "source_sha256": extraction.source_sha256,
            "extraction_id": str(extraction.extraction_id),
            "extraction_method": (
                extraction.provenance.method.value
            ),
            "processor_name": (
                extraction.provenance.processor_name
            ),
            "fallback_used": (
                extraction.provenance.fallback_used
            ),
        }

        if extraction.provenance.fallback_reason is not None:
            metadata["fallback_reason"] = (
                extraction.provenance.fallback_reason
            )

        if extraction.provenance.configuration:
            metadata["extraction_config"] = dict(
                extraction.provenance.configuration
            )

        return metadata
