"""
Tests for Investment Intelligence models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import uuid4

import pytest

from app.intelligence.models import (
    DocumentMetadata,
    FinancialMetrics,
    InvestmentEntities,
    InvestmentProfile,
)


# ============================================================================
# DocumentMetadata
# ============================================================================


class TestDocumentMetadata:
    """Tests for DocumentMetadata."""

    def test_create(self):
        metadata = DocumentMetadata(
            title="SemSure Pitch Deck",
            document_type="Pitch Deck",
            language="English",
            page_count=18,
            sections=("Problem", "Solution"),
            keywords=("AI", "Healthcare"),
            confidence=0.95,
        )

        assert metadata.title == "SemSure Pitch Deck"
        assert metadata.document_type == "Pitch Deck"
        assert metadata.language == "English"
        assert metadata.page_count == 18
        assert metadata.sections == ("Problem", "Solution")
        assert metadata.keywords == ("AI", "Healthcare")
        assert metadata.confidence == pytest.approx(0.95)

    def test_defaults(self):
        metadata = DocumentMetadata(title="Test")

        assert metadata.document_type is None
        assert metadata.language is None
        assert metadata.page_count == 0
        assert metadata.sections == ()
        assert metadata.keywords == ()
        assert metadata.confidence == 1.0

    def test_immutable(self):
        metadata = DocumentMetadata(title="Test")

        with pytest.raises(FrozenInstanceError):
            metadata.title = "Updated"


# ============================================================================
# InvestmentEntities
# ============================================================================


class TestInvestmentEntities:
    """Tests for InvestmentEntities."""

    def test_create(self):
        entities = InvestmentEntities(
            company_name="SemSure",
            founders=("Alice", "Bob"),
            investors=("LetsVenture",),
            accelerators=("NSRCEL",),
            locations=("Bangalore",),
            sectors=("Healthcare",),
            products=("Diagnostic Kit",),
            technologies=("AI",),
            confidence=0.90,
        )

        assert entities.company_name == "SemSure"
        assert entities.founders == ("Alice", "Bob")
        assert entities.investors == ("LetsVenture",)
        assert entities.accelerators == ("NSRCEL",)
        assert entities.locations == ("Bangalore",)
        assert entities.sectors == ("Healthcare",)
        assert entities.products == ("Diagnostic Kit",)
        assert entities.technologies == ("AI",)
        assert entities.confidence == pytest.approx(0.90)

    def test_defaults(self):
        entities = InvestmentEntities()

        assert entities.company_name is None
        assert entities.founders == ()
        assert entities.investors == ()
        assert entities.accelerators == ()
        assert entities.locations == ()
        assert entities.sectors == ()
        assert entities.products == ()
        assert entities.technologies == ()
        assert entities.confidence == 1.0

    def test_immutable(self):
        entities = InvestmentEntities()

        with pytest.raises(FrozenInstanceError):
            entities.company_name = "New Company"


# ============================================================================
# FinancialMetrics
# ============================================================================


class TestFinancialMetrics:
    """Tests for FinancialMetrics."""

    def test_create(self):
        metrics = FinancialMetrics(
            currency="INR",
            raise_amount=Decimal("55000000"),
            valuation=Decimal("240000000"),
            revenue=Decimal("12000000"),
            arr=Decimal("10000000"),
            ebitda=Decimal("1500000"),
            burn_rate=Decimal("500000"),
            runway_months=18,
            confidence=0.92,
        )

        assert metrics.currency == "INR"
        assert metrics.raise_amount == Decimal("55000000")
        assert metrics.valuation == Decimal("240000000")
        assert metrics.revenue == Decimal("12000000")
        assert metrics.arr == Decimal("10000000")
        assert metrics.ebitda == Decimal("1500000")
        assert metrics.burn_rate == Decimal("500000")
        assert metrics.runway_months == 18
        assert metrics.confidence == pytest.approx(0.92)

    def test_defaults(self):
        metrics = FinancialMetrics()

        assert metrics.currency is None
        assert metrics.raise_amount is None
        assert metrics.valuation is None
        assert metrics.revenue is None
        assert metrics.arr is None
        assert metrics.ebitda is None
        assert metrics.burn_rate is None
        assert metrics.runway_months is None
        assert metrics.confidence == 1.0

    def test_immutable(self):
        metrics = FinancialMetrics()

        with pytest.raises(FrozenInstanceError):
            metrics.currency = "USD"


# ============================================================================
# InvestmentProfile
# ============================================================================


class TestInvestmentProfile:
    """Tests for InvestmentProfile."""

    def test_create(self):
        document_id = uuid4()

        metadata = DocumentMetadata(
            title="Pitch Deck",
            page_count=20,
        )

        entities = InvestmentEntities(
            company_name="SemSure",
        )

        financials = FinancialMetrics(
            currency="INR",
            valuation=Decimal("240000000"),
        )

        profile = InvestmentProfile(
            document_id=document_id,
            metadata=metadata,
            entities=entities,
            financials=financials,
            extras={
                "source": "upload",
            },
            confidence=0.96,
        )

        assert profile.document_id == document_id
        assert profile.metadata is metadata
        assert profile.entities is entities
        assert profile.financials is financials
        assert profile.extras["source"] == "upload"
        assert profile.confidence == pytest.approx(0.96)

    def test_defaults(self):
        profile = InvestmentProfile(
            document_id=uuid4(),
            metadata=DocumentMetadata(title="Test"),
            entities=InvestmentEntities(),
            financials=FinancialMetrics(),
        )

        assert profile.extras == {}
        assert profile.confidence == 1.0

    def test_immutable(self):
        profile = InvestmentProfile(
            document_id=uuid4(),
            metadata=DocumentMetadata(title="Test"),
            entities=InvestmentEntities(),
            financials=FinancialMetrics(),
        )

        with pytest.raises(FrozenInstanceError):
            profile.confidence = 0.5

    def test_equality(self):
        document_id = uuid4()

        metadata = DocumentMetadata(title="Test")
        entities = InvestmentEntities()
        financials = FinancialMetrics()

        profile1 = InvestmentProfile(
            document_id=document_id,
            metadata=metadata,
            entities=entities,
            financials=financials,
        )

        profile2 = InvestmentProfile(
            document_id=document_id,
            metadata=metadata,
            entities=entities,
            financials=financials,
        )

        assert profile1 == profile2
