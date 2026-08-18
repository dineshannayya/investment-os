"""
Plain text document processor.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.processors.base import (
    DocumentContent,
    DocumentProcessor,
    DocumentSegment,
)


class TextProcessor(DocumentProcessor):
    """
    Processor for plain text documents.
    """

    _SUPPORTED_MIME_TYPES = {
        "text/plain",
    }

    _SUPPORTED_EXTENSIONS = {
        ".txt",
        ".text",
        ".md",
    }

    @property
    def supported_mime_types(self) -> set[str]:
        """Return supported MIME types."""

        return self._SUPPORTED_MIME_TYPES

    @property
    def supported_extensions(self) -> set[str]:
        """Return supported file extensions."""

        return self._SUPPORTED_EXTENSIONS

    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        """
        Extract text from a plain text document.
        """
    
        text, encoding = self._read_text(path)
    
        title = path.stem
    
        metadata = {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "encoding": encoding,
        }
    
        segments = (
            DocumentSegment(
                index=0,
                text=text,
                start_offset=0,
                end_offset=len(text),
                metadata={
                    "type": "document",
                },
            ),
        )
    
        return DocumentContent(
            document_id=document_id,
            title=title,
            text=text,
            page_count=1,
            metadata=metadata,
            segments=segments,
        )


    @staticmethod
    def _read_text(path: Path) -> str:
        """
        Read a text file.

        UTF-8 is attempted first, followed by a Latin-1 fallback.
        """
        try:
            return (
                path.read_text(encoding="utf-8"),
                "utf-8",
            )
        except UnicodeDecodeError:
            return (
                path.read_text(encoding="latin-1"),
                "latin-1",
            )

