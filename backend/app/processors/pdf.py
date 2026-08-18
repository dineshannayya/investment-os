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
    DocumentSegment,
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
            page_text = (page.extract_text() or "").strip()
            pages.append(page_text)

        
        text = "\n\n".join(pages)
        
        segments: list[DocumentSegment] = []
        
        offset = 0
        
        for index, page_text in enumerate(pages):
            start_offset = offset
            end_offset = start_offset + len(page_text)
        
            segments.append(
                DocumentSegment(
                    index=index,
                    text=page_text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    metadata={
                        "type": "page",
                        "page": index + 1,
                    },
                )
            )
        
            offset = end_offset
        
            # Account for the "\n\n" separator used by the joined document text.
            if index < len(pages) - 1:
                offset += 2

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
            segments=tuple(segments),
        )
