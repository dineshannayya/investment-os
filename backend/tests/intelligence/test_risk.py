"""
Tests for RiskExtractor.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.risk import RiskExtractor
from app.intelligence.models import IntelligenceEvidence
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

    #Test 1 — Word-boundary behavior
    def test_keyword_boundary(self):
        text = "The company has a stable financial position."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert risks.financial_risks == ()
    

    #9. Better new tests
    def test_extract_customer_concentration_explicit(self):
        text = "Revenue is highly concentrated in one customer."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "customer_concentration" in risks.market_risks
    
    # Major customer should not automatically mean concentration
    def test_major_customer_alone_is_not_customer_concentration(self):
        text = "The company has a major customer in the semiconductor industry."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "customer_concentration" not in risks.market_risks

    #10. Manufacturing false-positive test
    def test_foundry_alone_is_not_manufacturing_dependency(self):
        text = "The company manufactures its chips at a leading foundry."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "manufacturing_dependency" not in risks.technology_risks
    
    
    def test_single_foundry_dependency(self):
        text = "Production depends on a single foundry."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "manufacturing_dependency" in risks.technology_risks

    #11. Regulatory false-positive test
    def test_regulated_market_alone_is_not_regulatory_risk(self):
        text = "The company operates in a regulated market."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "regulatory_approval" not in risks.legal_risks
    
    def test_regulatory_approval_required(self):
        text = "FDA regulatory approval is required before launch."
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "regulatory_approval" in risks.legal_risks

    # 12. Production-style regression test
    def test_semiconductor_startup_risk_profile(self):
        text = """
        Risks
    
    
        The company is still validating its technology at production scale.
    
    
        Production depends on a single foundry.
    
    
        Revenue is concentrated in one major customer.
    
    
        Additional capital will be required to fund development.
    
    
        Regulatory approval is required before commercial deployment.
        """
    
    
        risks = RiskExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
    
        assert "unproven_technology" in risks.technology_risks
        assert "manufacturing_dependency" in risks.technology_risks
        assert "customer_concentration" in risks.market_risks
        assert "regulatory_approval" in risks.legal_risks

    # ==========================================================
    # Evidence / Provenance
    # ==========================================================
    # 9. Basic founder evidence
    def test_extract_evidence_for_solo_founder(self):
        text = "The company has a solo founder."
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        assert len(evidence) == 1
    
        item = evidence[0]
    
        assert isinstance(item, IntelligenceEvidence)
        assert item.extractor == "risks"
        assert item.field_name == "founder_risks"
        assert item.chunk_index == 0
    
        assert (
            text[
                item.start_offset:item.end_offset
            ].lower()
            == "solo founder"
        )
    
        assert item.text == text
    
    # 10. Evidence for multiple risk categories
    def test_extract_evidence_for_multiple_risks(self):
        text = """
Solo founder.

Pre-revenue startup.

Currently at prototype stage.

Strong competition.

Production depends on a single foundry.

Patent pending.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        assert {
            item.field_name
            for item in evidence
        } == {
            "founder_risks",
            "financial_risks",
            "execution_risks",
            "market_risks",
            "technology_risks",
            "legal_risks",
        }
    
        assert all(
            item.extractor == "risks"
            for item in evidence
        )
    
    # 11. Test duplicate risk → one evidence record
    def test_extract_evidence_deduplicates_same_risk(self):
        text = """
Prototype stage.

Prototype completed.

Proof of concept.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        prototype_evidence = [
            item
            for item in evidence
            if item.field_name == "execution_risks"
        ]
    
        assert len(prototype_evidence) == 1
        assert (
            text[
                prototype_evidence[0].start_offset:
                prototype_evidence[0].end_offset
            ].lower()
            == "prototype"
        )
    
    # 12. Test multiple risks in one category
    def test_extract_evidence_for_multiple_financial_risks(self):
        text = """
Pre-revenue.

High burn rate.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        financial_evidence = [
            item
            for item in evidence
            if item.field_name == "financial_risks"
        ]
    
        assert len(financial_evidence) == 2
    
        matched = {
            text[
                item.start_offset:item.end_offset
            ].lower()
            for item in financial_evidence
        }
    
        assert matched == {
            "pre-revenue",
            "high burn rate",
        }
    
    # 13. Test false-positive protection
    def test_no_evidence_for_false_positive_text(self):
        text = """
Growing revenue.

Experienced founding team.

Established technology.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        assert evidence == ()
    
    # 14. Test word boundaries
    def test_no_evidence_for_word_boundary_false_positive(self):
        text = "The company has a stable financial position."
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        assert evidence == ()
    
    # 15. Test customer concentration
    def test_customer_concentration_evidence(self):
        text = (
            "Revenue is highly concentrated in one customer."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        item = next(
            item
            for item in evidence
            if item.field_name == "market_risks"
        )
    
        assert (
            text[
                item.start_offset:item.end_offset
            ].lower()
            == "revenue is highly concentrated in one customer"
        )
    
        assert item.text == text
    
    # 16. Test manufacturing dependency
    def test_manufacturing_dependency_evidence(self):
        text = (
            "Production depends on a single foundry."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        item = next(
            item
            for item in evidence
            if item.field_name == "technology_risks"
        )
    
        assert (
            text[
                item.start_offset:item.end_offset
            ].lower()
            == "single foundry"
        )
    
        assert item.text == text
    
    # 17. Test regulatory approval
    def test_regulatory_approval_evidence(self):
        text = (
            "FDA regulatory approval is required before launch."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        item = next(
            item
            for item in evidence
            if item.field_name == "legal_risks"
        )
    
        assert (
            text[
                item.start_offset:item.end_offset
            ].lower()
            == "fda"
        )
    
        assert item.text == text
    
    # 18. Test chunk provenance
    def test_evidence_resolves_containing_chunk(self):
        first = "Company overview.\n"
        second = "Production depends on a single foundry.\n"
    
        text = first + second
    
        chunks = [
            Chunk(
                index=0,
                text=first,
                start_offset=0,
                end_offset=len(first),
                metadata={},
            ),
            Chunk(
                index=1,
                text=second,
                start_offset=len(first),
                end_offset=len(text),
                metadata={},
            ),
        ]
    
        document = self.create_document(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        item = next(
            item
            for item in evidence
            if item.field_name == "technology_risks"
        )
    
        assert item.chunk_index == 1
    
    # 19. Test exact match vs context
    def test_evidence_distinguishes_keyword_from_context(self):
        text = (
            "Production depends on a single foundry."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        item = next(
            item
            for item in evidence
            if item.field_name == "technology_risks"
        )
    
        assert (
            text[
                item.start_offset:item.end_offset
            ].lower()
            == "single foundry"
        )
    
        assert item.text == text
    
    # 20. Semiconductor production-style regression
    def test_semiconductor_startup_risk_evidence(self):
        text = """
The company is still validating its technology at production scale.

Production depends on a single foundry.

Revenue is concentrated in one major customer.

Regulatory approval is required before commercial deployment.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = RiskExtractor()
    
        risks = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            risks,
        )
    
        assert {
            item.field_name
            for item in evidence
        } == {
            "technology_risks",
            "market_risks",
            "legal_risks",
        }
    
        assert len(evidence) == 4
                        
