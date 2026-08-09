"""
Tests for DocxProcessor.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from docx import Document as WordDocument

from app.processors.base import DocumentContent
from app.processors.docx import DocxProcessor


class TestDocxProcessor:
    """Tests for DocxProcessor."""

    @staticmethod
    def create_processor() -> DocxProcessor:
        """Create a DocxProcessor."""
        return DocxProcessor()

    @staticmethod
    def create_docx(
        path,
        paragraphs: list[str],
        *,
        title: str | None = None,
        author: str | None = None,
        subject: str | None = None,
    ) -> None:
        """Create a DOCX document for testing."""

        document = WordDocument()

        core = document.core_properties

        if title:
            core.title = title

        if author:
            core.author = author

        if subject:
            core.subject = subject

        for paragraph in paragraphs:
            document.add_paragraph(paragraph)

        document.save(path)

    # ---------------------------------------------------------------------
    # Supported types
    # ---------------------------------------------------------------------

    def test_supported_mime_types(self):
        processor = self.create_processor()

        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in processor.supported_mime_types
        )

    def test_supported_extensions(self):
        processor = self.create_processor()

        assert ".docx" in processor.supported_extensions

    # ---------------------------------------------------------------------
    # supports()
    # ---------------------------------------------------------------------

    def test_supports_docx(self, tmp_path):
        processor = self.create_processor()

        docx = tmp_path / "sample.docx"

        self.create_docx(docx, ["Hello"])

        assert processor.supports(
            docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_rejects_non_docx(self, tmp_path):
        processor = self.create_processor()

        txt = tmp_path / "notes.txt"
        txt.write_text("Hello")

        assert not processor.supports(
            txt,
            "text/plain",
        )

    # ---------------------------------------------------------------------
    # process()
    # ---------------------------------------------------------------------

    def test_process_single_paragraph(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "single.docx"

        self.create_docx(
            docx,
            ["Investment OS"],
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert isinstance(
            document,
            DocumentContent,
        )

        assert document.text == "Investment OS"
        assert document.page_count == 1

    def test_process_multiple_paragraphs(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "multi.docx"

        self.create_docx(
            docx,
            [
                "Paragraph One",
                "Paragraph Two",
                "Paragraph Three",
            ],
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert "Paragraph One" in document.text
        assert "Paragraph Two" in document.text
        assert "Paragraph Three" in document.text

    def test_empty_document(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "empty.docx"

        self.create_docx(
            docx,
            [],
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert document.text == ""
        assert document.page_count == 1

    def test_document_title(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "meta.docx"

        self.create_docx(
            docx,
            ["Hello"],
            title="Investment Memo",
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert document.title == "Investment Memo"

    def test_filename_fallback(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "pitch_deck.docx"

        self.create_docx(
            docx,
            ["Hello"],
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert document.title == "pitch_deck"

    def test_metadata(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "metadata.docx"

        self.create_docx(
            docx,
            ["Hello"],
            author="OpenAI",
            subject="Testing",
        )

        document = processor.process(
            uuid4(),
            docx,
        )

        assert document.metadata["filename"] == "metadata.docx"
        assert document.metadata["extension"] == ".docx"
        assert document.metadata["author"] == "OpenAI"
        assert document.metadata["subject"] == "Testing"
        assert document.metadata["paragraph_count"] == 1

    def test_document_id_preserved(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "sample.docx"

        self.create_docx(
            docx,
            ["Hello"],
        )

        document_id = uuid4()

        document = processor.process(
            document_id,
            docx,
        )

        assert document.document_id == document_id

    def test_missing_docx(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        docx = tmp_path / "missing.docx"

        with pytest.raises(FileNotFoundError):
            processor.process(
                uuid4(),
                docx,
            )
