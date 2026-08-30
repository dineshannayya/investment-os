"""
Adapter from persisted SourceExtractionRecord to DocumentContent.

The source-extraction subsystem persists the final extraction artifact
as SourceExtractionRecord.

Downstream document-processing consumers operate on DocumentContent.

This adapter is the compatibility boundary between those two models.

Responsibilities:
    - Convert persisted extraction content into DocumentContent.
    - Reconstruct DocumentSegment objects.
    - Preserve extraction provenance in DocumentContent.metadata.
    - Preserve page count, title, text, and segment information.

Non-responsibilities:
    - Database access.
    - File access.
    - Extraction.
    - OCR.
    - Chunking.
    - Investment intelligence.
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


class SourceExtractionDocumentAdapter:
    """
    Convert persisted SourceExtractionRecord into DocumentContent.

    SourceExtractionRecord is the persistent representation of the
    canonical extraction artifact.

    DocumentContent is the downstream processing contract.
    """

    @classmethod
    def to_document_content(
        cls,
        record: SourceExtractionRecord,
        *,
        document_id: UUID,
    ) -> DocumentContent:
        """
        Convert a persisted extraction record into DocumentContent.

        The supplied document_id is used as the identity expected by
        downstream document-processing consumers.

        The extraction record's source_id remains available through
        metadata and is not substituted for document_id.
        """

        metadata = cls._build_metadata(record)

        segments = cls._build_segments(
            record.segments,
        )

        return DocumentContent(
            document_id=document_id,
            text=record.text or "",
            title=record.title,
            page_count=record.page_count or 0,
            metadata=metadata,
            segments=tuple(segments),
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @staticmethod
    def _build_metadata(
        record: SourceExtractionRecord,
    ) -> dict[str, Any]:
        """
        Reconstruct extraction provenance metadata.

        Provenance is deliberately preserved because downstream consumers
        may need to understand how the content was produced.
        """

        metadata: dict[str, Any] = {}

        metadata.update(
            {
                "source_extraction_id": str(
                    record.extraction_id,
                ),
                "source_id": str(
                    record.source_id,
                ),
                "source_sha256": record.source_sha256,
                "extraction_status": (
                    record.status.value
                    if hasattr(record.status, "value")
                    else str(record.status)
                ),
                "extraction_quality": (
                    record.quality.value
                    if hasattr(record.quality, "value")
                    else str(record.quality)
                ),
                "quality_warnings": list(
                    record.quality_warnings or [],
                ),
                "extraction_method": (
                    record.provenance.method.value
                    if hasattr(
                        record.provenance.method,
                        "value",
                    )
                    else str(record.provenance.method)
                ),
                "processor_name": (
                    record.provenance.processor_name
                ),
                "fallback_used": (
                    record.provenance.fallback_used
                ),
                "fallback_reason": (
                    record.provenance.fallback_reason
                ),
            }
        )

        # Preserve the exact processor configuration.
        #
        # Do not flatten or reinterpret it. The persisted extraction
        # provenance is the source of truth.
        configuration = dict(
            record.provenance.configuration or {},
        )

        metadata["extraction_config"] = configuration

        # Also expose configuration fields at the top level when
        # available. This keeps compatibility with the metadata shape
        # produced by processors.
        metadata.update(configuration)

        return metadata

    # ------------------------------------------------------------------
    # Segments
    # ------------------------------------------------------------------

    @classmethod
    def _build_segments(
        cls,
        segments: list[dict[str, Any]] | None,
    ) -> list[DocumentSegment]:
        """
        Reconstruct DocumentSegment objects.

        Persisted segments are JSON-compatible dictionaries.

        Expected representation:

            {
                "index": int,
                "text": str,
                "start_offset": int,
                "end_offset": int,
                "metadata": dict
            }

        The orchestrator persists exactly this structure.
        """

        if not segments:
            return []

        result: list[DocumentSegment] = []

        for position, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise ValueError(
                    "Invalid persisted extraction segment at "
                    f"index {position}: expected dict, "
                    f"got {type(segment).__name__}"
                )

            result.append(
                cls._build_segment(
                    segment,
                    position=position,
                )
            )

        return result

    @staticmethod
    def _build_segment(
        segment: dict[str, Any],
        *,
        position: int,
    ) -> DocumentSegment:
        """
        Convert one persisted segment dictionary into DocumentSegment.
        """

        try:
            index = int(
                segment.get(
                    "index",
                    position,
                )
            )

            text = segment.get(
                "text",
                "",
            )

            start_offset = int(
                segment.get(
                    "start_offset",
                    0,
                )
            )

            end_offset = int(
                segment.get(
                    "end_offset",
                    start_offset + len(text),
                )
            )

            metadata = segment.get(
                "metadata",
                {},
            )

        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Invalid persisted extraction segment at "
                f"position {position}"
            ) from exc

        if not isinstance(text, str):
            raise ValueError(
                "Invalid persisted extraction segment text at "
                f"position {position}: expected str"
            )

        if not isinstance(metadata, dict):
            raise ValueError(
                "Invalid persisted extraction segment metadata at "
                f"position {position}: expected dict"
            )

        return DocumentSegment(
            index=index,
            text=text,
            start_offset=start_offset,
            end_offset=end_offset,
            metadata=dict(metadata),
        )
