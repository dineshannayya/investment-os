"""
Tests for RiskExtractor.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.risk import RiskExtractor
from app.processors import DocumentContent


class TestRiskExtractor:
    """Tests for RiskExtractor."""

    @staticmethod
    def create_document(
        text: str,
        title: str = "Risk Assessment",
    ) -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title=title,
            text=text,
            page_count=1,
            metadata={},
        )

    @staticmethod
    def create_chunks(text: str) -> list[Chunk]:
        return [
            Chunk(
                index=0,
                text=text,
                start_offset=0,
                end_offset=len(text),
                metadata={},
            )
        ]

    # ==========================================================
    # Properties
    # ==========================================================

    def test_name(self):
        extractor = RiskExtractor()

        assert extractor.name == "risks"

    def test_supports(self):
        extractor = RiskExtractor()

        assert extractor.supports(
            self.create_document("Prototype startup")
        )

    # ==========================================================
    # Founder Risks
    # ==========================================================

    def test_extract_solo_founder(self):
        text = "The company has a solo founder."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "solo_founder" in risks.founder_risks

    def test_extract_first_time_founder(self):
        text = "This is a first-time founder."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "first_time_founder" in risks.founder_risks

    # ==========================================================
    # Financial Risks
    # ==========================================================

    def test_extract_high_burn(self):
        text = "Current burn rate is very high."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "high_burn" in risks.financial_risks

    def test_extract_pre_revenue(self):
        text = "The startup is pre-revenue."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "pre_revenue" in risks.financial_risks

    # ==========================================================
    # Execution Risks
    # ==========================================================

    def test_extract_prototype_stage(self):
        text = "Currently at prototype stage."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "prototype_stage" in risks.execution_risks

    def test_extract_hiring_dependency(self):
        text = "Growth depends on key hires."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "hiring_dependency" in risks.execution_risks

    # ==========================================================
    # Market Risks
    # ==========================================================

    def test_extract_competition(self):
        text = "Operating in a highly competitive market."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "high_competition" in risks.market_risks

    def test_extract_customer_concentration(self):
        text = "Revenue depends on a single customer."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "customer_concentration" in risks.market_risks

    # ==========================================================
    # Technology Risks
    # ==========================================================

    def test_extract_unproven_technology(self):
        text = "The solution uses experimental technology."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "unproven_technology" in risks.technology_risks

    def test_extract_manufacturing_dependency(self):
        text = "Production depends on a manufacturing partner."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "manufacturing_dependency" in risks.technology_risks

    # ==========================================================
    # Legal Risks
    # ==========================================================

    def test_extract_patent_pending(self):
        text = "Patent pending."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "patent_pending" in risks.legal_risks

    def test_extract_regulatory_approval(self):
        text = "FDA regulatory approval is required."

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "regulatory_approval" in risks.legal_risks

    # ==========================================================
    # Combined
    # ==========================================================

    def test_complete_document(self):
        text = """
Solo founder.

Pre-revenue startup.

Prototype completed.

Strong competition.

Manufacturing partner required.

Patent pending.
"""

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert "solo_founder" in risks.founder_risks

        assert "pre_revenue" in risks.financial_risks

        assert "prototype_stage" in risks.execution_risks

        assert "high_competition" in risks.market_risks

        assert "manufacturing_dependency" in risks.technology_risks

        assert "patent_pending" in risks.legal_risks

    # ==========================================================
    # Empty
    # ==========================================================

    def test_empty_document(self):
        risks = RiskExtractor().extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        assert risks.founder_risks == ()
        assert risks.financial_risks == ()
        assert risks.execution_risks == ()
        assert risks.market_risks == ()
        assert risks.technology_risks == ()
        assert risks.legal_risks == ()

    # ==========================================================
    # Confidence
    # ==========================================================

    def test_confidence_range(self):
        text = """
Solo founder.

Pre-revenue.

Prototype.
"""

        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert 0.0 <= risks.confidence <= 1.0

    def test_confidence_increases(self):
        extractor = RiskExtractor()

        empty = extractor.extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        full = extractor.extract(
            self.create_document(
                """
Solo founder.

Pre-revenue.

Prototype.

Competitive market.

Patent pending.
"""
            ),
            self.create_chunks(
                """
Solo founder.

Pre-revenue.

Prototype.

Competitive market.

Patent pending.
"""
            ),
        )

        assert full.confidence > empty.confidence

    # Duplicate risk detection
    def test_duplicate_risk(self):
        text = """
Prototype stage.

Prototype completed.

Proof of concept.
"""
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert risks.execution_risks == ("prototype_stage",)
    
    #  Multiple risks in one category
    def test_multiple_financial_risks(self):
        text = """
Pre-revenue.

High burn rate.
"""
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert "pre_revenue" in risks.financial_risks
        assert "high_burn" in risks.financial_risks
    
    # Case-insensitive matching
    def test_case_insensitive(self):
        text = """
SOLO FOUNDER

PATENT PENDING
"""
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert "solo_founder" in risks.founder_risks
        assert "patent_pending" in risks.legal_risks
    
    # 4. No false positives
    def test_no_false_positive(self):
        text = """
Growing revenue.

Experienced founding team.

Established technology.
"""
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert risks.founder_risks == ()
        assert risks.financial_risks == ()
        assert risks.execution_risks == ()
        assert risks.market_risks == ()
        assert risks.technology_risks == ()
        assert risks.legal_risks == ()
    
