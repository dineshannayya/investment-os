"""
PDF document processor.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pypdf import PdfReader

from app.processors.base import (
    DocumentContent,
    DocumentProcessor,
)


class PdfProcessor(DocumentProcessor):
    """
    Processor for PDF documents.
    """

    _SUPPORTED_MIME_TYPES = {
        "application/pdf",
    }

    _SUPPORTED_EXTENSIONS = {
        ".pdf",
    }

    @property
    def supported_mime_types(self) -> set[str]:
        """Return supported MIME types."""
        return self._SUPPORTED_MIME_TYPES

    @property
    def supported_extensions(self) -> set[str]:
        """Return supported extensions."""
        return self._SUPPORTED_EXTENSIONS

    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        """
        Extract text from a PDF document.
        """

        reader = PdfReader(path)

        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        text = "\n\n".join(pages)

        metadata = {}

        if reader.metadata:
            for key, value in reader.metadata.items():
                metadata[key.lstrip("/")] = (
                    str(value) if value is not None else ""
                )

        metadata.update(
            {
                "filename": path.name,
                "extension": path.suffix.lower(),
            }
        )

        title = path.stem
        
        if reader.metadata:
            pdf_title = getattr(reader.metadata, "title", None)
            if pdf_title:
                pdf_title = pdf_title.strip()
        
                if pdf_title.lower() not in {
                    "",
                    "untitled",
                    "none",
                }:
                    title = pdf_title


        return DocumentContent(
            document_id=document_id,
            title=title,
            text=text,
            page_count=len(reader.pages),
            metadata=metadata,
        )
