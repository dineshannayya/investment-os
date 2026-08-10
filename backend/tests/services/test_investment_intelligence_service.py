"""
Tests for InvestmentIntelligenceService.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.chunking.base import Chunk
from app.intelligence.models import (
    DocumentMetadata,
    FinancialMetrics,
    InvestmentEntities,
    InvestmentProfile,
)
from app.processors import DocumentContent
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)


# ============================================================================
# Test Double
# ============================================================================


class FakeIntelligenceFactory:
    """Fake intelligence factory."""

    def __init__(self, results=None):
        self._results = results or {}
        self.called = False

    def run(self, document, chunks):
        self.called = True
        self.document = document
        self.chunks = chunks
        return self._results


# ============================================================================
# Tests
# ============================================================================


class TestInvestmentIntelligenceService:
    """Tests for InvestmentIntelligenceService."""

    @staticmethod
    def create_document() -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title="SemSure Pitch Deck",
            text="Investment OS",
            page_count=18,
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
    # Properties
    # ------------------------------------------------------------------

    def test_factory_property(self):
        factory = FakeIntelligenceFactory()

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        assert service.factory is factory

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def test_analyze_metadata_only(self):
        metadata = DocumentMetadata(
            title="SemSure Pitch Deck",
            confidence=0.95,
        )

        factory = FakeIntelligenceFactory(
            {
                "metadata": metadata,
            }
        )

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert factory.called
        assert isinstance(profile, InvestmentProfile)

        assert profile.metadata is metadata
        assert profile.entities == InvestmentEntities()
        assert profile.financials == FinancialMetrics()

    def test_analyze_complete_profile(self):
        metadata = DocumentMetadata(
            title="SemSure",
            confidence=0.90,
        )

        entities = InvestmentEntities(
            company_name="SemSure",
            confidence=0.80,
        )

        financials = FinancialMetrics(
            currency="INR",
            valuation=Decimal("240000000"),
            confidence=0.70,
        )

        factory = FakeIntelligenceFactory(
            {
                "metadata": metadata,
                "entities": entities,
                "financials": financials,
            }
        )

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.metadata is metadata
        assert profile.entities is entities
        assert profile.financials is financials

    def test_default_metadata(self):
        factory = FakeIntelligenceFactory()

        document = self.create_document()

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            document,
            self.create_chunks(),
        )

        assert profile.metadata.title == document.title
        assert profile.metadata.page_count == document.page_count

    def test_default_entities(self):
        factory = FakeIntelligenceFactory(
            {
                "metadata": DocumentMetadata(
                    title="Test",
                )
            }
        )

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.entities == InvestmentEntities()

    def test_default_financials(self):
        factory = FakeIntelligenceFactory(
            {
                "metadata": DocumentMetadata(
                    title="Test",
                )
            }
        )

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.financials == FinancialMetrics()

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def test_confidence_average(self):
        metadata = DocumentMetadata(
            title="Test",
            confidence=0.9,
        )

        entities = InvestmentEntities(
            confidence=0.6,
        )

        financials = FinancialMetrics(
            confidence=0.3,
        )

        factory = FakeIntelligenceFactory(
            {
                "metadata": metadata,
                "entities": entities,
                "financials": financials,
            }
        )

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.confidence == pytest.approx(
            (0.9 + 0.6 + 0.3) / 3
        )

    def test_factory_receives_document_and_chunks(self):
        factory = FakeIntelligenceFactory()

        service = InvestmentIntelligenceService(
            factory=factory,
        )

        document = self.create_document()
        chunks = self.create_chunks()

        service.analyze(
            document,
            chunks,
        )

        assert factory.document is document
        assert factory.chunks is chunks
