"""
Tests for FinancialExtractor.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.financial import FinancialExtractor
from app.intelligence.parsers import MoneyParser
from app.processors import DocumentContent
from app.intelligence.models import IntelligenceEvidence


class TestFinancialExtractor:
    """Tests for FinancialExtractor."""

    @staticmethod
    def create_document(
        text: str,
        title: str = "Financial Document",
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

    # ==============================================================
    # Money Parser Safety
    # ==============================================================

    def test_money_parser_ignores_plain_year(self):
        occurrences = MoneyParser.find_all("FY2025 revenue: INR 12 crore.")
        assert len(occurrences) == 1
        assert occurrences[0].money.amount == Decimal("120000000")

    def test_money_parser_requires_currency_or_unit(self):
        assert MoneyParser.find_all("2025 50 18 100") == []

    def test_money_parser_accepts_unit_without_currency(self):
        occurrences = MoneyParser.find_all("Revenue 12 crore.")
        assert len(occurrences) == 1
        assert occurrences[0].money.amount == Decimal("120000000")

    def test_money_parser_does_not_parse_months_as_money(self):
        occurrences = MoneyParser.find_all("Runway is 18 months.")
        assert occurrences == []

    # ==============================================================
    # Properties
    # ==============================================================

    def test_name(self):
        extractor = FinancialExtractor()

        assert extractor.name == "financials"

    def test_supports(self):
        extractor = FinancialExtractor()

        document = self.create_document(
            "Raised ₹5 Cr."
        )

        assert extractor.supports(document)

    # ==============================================================
    # Raise Amount
    # ==============================================================

    def test_extract_raise_amount(self):
        text = "Company raised ₹5 Cr in Seed funding."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.raise_amount == Decimal("50000000")
        assert metrics.currency == "INR"

    # ==============================================================
    # Valuation
    # ==============================================================

    def test_extract_valuation(self):
        text = "Current valuation is ₹25 Cr."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.valuation == Decimal("250000000")

    # ==============================================================
    # Revenue
    # ==============================================================

    def test_extract_revenue(self):
        text = "Annual revenue reached ₹8 Cr."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.revenue == Decimal("80000000")

    # ==============================================================
    # ARR
    # ==============================================================

    def test_extract_arr(self):
        text = "ARR is ₹12 Cr."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.arr == Decimal("120000000")

    # ==============================================================
    # Burn Rate
    # ==============================================================

    def test_extract_burn_rate(self):
        text = "Monthly burn rate is ₹50 Lakhs."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.burn_rate == Decimal("5000000")

    # ==============================================================
    # Percentage
    # ==============================================================

    def test_extract_margin(self):
        text = "EBITDA margin is 32.5%."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.margin == Decimal("32.5")

    def test_unrelated_percentage_is_not_ebitda_margin(self):
        text = "Revenue grew 95% YoY."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.margin is None

    def test_ownership_percentage_is_not_ebitda_margin(self):
        text = "Founder ownership is 95%."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.margin is None

    def test_ebitda_amount_without_margin_does_not_create_margin(self):
        text = "EBITDA was ₹2 Cr."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.ebitda == Decimal("20000000")
        assert metrics.margin is None

    def test_extract_margin_when_percentage_precedes_ebitda_margin(self):
        text = "The company achieved a 32.5% EBITDA margin."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.margin == Decimal("32.5")

    def test_extract_margin_with_space_before_percent(self):
        text = "EBITDA margin: 32.5 %."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.margin == Decimal("32.5")

    def test_extract_evidence_for_ebitda_margin(self):
        text = "EBITDA margin is 32.5%."

        document = self.create_document(text)
        chunks = self.create_chunks(text)

        extractor = FinancialExtractor()

        metrics = extractor.extract(
            document,
            chunks,
        )

        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )

        margin_evidence = [
            item
            for item in evidence
            if item.field_name == "margin"
        ]

        assert len(margin_evidence) == 1

        item = margin_evidence[0]

        assert isinstance(item, IntelligenceEvidence)
        assert item.extractor == "financials"
        assert item.field_name == "margin"
        assert item.chunk_index == 0

        assert text[
            item.start_offset:item.end_offset
        ] == "32.5%"

        assert item.text == text

    def test_no_margin_evidence_for_unrelated_percentage(self):
        text = "Revenue grew 95% YoY."

        document = self.create_document(text)
        chunks = self.create_chunks(text)

        extractor = FinancialExtractor()

        metrics = extractor.extract(
            document,
            chunks,
        )

        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )

        assert metrics.margin is None
        assert not any(
            item.field_name == "margin"
            for item in evidence
        )

    # ==============================================================
    # Runway
    # ==============================================================

    def test_extract_runway(self):
        text = "Runway is 18 months."

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.runway_months == 18

    # ==============================================================
    # Combined
    # ==============================================================

    def test_extract_complete_document(self):
        text = """
Raised ₹5 Cr in Seed round.

Current valuation ₹25 Cr.

Annual revenue ₹8 Cr.

EBITDA ₹2 Cr.

ARR ₹10 Cr.

Monthly burn rate ₹40 Lakhs.

Runway 24 months.

EBITDA margin 28%.
"""

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.raise_amount == Decimal("50000000")
        assert metrics.valuation == Decimal("250000000")
        assert metrics.revenue == Decimal("80000000")
        assert metrics.ebitda == Decimal("20000000")
        assert metrics.arr == Decimal("100000000")
        assert metrics.burn_rate == Decimal("4000000")

        assert metrics.margin == Decimal("28")
        assert metrics.runway_months == 24
        assert metrics.currency == "INR"

    # ==============================================================
    # Missing Values
    # ==============================================================

    def test_empty_document(self):
        metrics = FinancialExtractor().extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        assert metrics.raise_amount is None
        assert metrics.valuation is None
        assert metrics.revenue is None
        assert metrics.ebitda is None
        assert metrics.arr is None
        assert metrics.burn_rate is None
        assert metrics.margin is None
        assert metrics.runway_months is None

    # ==============================================================
    # Currency
    # ==============================================================

    def test_currency_from_first_metric(self):
        text = """
Raised USD 2 Million.

Valuation USD 12 Million.
"""

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.currency == "USD"

    # ==============================================================
    # Confidence
    # ==============================================================

    def test_confidence_range(self):
        text = """
Raised ₹5 Cr.

Valuation ₹25 Cr.
"""

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert 0.0 <= metrics.confidence <= 1.0

    # ==============================================================
    # Same Amount, Different Metrics
    # ==============================================================
    def test_confidence_increases(self):
        extractor = FinancialExtractor()

        empty = extractor.extract(
            self.create_document(""),
            self.create_chunks(""),
        )

        full = extractor.extract(
            self.create_document(
                """
Raised ₹5 Cr.

Valuation ₹25 Cr.

Revenue ₹10 Cr.

ARR ₹12 Cr.

Runway 24 months.

EBITDA margin 30%.
"""
            ),
            self.create_chunks(
                """
Raised ₹5 Cr.

Valuation ₹25 Cr.

Revenue ₹10 Cr.

ARR ₹12 Cr.

Runway 24 months.

EBITDA margin 30%.
"""
            ),
        )

        assert full.confidence > empty.confidence

    # ==============================================================
    # Duplicate Metric Policy
    # ==============================================================
    def test_same_amount_different_metrics(self):
        text = """
    Raised ₹5 Cr in Seed funding.
    
    Current valuation ₹5 Cr.
    """
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.raise_amount == Decimal("50000000")
        assert metrics.valuation == Decimal("50000000")
    
        assert metrics.revenue is None
        assert metrics.arr is None

    # ==============================================================
    # False Positive / Context Isolation
    # ==============================================================

    def test_year_is_not_parsed_as_revenue(self):
        text = "FY2025 revenue: INR 12 crore."
        metrics = FinancialExtractor().extract(self.create_document(text), self.create_chunks(text))
        assert metrics.revenue == Decimal("120000000")

    def test_cash_balance_does_not_become_burn_rate(self):
        text = """
Cash balance: INR 8 crore.
Monthly burn: INR 0.5 crore.
"""
        metrics = FinancialExtractor().extract(self.create_document(text), self.create_chunks(text))
        assert metrics.burn_rate == Decimal("5000000")

    def test_extract_ebitda(self):
        text = "FY2025 EBITDA: INR 2 crore."
        metrics = FinancialExtractor().extract(self.create_document(text), self.create_chunks(text))
        assert metrics.ebitda == Decimal("20000000")

    def test_adjacent_financial_metrics_do_not_cross_contaminate(self):
        text = """
Revenue: INR 12 crore.
EBITDA: INR 2 crore.
Cash balance: INR 8 crore.
Monthly burn: INR 0.5 crore.
"""
        metrics = FinancialExtractor().extract(self.create_document(text), self.create_chunks(text))
        assert metrics.revenue == Decimal("120000000")
        assert metrics.ebitda == Decimal("20000000")
        assert metrics.burn_rate == Decimal("5000000")

    # ==============================================================
    # Mixed Currency Documents    
    # ==============================================================
    def test_first_metric_wins(self):
        text = """
    Revenue ₹5 Cr.
    
    Revenue ₹8 Cr.
    """
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.revenue == Decimal("50000000")
    
    def test_first_currency_is_retained(self):
        text = """
    Raised USD 2 Million.
    
    Revenue ₹5 Cr.
    """
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.raise_amount == Decimal("2000000")
        assert metrics.revenue == Decimal("50000000")
    
        assert metrics.currency == "USD"
    
    # ==============================================================
    # Ignore Unrelated Money
    # ==============================================================
    def test_ignore_unclassified_money(self):
        text = """
    Cash balance ₹10 Cr.
    
    Office rent ₹20 Lakhs.
    """
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.raise_amount is None
        assert metrics.valuation is None
        assert metrics.revenue is None
        assert metrics.arr is None
        assert metrics.burn_rate is None
   
    # ==============================================================
    # Evidence / Provenance
    # ==============================================================
    
    def test_extract_evidence_for_revenue(self):
        text = "Annual revenue reached ₹8 Cr."
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert len(evidence) == 1
    
        item = evidence[0]
    
        assert isinstance(item, IntelligenceEvidence)
        assert item.extractor == "financials"
        assert item.field_name == "revenue"
        assert item.chunk_index == 0
        assert item.start_offset == text.index("₹8 Cr.")
        assert text[
            item.start_offset:item.end_offset
        ] == "₹8 Cr"

        assert item.text == text

    def test_extract_evidence_for_multiple_metrics(self):
        text = """
Raised ₹5 Cr in Seed round.
Current valuation ₹25 Cr.
Annual revenue ₹8 Cr.
EBITDA ₹2 Cr.
ARR ₹10 Cr.
Monthly burn rate ₹40 Lakhs.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert [item.field_name for item in evidence] == [
            "raise_amount",
            "valuation",
            "revenue",
            "ebitda",
            "arr",
            "burn_rate",
        ]
    
        assert all(
            item.extractor == "financials"
            for item in evidence
        )
    
        assert all(
            item.chunk_index == 0
            for item in evidence
        )
    
    def test_evidence_offsets_match_source_text(self):
        text = (
            "Company raised ₹5 Cr in Seed funding."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert len(evidence) == 1
    
        item = evidence[0]
    
        assert text[
            item.start_offset:item.end_offset
        ] == "₹5 Cr"
    
    def test_evidence_contains_source_line(self):
        text = (
            "Company raised ₹5 Cr in Seed funding."
        )
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert evidence[0].text == text
    
    def test_evidence_follows_first_match_policy(self):
        text = """
Revenue ₹5 Cr.
Revenue ₹8 Cr.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        revenue_evidence = [
            item
            for item in evidence
            if item.field_name == "revenue"
        ]
    
        assert len(revenue_evidence) == 1
        assert revenue_evidence[0].text == (
            "Revenue ₹5 Cr."
        )
    
    def test_no_evidence_for_unclassified_money(self):
        text = """
Cash balance ₹10 Cr.
Office rent ₹20 Lakhs.
"""
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert evidence == ()
    
    def test_no_evidence_for_empty_document(self):
        document = self.create_document("")
        chunks = self.create_chunks("")
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert evidence == ()
    
    def test_evidence_resolves_containing_chunk(self):
        first = "Company overview.\n"
        second = "Annual revenue ₹8 Cr."
    
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
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert len(evidence) == 1
        assert evidence[0].field_name == "revenue"
        assert evidence[0].chunk_index == 1

    def test_evidence_distinguishes_occurrence_from_context(self):
        text = "Annual revenue reached ₹8 Cr."
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(document, chunks)
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        assert len(evidence) == 1
    
        item = evidence[0]
    
        assert text[
            item.start_offset:item.end_offset
        ] == "₹8 Cr"
    
        assert item.text == (
            "Annual revenue reached ₹8 Cr."
        )
         

    def test_unrelated_percentages_do_not_become_ebitda_margin(self):
        text = """
        Founder ownership: 95%.
        Revenue growth: 40%.
        Customer retention: 92%.
        EBITDA: ₹2 Cr.
        """

        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )

        assert metrics.ebitda == Decimal("20000000")
        assert metrics.margin is None

    def test_extracts_pre_money_valuation(self):
        text = "Pre-money valuation: ₹10 Cr."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.valuation == Decimal("100000000")
        assert metrics.valuation_type.value == "pre_money"

    def test_extracts_post_money_valuation(self):
        text = "Post-money valuation: ₹12 Cr."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.valuation == Decimal("120000000")
        assert metrics.valuation_type.value == "post_money"

    def test_extracts_valuation_cap(self):
        text = "The SAFE has a valuation cap of ₹15 Cr."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.valuation == Decimal("150000000")
        assert metrics.valuation_type.value == "valuation_cap"

    def test_extracts_unspecified_valuation(self):
        text = "The company valuation is ₹9.25 Cr."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.valuation == Decimal("92500000")
        assert metrics.valuation_type.value == "unspecified"    

    def test_does_not_extract_unrelated_amount_as_valuation(self):
        text = "The company raised ₹5 Cr in its latest round."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.raise_amount == Decimal("50000000")
        assert metrics.valuation is None

    def test_amount_without_valuation_context_is_not_valuation(self):
        text = "The company has ₹9.25 Cr in annual revenue."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.revenue == Decimal("92500000")
        assert metrics.valuation is None

    def test_valued_at_is_unspecified_valuation(self):
        text = "The company was valued at ₹20 Cr."
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.valuation == Decimal("200000000")
        assert metrics.valuation_type.value == "unspecified"

    def test_valuation_evidence_contains_source_and_type(self):
        text = "Post-money valuation: ₹12 Cr."
    
        document = self.create_document(text)
        chunks = self.create_chunks(text)
    
        extractor = FinancialExtractor()
    
        metrics = extractor.extract(
            document,
            chunks,
        )
    
        evidence = extractor.extract_evidence(
            document,
            chunks,
            metrics,
        )
    
        valuation_evidence = [
            item
            for item in evidence
            if item.field_name == "valuation"
        ]
    
        assert len(valuation_evidence) == 1
    
        item = valuation_evidence[0]
    
        assert item.extractor == "financials"
        assert item.field_name == "valuation"
        assert item.metadata["valuation_type"] == "post_money"
        assert "Post-money valuation" in item.text

    def test_valuation_and_other_financials_are_not_confused(self):
        text = """
        Revenue: ₹2.68 Cr.
        The company was valued at ₹9.25 Cr.
        Founder ownership is 95%.
        EBITDA: ₹2 Cr.
        """
    
        metrics = FinancialExtractor().extract(
            self.create_document(text),
            self.create_chunks(text),
        )
    
        assert metrics.revenue == Decimal("26800000")
        assert metrics.valuation == Decimal("92500000")
        assert metrics.valuation_type.value == "unspecified"
        assert metrics.ebitda == Decimal("20000000")
        assert metrics.margin is None
                
