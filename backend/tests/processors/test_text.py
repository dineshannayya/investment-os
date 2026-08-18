"""
Tests for TextProcessor.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.processors.text import TextProcessor
from app.processors.base import (
    DocumentContent,
    DocumentSegment,
)

class TestTextProcessor:
    """Tests for TextProcessor."""

    @staticmethod
    def create_processor() -> TextProcessor:
        """Create a TextProcessor."""
        return TextProcessor()

    # -------------------------------------------------------------------------
    # Supported types
    # -------------------------------------------------------------------------

    def test_supported_mime_types(self) -> None:
        """Verify supported MIME types."""

        processor = self.create_processor()

        assert "text/plain" in processor.supported_mime_types

    def test_supported_extensions(self) -> None:
        """Verify supported extensions."""

        processor = self.create_processor()

        assert ".txt" in processor.supported_extensions
        assert ".text" in processor.supported_extensions
        assert ".md" in processor.supported_extensions

    # -------------------------------------------------------------------------
    # supports()
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("filename", "mime_type"),
        [
            ("notes.txt", "text/plain"),
            ("README.md", "text/plain"),
            ("document.text", "text/plain"),
            ("notes.txt", "application/octet-stream"),
            ("README.md", "application/octet-stream"),
        ],
    )
    def test_supports_valid_files(
        self,
        tmp_path,
        filename: str,
        mime_type: str,
    ) -> None:
        """Supported files should return True."""

        processor = self.create_processor()

        path = tmp_path / filename
        path.write_text("Hello")

        assert processor.supports(path, mime_type)

    @pytest.mark.parametrize(
        ("filename", "mime_type"),
        [
            ("image.png", "image/png"),
            ("report.pdf", "application/pdf"),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ],
    )
    def test_supports_invalid_files(
        self,
        tmp_path,
        filename: str,
        mime_type: str,
    ) -> None:
        """Unsupported files should return False."""

        processor = self.create_processor()

        path = tmp_path / filename
        path.write_bytes(b"")

        assert not processor.supports(path, mime_type)

    # -------------------------------------------------------------------------
    # process()
    # -------------------------------------------------------------------------

    def test_process_text_file(
        self,
        tmp_path,
    ) -> None:
        """Process a UTF-8 text file."""

        processor = self.create_processor()

        path = tmp_path / "notes.txt"

        path.write_text(
            "Investment OS\nDocument Processor",
            encoding="utf-8",
        )

        document = processor.process(
            uuid4(),
            path,
        )

        assert isinstance(document, DocumentContent)

        assert document.title == "notes"

        assert document.text == (
            "Investment OS\nDocument Processor"
        )

        assert document.page_count == 1

        assert document.metadata["filename"] == "notes.txt"
        assert document.metadata["extension"] == ".txt"
        assert document.metadata["encoding"] == "utf-8"

        assert len(document.segments) == 1
        
        segment = document.segments[0]
        
        assert segment.index == 0
        assert segment.text == document.text
        assert segment.metadata["type"] == "document"
        assert segment.start_offset == 0
        assert segment.end_offset == len(document.text)
        
        assert (
            document.text[segment.start_offset:segment.end_offset]
            == segment.text
        )


    def test_process_markdown_file(
        self,
        tmp_path,
    ) -> None:
        """Markdown files are treated as plain text."""

        processor = self.create_processor()

        path = tmp_path / "README.md"

        path.write_text(
            "# Heading\n\nSome text.",
            encoding="utf-8",
        )

        document = processor.process(
            uuid4(),
            path,
        )

        assert document.title == "README"
        assert "# Heading" in document.text
        assert document.metadata["extension"] == ".md"

        assert len(document.segments) == 1
        
        segment = document.segments[0]
        
        assert segment.text == document.text
        assert segment.metadata["type"] == "document"
        assert segment.start_offset == 0
        assert segment.end_offset == len(document.text)


    def test_process_empty_file(
        self,
        tmp_path,
    ) -> None:
        """Empty text files are supported."""

        processor = self.create_processor()

        path = tmp_path / "empty.txt"

        path.write_text(
            "",
            encoding="utf-8",
        )

        document = processor.process(
            uuid4(),
            path,
        )

        assert document.text == ""
        assert document.page_count == 1

        assert len(document.segments) == 1
        
        segment = document.segments[0]
        
        assert segment.text == ""
        assert segment.start_offset == 0
        assert segment.end_offset == 0
        assert segment.metadata["type"] == "document"


    def test_process_latin1_file(
        self,
        tmp_path,
    ) -> None:
        """Latin-1 fallback is used."""

        processor = self.create_processor()

        path = tmp_path / "latin1.txt"

        text = "Café"

        path.write_bytes(
            text.encode("latin-1"),
        )

        document = processor.process(
            uuid4(),
            path,
        )

        assert document.text == text

        assert len(document.segments) == 1
        
        segment = document.segments[0]
        
        assert segment.text == text
        assert segment.start_offset == 0
        assert segment.end_offset == len(text)
        assert segment.metadata["type"] == "document"


    def test_document_id_preserved(
        self,
        tmp_path,
    ) -> None:
        """Document ID is preserved."""

        processor = self.create_processor()

        path = tmp_path / "notes.txt"

        path.write_text(
            "Investment OS",
            encoding="utf-8",
        )

        document_id = uuid4()

        document = processor.process(
            document_id,
            path,
        )

        assert document.document_id == document_id
