"""
Tests for Investment Intelligence base extractor.
"""

from __future__ import annotations

from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    IntelligenceEvidence,
    InvestmentEntities,
)


class FakeExtractor(
    IntelligenceExtractor[InvestmentEntities]
):
    """Concrete extractor for testing the base contract."""

    @property
    def name(self) -> str:
        return "fake"

    def extract(
        self,
        document,
        chunks,
    ) -> InvestmentEntities:
        return InvestmentEntities(
            company_name="Test Startup",
        )


class EvidenceExtractor(
    IntelligenceExtractor[InvestmentEntities]
):
    """Concrete extractor implementing evidence."""

    @property
    def name(self) -> str:
        return "entities"

    def extract(
        self,
        document,
        chunks,
    ) -> InvestmentEntities:
        return InvestmentEntities(
            company_name="Test Startup",
        )

    def extract_evidence(
        self,
        document,
        chunks,
        result,
    ) -> tuple[IntelligenceEvidence, ...]:
        return (
            IntelligenceEvidence(
                extractor=self.name,
                field_name="company_name",
                chunk_index=0,
                start_offset=0,
                end_offset=12,
                text="Test Startup",
            ),
        )


class TestIntelligenceExtractor:
    """Tests for IntelligenceExtractor."""

    def test_name_and_extract_contract(self):
        extractor = FakeExtractor()

        result = extractor.extract(
            document=None,
            chunks=[],
        )

        assert extractor.name == "fake"
        assert result.company_name == "Test Startup"

    def test_supports_defaults_to_true(self):
        extractor = FakeExtractor()

        assert extractor.supports(None) is True

    def test_extract_evidence_defaults_to_empty_tuple(self):
        extractor = FakeExtractor()

        evidence = extractor.extract_evidence(
            document=None,
            chunks=[],
            result=InvestmentEntities(
                company_name="Test Startup",
            ),
        )

        assert evidence == ()

    def test_extract_evidence_can_be_overridden(self):
        extractor = EvidenceExtractor()

        result = extractor.extract(
            document=None,
            chunks=[],
        )

        evidence = extractor.extract_evidence(
            document=None,
            chunks=[],
            result=result,
        )

        assert len(evidence) == 1
        assert evidence[0].extractor == "entities"
        assert evidence[0].field_name == "company_name"
        assert evidence[0].chunk_index == 0
        assert evidence[0].text == "Test Startup"
