from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.financial import FinancialExtractor
from app.intelligence.models import FinancialMetrics, IntelligenceEvidence
from app.processors.base import DocumentContent


def _make_document(text: str) -> DocumentContent:
    return DocumentContent(
        document_id=uuid4(),
        text=text,
        title="RestoMart Financial Summary",
        page_count=1,
    )


def _make_chunks(document: DocumentContent) -> list[Chunk]:
    return [
        Chunk(
            index=0,
            text=document.text,
            start_offset=0,
            end_offset=len(document.text),
        )
    ]


def _extract(
    text: str,
) -> tuple[
    FinancialExtractor,
    DocumentContent,
    FinancialMetrics,
    tuple[IntelligenceEvidence, ...],
]:
    document = _make_document(text)
    chunks = _make_chunks(document)
    extractor = FinancialExtractor()

    result = extractor.extract(document, chunks)
    evidence = extractor.extract_evidence(document, chunks, result)

    return extractor, document, result, evidence


def test_financial_extractor_extracts_revenue():
    _, _, result, evidence = _extract(
        "Reported revenue: INR 2.68 crore."
    )

    assert isinstance(result, FinancialMetrics)
    assert result.revenue == Decimal("26800000")
    assert result.raise_amount is None
    assert result.valuation is None

    revenue_evidence = tuple(
        item for item in evidence if item.field_name == "revenue"
    )

    assert revenue_evidence
    for item in revenue_evidence:
        assert item.extractor == "financials"
        assert item.chunk_index == 0
        assert item.text
        assert item.start_offset is not None
        assert item.end_offset is not None


def test_financial_extractor_extracts_numeric_valuation():
    _, _, result, evidence = _extract(
        "Numeric valuation: INR 92,500,000."
    )

    assert isinstance(result, FinancialMetrics)
    assert result.valuation == Decimal("92500000")
    assert result.raise_amount is None

    valuation_evidence = tuple(
        item for item in evidence if item.field_name == "valuation"
    )

    assert len(valuation_evidence) == 1

    item = valuation_evidence[0]
    assert item.extractor == "financials"
    assert item.chunk_index == 0
    assert item.text
    assert "92,500,000" in item.text
    assert item.start_offset is not None
    assert item.end_offset is not None
    assert item.end_offset > item.start_offset
    assert item.metadata["valuation_type"] == "unspecified"


def test_financial_extractor_does_not_treat_minimum_investment_as_raise():
    _, _, result, evidence = _extract(
        "Minimum investment: INR 2 lakh."
    )

    assert result.raise_amount is None
    assert result.valuation is None
    assert result.revenue is None
    assert result.arr is None
    assert result.ebitda is None
    assert result.burn_rate is None

    assert not any(
        item.field_name == "raise_amount"
        for item in evidence
    )


def test_financial_extractor_extracts_explicit_raise_amount():
    _, _, result, evidence = _extract(
        "Target raise: INR 5 crore."
    )

    assert result.raise_amount == Decimal("50000000")

    raise_evidence = tuple(
        item for item in evidence if item.field_name == "raise_amount"
    )

    assert len(raise_evidence) == 1
    assert raise_evidence[0].extractor == "financials"
    assert raise_evidence[0].chunk_index == 0
    assert "5 crore" in raise_evidence[0].text.lower()


def test_financial_extractor_keeps_revenue_valuation_and_raise_independent():
    _, _, result, evidence = _extract(
        "Reported revenue: INR 2.68 crore.\n"
        "Numeric valuation: INR 92,500,000.\n"
        "Target raise: INR 5 crore."
    )

    assert result.revenue == Decimal("26800000")
    assert result.valuation == Decimal("92500000")
    assert result.raise_amount == Decimal("50000000")

    fields = {
        item.field_name
        for item in evidence
    }

    assert {"revenue", "valuation", "raise_amount"} <= fields

    assert all(
        item.extractor == "financials"
        for item in evidence
    )
