"""
Tests for ProcessorFactory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.processors import (
    DocumentContent,
    DocumentProcessor,
)
from app.processors.docx import DocxProcessor
from app.processors.factory import (
    ProcessorFactory,
    create_processor_factory,
)
from app.processors.pdf import PdfProcessor
from app.processors.text import TextProcessor

# ============================================================================
# Test Processor
# ============================================================================


class DummyProcessor(DocumentProcessor):
    """Dummy processor for factory tests."""

    @property
    def supported_mime_types(self) -> set[str]:
        return {"application/x-dummy"}

    @property
    def supported_extensions(self) -> set[str]:
        return {".dummy"}

    def process(
        self,
        document_id,
        path,
    ) -> DocumentContent:
        return DocumentContent(
            document_id=document_id,
            title="Dummy",
            text="Dummy",
            page_count=1,
            metadata={},
        )


# ============================================================================
# Tests
# ============================================================================


class TestProcessorFactory:
    """Tests for ProcessorFactory."""

    def test_register_processor(self):
        """Register a processor."""

        factory = ProcessorFactory()
        processor = DummyProcessor()

        factory.register(processor)

        assert len(factory.processors) == 1
        assert factory.processors[0] is processor

    def test_duplicate_registration_is_ignored(self):
        """Duplicate registration should not add another instance."""

        factory = ProcessorFactory()
        processor = DummyProcessor()

        factory.register(processor)
        factory.register(processor)

        assert len(factory.processors) == 1

    def test_clear(self):
        """Clear all processors."""

        factory = ProcessorFactory()

        factory.register(DummyProcessor())

        assert len(factory.processors) == 1

        factory.clear()

        assert factory.processors == ()

    def test_supports_registered_processor(self):
        """supports() returns True."""

        factory = ProcessorFactory()
        factory.register(DummyProcessor())

        assert factory.supports(
            Path("sample.dummy"),
            "application/x-dummy",
        )

    def test_supports_unknown_processor(self):
        """supports() returns False."""

        factory = ProcessorFactory()

        assert not factory.supports(
            Path("sample.pdf"),
            "application/pdf",
        )

    def test_get_processor(self):
        """Return matching processor."""

        factory = ProcessorFactory()

        processor = DummyProcessor()

        factory.register(processor)

        result = factory.get_processor(
            Path("sample.dummy"),
            "application/x-dummy",
        )

        assert result is processor

    def test_get_processor_unknown(self):
        """Unknown processor raises ValueError."""

        factory = ProcessorFactory()

        with pytest.raises(
            ValueError,
            match="No processor registered",
        ):
            factory.get_processor(
                Path("sample.pdf"),
                "application/pdf",
            )

    def test_processors_property_is_tuple(self):
        """processors property returns immutable tuple."""

        factory = ProcessorFactory()

        factory.register(DummyProcessor())

        assert isinstance(
            factory.processors,
            tuple,
        )

    # -------------------------------------------------------------------------
    # Default factory
    # -------------------------------------------------------------------------

    def test_create_processor_factory(self):
        """Built-in processors are registered."""

        factory = create_processor_factory()

        assert any(
            isinstance(p, TextProcessor)
            for p in factory.processors
        )

        assert any(
            isinstance(p, PdfProcessor)
            for p in factory.processors
        )

        assert any(
            isinstance(p, DocxProcessor)
            for p in factory.processors
        )

    @pytest.mark.parametrize(
        ("filename", "mime_type", "expected"),
        [
            ("notes.txt", "text/plain", TextProcessor),
            ("deck.pdf", "application/pdf", PdfProcessor),
            (
                "proposal.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                DocxProcessor,
            ),
        ],
    )
    def test_default_factory_lookup(
        self,
        filename,
        mime_type,
        expected,
    ):
        """Default factory resolves built-in processors."""

        factory = create_processor_factory()

        processor = factory.get_processor(
            Path(filename),
            mime_type,
        )

        assert isinstance(
            processor,
            expected,
        )
