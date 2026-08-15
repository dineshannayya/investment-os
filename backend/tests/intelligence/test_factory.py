"""
Tests for IntelligenceFactory.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.entities import EntityExtractor
from app.intelligence.factory import (
    IntelligenceFactory,
    create_intelligence_factory,
)
from app.intelligence.financial import FinancialExtractor
from app.intelligence.metadata import MetadataExtractor
from app.intelligence.models import DocumentMetadata
from app.intelligence.risk import RiskExtractor
from app.processors import DocumentContent

# ============================================================================
# Test Doubles
# ============================================================================


class DummyExtractor(IntelligenceExtractor[dict]):
    """Dummy extractor."""

    @property
    def name(self) -> str:
        return "dummy"

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> dict:
        return {
            "title": document.title,
            "chunks": len(chunks),
        }


class UnsupportedExtractor(IntelligenceExtractor[dict]):
    """Extractor that supports no documents."""

    @property
    def name(self) -> str:
        return "unsupported"

    def supports(
        self,
        document: DocumentContent,
    ) -> bool:
        return False

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> dict:
        return {}


# ============================================================================
# Tests
# ============================================================================


class TestIntelligenceFactory:
    """Tests for IntelligenceFactory."""

    @staticmethod
    def create_document() -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title="SemSure Pitch Deck",
            text="Investment OS",
            page_count=5,
            metadata={},
        )

    @staticmethod
    def create_chunks() -> list[Chunk]:
        return [
            Chunk(
                index=0,
                text="Investment OS",
                start_offset=0,
                end_offset=13,
                metadata={},
            )
        ]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_register(self):
        factory = IntelligenceFactory()

        extractor = DummyExtractor()

        factory.register(extractor)

        assert len(factory.extractors) == 1
        assert factory.extractors[0] is extractor

    def test_duplicate_registration_ignored(self):
        factory = IntelligenceFactory()

        extractor = DummyExtractor()

        factory.register(extractor)
        factory.register(extractor)

        assert len(factory.extractors) == 1

    def test_clear(self):
        factory = IntelligenceFactory()

        factory.register(DummyExtractor())

        assert len(factory.extractors) == 1

        factory.clear()

        assert factory.extractors == ()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def test_run_single_extractor(self):
        factory = IntelligenceFactory()

        factory.register(DummyExtractor())

        results = factory.run(
            self.create_document(),
            self.create_chunks(),
        )

        assert "dummy" in results
        assert results["dummy"]["title"] == "SemSure Pitch Deck"
        assert results["dummy"]["chunks"] == 1

    def test_run_multiple_extractors(self):
        factory = IntelligenceFactory()

        factory.register(DummyExtractor())
        factory.register(MetadataExtractor())

        results = factory.run(
            self.create_document(),
            self.create_chunks(),
        )

        assert "dummy" in results
        assert "metadata" in results

        assert isinstance(
            results["metadata"],
            DocumentMetadata,
        )

    def test_skip_unsupported_extractor(self):
        factory = IntelligenceFactory()

        factory.register(UnsupportedExtractor())

        results = factory.run(
            self.create_document(),
            self.create_chunks(),
        )

        assert results == {}

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    def test_create_intelligence_factory(self):
        factory = create_intelligence_factory()

        assert any(
            isinstance(extractor, MetadataExtractor)
            for extractor in factory.extractors
        )
        
        assert any(
            isinstance(extractor, EntityExtractor)
            for extractor in factory.extractors
        )
        
        assert any(
            isinstance(extractor, FinancialExtractor)
            for extractor in factory.extractors
        )

        assert any(
            isinstance(extractor, RiskExtractor)
            for extractor in factory.extractors
        )

        assert len(factory.extractors) == 4

    def test_extractors_property_returns_tuple(self):
        factory = IntelligenceFactory()

        factory.register(DummyExtractor())

        assert isinstance(
            factory.extractors,
            tuple,
        )
