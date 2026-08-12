"""
Tests for FinancialExtractor.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.financial import FinancialExtractor
from app.processors import DocumentContent


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

Margin 30%.
"""
            ),
            self.create_chunks(
                """
Raised ₹5 Cr.

Valuation ₹25 Cr.

Revenue ₹10 Cr.

ARR ₹12 Cr.

Runway 24 months.

Margin 30%.
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
    
