"""
Tests for PdfProcessor.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from reportlab.pdfgen import canvas

from app.processors.base import DocumentContent
from app.processors.pdf import PdfProcessor


class TestPdfProcessor:
    """Tests for PdfProcessor."""

    @staticmethod
    def create_processor() -> PdfProcessor:
        """Create a PdfProcessor."""
        return PdfProcessor()

    @staticmethod
    def create_pdf(
        path,
        pages: list[str],
        title: str | None = None,
        author: str | None = None,
    ) -> None:
        """Create a simple PDF for testing."""

        pdf = canvas.Canvas(str(path))

        if title:
            pdf.setTitle(title)

        if author:
            pdf.setAuthor(author)

        for text in pages:
            pdf.drawString(72, 750, text)
            pdf.showPage()

        pdf.save()

    # ---------------------------------------------------------------------
    # Supported types
    # ---------------------------------------------------------------------

    def test_supported_mime_types(self):
        processor = self.create_processor()

        assert "application/pdf" in processor.supported_mime_types

    def test_supported_extensions(self):
        processor = self.create_processor()

        assert ".pdf" in processor.supported_extensions

    # ---------------------------------------------------------------------
    # supports()
    # ---------------------------------------------------------------------

    def test_supports_pdf(self, tmp_path):
        processor = self.create_processor()

        pdf = tmp_path / "sample.pdf"

        self.create_pdf(pdf, ["Hello"])

        assert processor.supports(
            pdf,
            "application/pdf",
        )

    def test_rejects_non_pdf(self, tmp_path):
        processor = self.create_processor()

        text = tmp_path / "sample.txt"
        text.write_text("hello")

        assert not processor.supports(
            text,
            "text/plain",
        )

    # ---------------------------------------------------------------------
    # process()
    # ---------------------------------------------------------------------

    def test_process_single_page_pdf(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "single.pdf"

        self.create_pdf(
            pdf,
            ["Investment OS"],
        )

        document = processor.process(
            uuid4(),
            pdf,
        )

        assert isinstance(
            document,
            DocumentContent,
        )

        assert "Investment OS" in document.text
        assert document.page_count == 1

    def test_process_multiple_pages(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "multi.pdf"

        self.create_pdf(
            pdf,
            [
                "Page One",
                "Page Two",
                "Page Three",
            ],
        )

        document = processor.process(
            uuid4(),
            pdf,
        )

        assert document.page_count == 3

        assert "Page One" in document.text
        assert "Page Two" in document.text
        assert "Page Three" in document.text

    def test_pdf_title_metadata(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "meta.pdf"

        self.create_pdf(
            pdf,
            ["Hello"],
            title="Investment Deck",
            author="OpenAI",
        )

        document = processor.process(
            uuid4(),
            pdf,
        )

        assert document.title == "Investment Deck"

        assert (
            document.metadata["Author"]
            == "OpenAI"
        )

    def test_fallback_title(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "pitch_deck.pdf"

        self.create_pdf(
            pdf,
            ["Hello"],
        )

        document = processor.process(
            uuid4(),
            pdf,
        )

        assert document.title == "pitch_deck"

    def test_filename_metadata(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "sample.pdf"

        self.create_pdf(
            pdf,
            ["Hello"],
        )

        document = processor.process(
            uuid4(),
            pdf,
        )

        assert (
            document.metadata["filename"]
            == "sample.pdf"
        )

        assert (
            document.metadata["extension"]
            == ".pdf"
        )

    def test_document_id_preserved(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "sample.pdf"

        self.create_pdf(
            pdf,
            ["Hello"],
        )

        document_id = uuid4()

        document = processor.process(
            document_id,
            pdf,
        )

        assert (
            document.document_id
            == document_id
        )

    def test_missing_pdf(
        self,
        tmp_path,
    ):
        processor = self.create_processor()

        pdf = tmp_path / "missing.pdf"

        with pytest.raises(FileNotFoundError):
            processor.process(
                uuid4(),
                pdf,
            )
