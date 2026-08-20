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
    IntelligenceEvidence,
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

    def __init__(
        self,
        name: str,
        result,
        *,
        supported: bool = True,
        evidence=(),
    ):
        self.name = name
        self.result = result
        self.supported = supported
        self.evidence = evidence
        self.called = False
        self.evidence_called = False

    def supports(self, document) -> bool:
        return self.supported

    def extract(self, document, chunks):
        self.called = True
        self.document = document
        self.chunks = chunks
        return self.result

    def extract_evidence(
        self,
        document,
        chunks,
        result,
    ):
        self.evidence_called = True
        self.evidence_document = document
        self.evidence_chunks = chunks
        self.evidence_result = result
        return self.evidence

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

    # Test 1 — all core components available
    def test_quality_reports_all_core_components_available(self):
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
    
        quality = profile.extras["intelligence_quality"]
    
        assert quality["components_expected"] == 5
        assert quality["components_available"] == 5
        assert quality["components_missing"] == 0
    
        assert quality["available_components"] == (
            "metadata",
            "entities",
            "financials",
            "signals",
            "risks",
        )
    
        assert quality["missing_components"] == ()

    # Test 2 — default objects must NOT count as extracted
    def test_quality_does_not_count_default_components_as_available(self):
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        quality = profile.extras["intelligence_quality"]
    
        assert quality["components_expected"] == 5
        assert quality["components_available"] == 0
        assert quality["components_missing"] == 5
    
        assert quality["available_components"] == ()
    
        assert quality["missing_components"] == (
            "metadata",
            "entities",
            "financials",
            "signals",
            "risks",
        )

    # Test 3 — partial extractor coverage
    def test_quality_reports_partial_component_coverage(self):
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor(
                    "metadata",
                    DocumentMetadata(
                        title="SemSure",
                        confidence=0.90,
                    ),
                ),
                FakeExtractor(
                    "entities",
                    InvestmentEntities(
                        company_name="SemSure",
                        confidence=0.80,
                    ),
                ),
            ),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        quality = profile.extras["intelligence_quality"]
    
        assert quality["components_expected"] == 5
        assert quality["components_available"] == 2
        assert quality["components_missing"] == 3
    
        assert quality["available_components"] == (
            "metadata",
            "entities",
        )
    
        assert quality["missing_components"] == (
            "financials",
            "signals",
            "risks",
        )
            

    # Test 4 — confidence metadata is preserved
    def test_quality_preserves_component_confidence(self):
        metadata = DocumentMetadata(
            title="Test",
            confidence=0.90,
        )
    
        entities = InvestmentEntities(
            confidence=0.80,
        )
    
        financials = FinancialMetrics(
            confidence=0.70,
        )
    
        signals = InvestmentSignals(
            confidence=0.60,
        )
    
        risks = RiskAssessment(
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
    
        quality = profile.extras["intelligence_quality"]
    
        assert quality["component_confidence"] == {
            "metadata": 0.90,
            "entities": 0.80,
            "financials": 0.70,
            "signals": 0.60,
            "risks": 0.50,
        }

    # Test 5 — unsupported extractor
    def test_unsupported_extractor_is_skipped(self):
        extractor = FakeExtractor(
            "metadata",
            DocumentMetadata(title="Should Not Run"),
            supported=False,
        )
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(extractor),
        )
    
        document = self.create_document()
    
        profile = service.analyze(
            document,
            self.create_chunks(),
        )
    
        assert extractor.called is False
        assert profile.metadata.title == document.title
    
        quality = profile.extras["intelligence_quality"]
    
        assert quality["components_available"] == 0
        assert quality["components_missing"] == 5

    def test_no_extractor_evidence_returns_empty_tuple(self):
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor(
                    "metadata",
                    DocumentMetadata(title="Test"),
                ),
            ),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        assert profile.evidence == ()
    
    def test_extractor_evidence_is_aggregated(self):
        evidence = IntelligenceEvidence(
            extractor="financials",
            field_name="revenue",
            chunk_index=0,
            start_offset=0,
            end_offset=13,
            text="Investment OS",
        )
    
        extractor = FakeExtractor(
            "financials",
            FinancialMetrics(),
            evidence=(evidence,),
        )
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(extractor),
        )
    
        document = self.create_document()
        chunks = self.create_chunks()
    
        profile = service.analyze(
            document,
            chunks,
        )
    
        assert profile.evidence == (evidence,)
    
    def test_evidence_from_multiple_extractors_is_aggregated(self):
        metadata_evidence = IntelligenceEvidence(
            extractor="metadata",
            field_name="title",
            chunk_index=0,
            start_offset=0,
            end_offset=13,
            text="Investment OS",
        )
    
        financial_evidence = IntelligenceEvidence(
            extractor="financials",
            field_name="valuation",
            chunk_index=0,
            start_offset=0,
            end_offset=13,
            text="Investment OS",
        )
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(
                FakeExtractor(
                    "metadata",
                    DocumentMetadata(title="Test"),
                    evidence=(metadata_evidence,),
                ),
                FakeExtractor(
                    "financials",
                    FinancialMetrics(),
                    evidence=(financial_evidence,),
                ),
            ),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        assert profile.evidence == (
            metadata_evidence,
            financial_evidence,
        )
    
    def test_evidence_extractor_receives_same_inputs_and_result(self):
        result = FinancialMetrics()
    
        evidence = IntelligenceEvidence(
            extractor="financials",
            text="Investment OS",
        )
    
        extractor = FakeExtractor(
            "financials",
            result,
            evidence=(evidence,),
        )
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(extractor),
        )
    
        document = self.create_document()
        chunks = self.create_chunks()
    
        profile = service.analyze(
            document,
            chunks,
        )
    
        assert extractor.evidence_called is True
        assert extractor.evidence_document is document
        assert extractor.evidence_chunks is chunks
        assert extractor.evidence_result is result
        assert profile.evidence == (evidence,)
    
    def test_unsupported_extractor_does_not_generate_evidence(self):
        evidence = IntelligenceEvidence(
            extractor="metadata",
            field_name="title",
            text="Should Not Run",
        )
    
        extractor = FakeExtractor(
            "metadata",
            DocumentMetadata(title="Should Not Run"),
            supported=False,
            evidence=(evidence,),
        )
    
        service = InvestmentIntelligenceService(
            factory=FakeIntelligenceFactory(extractor),
        )
    
        profile = service.analyze(
            self.create_document(),
            self.create_chunks(),
        )
    
        assert extractor.called is False
        assert extractor.evidence_called is False
        assert profile.evidence == ()
    
