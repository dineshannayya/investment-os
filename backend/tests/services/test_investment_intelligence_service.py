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
    InvestmentSignals,
    RiskAssessment,
)
from app.processors import DocumentContent
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)

# ============================================================================
# Test doubles
# ============================================================================


class FakeExtractor:
    """Simple intelligence extractor."""

    def __init__(self, name: str, result):
        self.name = name
        self.result = result
        self.called = False

    def extract(self, document, chunks):
        self.called = True
        self.document = document
        self.chunks = chunks
        return self.result


class FakeIntelligenceFactory:
    """Fake IntelligenceFactory."""

    def __init__(self, *extractors):
        self.extractors = list(extractors)


# ============================================================================
# Tests
# ============================================================================


class TestInvestmentIntelligenceService:

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
    # Metadata
    # ------------------------------------------------------------------

    def test_default_metadata(self):

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )

        document = self.create_document()

        profile = service.analyze(
            document,
            self.create_chunks(),
        )

        assert profile.metadata.title == document.title
        assert profile.metadata.page_count == document.page_count

    # ------------------------------------------------------------------
    # Complete Profile
    # ------------------------------------------------------------------

    def test_complete_profile(self):

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

        signals = InvestmentSignals(
            stage="seed",
            confidence=0.60,
        )

        risks = RiskAssessment(
            financial_risks=("pre_revenue",),
            confidence=0.50,
        )

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor("metadata", metadata),
                FakeExtractor("entities", entities),
                FakeExtractor("financials", financials),
                FakeExtractor("signals", signals),
                FakeExtractor("risks", risks),
            ),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert isinstance(
            profile,
            InvestmentProfile,
        )

        assert profile.metadata is metadata
        assert profile.entities is entities
        assert profile.financials is financials
        assert profile.signals is signals
        assert profile.risks is risks

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def test_default_entities(self):

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.entities == InvestmentEntities()

    def test_default_financials(self):

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.financials == FinancialMetrics()

    def test_default_signals(self):

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.signals == InvestmentSignals()

    def test_default_risks(self):

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.risks == RiskAssessment()

    # ------------------------------------------------------------------
    # Extras
    # ------------------------------------------------------------------

    def test_unknown_extractor_goes_to_extras(self):

        class Dummy:
            pass

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor(
                    "dummy",
                    Dummy(),
                ),
            ),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert "dummy" in profile.extras

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def test_confidence_average(self):

        metadata = DocumentMetadata(
            title="Test",
            confidence=0.9,
        )

        entities = InvestmentEntities(
            confidence=0.8,
        )

        financials = FinancialMetrics(
            confidence=0.7,
        )

        signals = InvestmentSignals(
            confidence=0.6,
        )

        risks = RiskAssessment(
            confidence=0.5,
        )

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor("metadata", metadata),
                FakeExtractor("entities", entities),
                FakeExtractor("financials", financials),
                FakeExtractor("signals", signals),
                FakeExtractor("risks", risks),
            ),
        )

        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )

        assert profile.confidence == pytest.approx(
            (0.9 + 0.8 + 0.7 + 0.6 + 0.5) / 5
        )

    # ------------------------------------------------------------------
    # Extractor invocation
    # ------------------------------------------------------------------

    def test_extractors_receive_document_and_chunks(self):

        extractor = FakeExtractor(
            "metadata",
            DocumentMetadata(title="Test"),
        )

        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                extractor,
            ),
        )

        document = self.create_document()
        chunks = self.create_chunks()

        service.analyze(
            document,
            chunks,
        )

        assert extractor.called
        assert extractor.document is document
        assert extractor.chunks is chunks

    def test_extractor_order_independent(self):
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor("financials", FinancialMetrics()),
                FakeExtractor("metadata", DocumentMetadata(title="Test")),
                FakeExtractor("signals", InvestmentSignals()),
                FakeExtractor("entities", InvestmentEntities()),
                FakeExtractor("risks", RiskAssessment()),
            ),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        assert profile.metadata.title == "Test"
