"""
Tests for MetadataExtractor.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.metadata import MetadataExtractor
from app.processors import DocumentContent


class TestMetadataExtractor:
    """Tests for MetadataExtractor."""

    @staticmethod
    def create_document(
        *,
        title: str = "",
        text: str = "",
        page_count: int = 1,
    ) -> DocumentContent:
        """Create a test document."""

        return DocumentContent(
            document_id=uuid4(),
            title=title,
            text=text,
            page_count=page_count,
            metadata={},
        )

    @staticmethod
    def create_chunks(document: DocumentContent) -> list[Chunk]:
        """Create a single chunk."""

        return [
            Chunk(
                index=0,
                text=document.text,
                start_offset=0,
                end_offset=len(document.text),
                metadata={},
            )
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_name(self):
        extractor = MetadataExtractor()

        assert extractor.name == "metadata"

    def test_supports(self):
        extractor = MetadataExtractor()

        document = self.create_document(text="Hello")

        assert extractor.supports(document)

    # ------------------------------------------------------------------
    # Title extraction
    # ------------------------------------------------------------------

    def test_extract_document_title(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="SemSure Pitch Deck",
            text="Ignored",
            page_count=12,
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.title == "SemSure Pitch Deck"

    def test_extract_first_line_as_title(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            text=(
                "Investment OS\n"
                "\n"
                "Second line"
            ),
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.title == "Investment OS"

    def test_extract_untitled_document(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            text="",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.title == "Untitled"

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def test_extract_sections(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Pitch Deck",
            text="""
# Problem

Some text

# Solution

More text

Financials:

Even more text
""",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.sections == (
            "# Problem",
            "# Solution",
            "Financials",
        )

    def test_duplicate_sections_removed(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            text="""
Problem:

Some text

Problem:

Another paragraph
""",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.sections == (
            "Problem",
        )

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------

    def test_extract_keywords(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            text="""
AI Healthcare AI
Healthcare Startup
Startup Investment
""",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert "ai" in metadata.keywords
        assert "healthcare" in metadata.keywords
        assert "startup" in metadata.keywords

    def test_stop_words_removed(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            text="""
the and this that with from company
investment healthcare ai
""",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert "the" not in metadata.keywords
        assert "and" not in metadata.keywords
        assert "company" not in metadata.keywords

        assert "investment" in metadata.keywords
        assert "healthcare" in metadata.keywords

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def test_pitch_deck_classification(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="SemSure Pitch Deck",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.document_type == "Pitch Deck"

    def test_term_sheet_classification(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Series A Term Sheet",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.document_type == "Term Sheet"

    def test_sha_classification(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Shareholder Agreement",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.document_type == "Shareholders Agreement"

    def test_unknown_document_type(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Meeting Notes",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.document_type is None

    # ------------------------------------------------------------------
    # Page count / confidence
    # ------------------------------------------------------------------

    def test_page_count(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Pitch Deck",
            page_count=18,
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.page_count == 18

    def test_confidence(self):
        extractor = MetadataExtractor()

        document = self.create_document(
            title="Pitch Deck",
        )

        metadata = extractor.extract(
            document,
            self.create_chunks(document),
        )

        assert metadata.confidence == 1.0
