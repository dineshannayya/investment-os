"""
Source extraction service.

Converts discovered SourceDocument records into DocumentContent
using the existing processor factory.

No LLM or investment interpretation is performed here.
"""

from __future__ import annotations

from pathlib import Path

from app.models.source_document import (
    ExtractionStatus,
    SourceDocument,
)
from app.processors.factory import create_processor_factory


class SourceExtractionError(RuntimeError):
    """Raised when source extraction fails."""


class SourceExtractionService:
    """
    Extract content from discovered source documents.
    """

    def __init__(
        self,
        processor_factory=None,
    ) -> None:
        self._processor_factory = (
            processor_factory
            or create_processor_factory()
        )

    def extract(
        self,
        source: SourceDocument,
        source_root: Path,
    ):
        """
        Extract one discovered source.

        Args:
            source:
                SourceDocument produced by SourceDiscoveryService.

            source_root:
                Root directory containing the startup sources.

        Returns:
            Processor-produced DocumentContent.
        """

        if source.extraction_status not in (
            ExtractionStatus.DISCOVERED,
            ExtractionStatus.FAILED,
        ):
            raise SourceExtractionError(
                "Source is not eligible for extraction: "
                f"{source.relative_path} "
                f"status={source.extraction_status.value}"
            )

        source_root = source_root.resolve()

        path = (
            source_root
            / source.relative_path
        ).resolve()

        # Prevent accidental path traversal.
        try:
            path.relative_to(source_root)
        except ValueError as exc:
            raise SourceExtractionError(
                f"Source path escapes source root: "
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

        processor = self._processor_factory.get_processor(
            path,
            source.mime_type,
        )

        if processor is None:
            raise SourceExtractionError(
                "No processor available for source: "
                f"{source.relative_path}"
            )

        try:
            content = processor.process(
                source.source_id,
                path,
            )
        except Exception as exc:
            raise SourceExtractionError(
                "Failed to extract source "
                f"{source.relative_path}: {exc}"
            ) from exc

        return content
