"""
Tests for the OCR document processor.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from app.processors.ocr import OcrProcessor


class TestOcrProcessor:
    """Tests for OcrProcessor."""

    def test_supported_pdf(self):
        processor = OcrProcessor()

        assert processor.supports(
            Path("document.pdf"),
            "application/pdf",
        )

    def test_supported_extension(self):
        processor = OcrProcessor()

        assert processor.supports(
            Path("document.pdf"),
            "application/octet-stream",
        )

    def test_unsupported_file(self):
        processor = OcrProcessor()

        assert not processor.supports(
            Path("document.docx"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_invalid_dpi(self):
        with pytest.raises(
            ValueError,
            match="dpi must be greater than zero",
        ):
            OcrProcessor(dpi=0)

    def test_invalid_timeout(self):
        with pytest.raises(
            ValueError,
            match="timeout_seconds must be greater than zero",
        ):
            OcrProcessor(timeout_seconds=0)

    def test_missing_source(self):
        processor = OcrProcessor()

        with pytest.raises(
            FileNotFoundError,
            match="does not exist",
        ):
            processor.process(
                uuid4(),
                Path("/tmp/nonexistent.pdf"),
            )
