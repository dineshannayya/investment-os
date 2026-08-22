from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.chunking.base import Chunk
from app.intelligence.models import InvestmentProfile
from app.processors.base import DocumentContent
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)
from app.services.startup_analysis_application import (
    create_intelligence_factory,
)


# ============================================================================
# Test fixtures
# ============================================================================


def _make_document(
    *,
    text: str,
    title: str = "RestoMart Financial Summary",
) -> DocumentContent:
    """Create deterministic production DocumentContent for handshake tests."""

    document_id = uuid4()

    return DocumentContent(
        document_id=document_id,
        text=text,
        title=title,
        page_count=1,
    )


def _make_chunks(
    document: DocumentContent,
) -> list[Chunk]:
    """
    Create deterministic chunks matching the DocumentContent contract.

    This test intentionally uses a single explicit chunk rather than
    TextChunker so that failures remain localized to the
    DocumentContent -> InvestmentProfile handshake.
    """

    return [
        Chunk(
            index=0,
            text=document.text,
            start_offset=0,
            end_offset=len(document.text),
        )
    ]


def _make_service() -> InvestmentIntelligenceService:
    """Create InvestmentIntelligenceService using the production factory."""

    return InvestmentIntelligenceService(
        factory=create_intelligence_factory(),
    )


# ============================================================================
# C.7.7.6.2.A — Production factory handshake
# ============================================================================


def test_production_intelligence_factory_registers_expected_extractors():
    """
    Verify that the production intelligence factory registers all
    five expected core intelligence extractors in the expected order.
    """

    factory = create_intelligence_factory()

    assert [
        extractor.name
        for extractor in factory.extractors
    ] == [
        "metadata",
        "entities",
        "financials",
        "signals",
        "risks",
    ]


# ============================================================================
# C.7.7.6.2.B — DocumentContent -> Chunk[] handshake
# ============================================================================


def test_document_content_chunk_contract_is_preserved():
    """
    Verify that the chunks supplied to InvestmentIntelligenceService
    represent the complete source DocumentContent without offset drift.
    """

    document = _make_document(
        text=(
            "RestoMart is a B2B food-supply company. "
            "Reported revenue: INR 2.68 crore. "
            "Numeric valuation: INR 92,500,000."
        )
    )

    chunks = _make_chunks(document)

    assert chunks

    chunk = chunks[0]

    assert chunk.index == 0
    assert chunk.text == document.text
    assert chunk.start_offset == 0
    assert chunk.end_offset == len(document.text)

    # The chunk offsets must describe the complete source document.
    assert (
        document.text[
            chunk.start_offset : chunk.end_offset
        ]
        == chunk.text
    )


# ============================================================================
# C.7.7.6.2.C — DocumentContent -> InvestmentProfile handshake
# ============================================================================


def test_investment_intelligence_builds_profile():
    """
    Verify the production DocumentContent -> InvestmentProfile handshake.
    """

    document = _make_document(
        text=(
            "RestoMart is a B2B food-supply company. "
            "Reported revenue: INR 2.68 crore. "
            "Numeric valuation: INR 92,500,000."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    assert isinstance(profile, InvestmentProfile)

    # ------------------------------------------------------------------
    # Document identity
    # ------------------------------------------------------------------

    assert profile.document_id == document.document_id

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    assert profile.metadata.title == document.title
    assert profile.metadata.page_count == document.page_count

    # ------------------------------------------------------------------
    # Core intelligence components
    # ------------------------------------------------------------------

    assert profile.entities is not None
    assert profile.financials is not None
    assert profile.signals is not None
    assert profile.risks is not None

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    assert isinstance(profile.evidence, tuple)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    assert 0.0 <= profile.confidence <= 1.0

    # ------------------------------------------------------------------
    # Quality metadata
    # ------------------------------------------------------------------

    assert "intelligence_quality" in profile.extras


# ============================================================================
# C.7.7.6.2.C.1 — Intelligence quality handshake
# ============================================================================


def test_investment_intelligence_reports_complete_component_quality():
    """
    Verify that the production InvestmentProfile reports the availability
    of all five core intelligence components.
    """

    document = _make_document(
        text=(
            "RestoMart is a B2B food-supply company. "
            "Reported revenue: INR 2.68 crore. "
            "Customer concentration is a market risk. "
            "The company operates in India."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    quality = profile.extras.get(
        "intelligence_quality"
    )

    assert quality is not None

    assert quality["components_expected"] == 5
    assert quality["components_available"] == 5
    assert quality["components_missing"] == 0

    assert set(
        quality["available_components"]
    ) == {
        "metadata",
        "entities",
        "financials",
        "signals",
        "risks",
    }

    assert quality["missing_components"] == ()

    assert set(
        quality["component_confidence"]
    ) == {
        "metadata",
        "entities",
        "financials",
        "signals",
        "risks",
    }


# ============================================================================
# C.7.7.6.2.D — InvestmentProfile -> evidence/provenance handshake
# ============================================================================


def test_investment_intelligence_preserves_extractor_evidence():
    """
    Verify that extracted financial values and their evidence survive
    the InvestmentIntelligenceService boundary.
    """

    document = _make_document(
        text=(
            "Reported revenue: INR 2.68 crore. "
            "Numeric valuation: INR 92,500,000."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    assert profile.financials.revenue == Decimal(
        "26800000"
    )

    revenue_evidence = tuple(
        evidence
        for evidence in profile.evidence
        if evidence.field_name == "revenue"
    )

    assert revenue_evidence

    for evidence in revenue_evidence:
        assert evidence.extractor == "financials"
        assert evidence.field_name == "revenue"
        assert evidence.text
        assert evidence.chunk_index == 0

        # Provenance offsets must exist.
        assert evidence.start_offset is not None
        assert evidence.end_offset is not None

        # Offsets must be valid for the source document.
        assert 0 <= evidence.start_offset
        assert evidence.start_offset < evidence.end_offset
        assert evidence.end_offset <= len(document.text)

        # Evidence text must correspond to the original source range.
        source_text = document.text[
            evidence.start_offset : evidence.end_offset
        ]

        assert source_text
        assert source_text.lower() in document.text.lower()


# ============================================================================
# C.7.7.6.2.D.1 — Complete evidence provenance contract
# ============================================================================


def test_investment_intelligence_evidence_is_bound_to_source_document():
    """
    Verify that every emitted evidence record can be traced back to the
    exact source DocumentContent used by the production intelligence service.
    """

    document = _make_document(
        text=(
            "RestoMart is a B2B food-supply company. "
            "Reported revenue: INR 2.68 crore. "
            "The company operates in India. "
            "Customer concentration is a market risk."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    assert profile.evidence

    for evidence in profile.evidence:
        # Every evidence item must identify its producer.
        assert evidence.extractor

        # Every evidence item produced by the current extractors should
        # identify the semantic field it supports.
        assert evidence.field_name

        # Evidence must contain actual source text.
        assert evidence.text

        # Evidence must identify its originating chunk.
        assert evidence.chunk_index is not None
        assert evidence.chunk_index == 0

        # Source offsets are required for provenance validation.
        assert evidence.start_offset is not None
        assert evidence.end_offset is not None

        assert 0 <= evidence.start_offset
        assert evidence.start_offset < evidence.end_offset
        assert evidence.end_offset <= len(document.text)

        source_text = document.text[
            evidence.start_offset : evidence.end_offset
        ]

        assert source_text.lower() in document.text.lower()


# ============================================================================
# C.7.7.6.2.E — Cross-component financial handshake
# ============================================================================


def test_financial_values_and_currency_survive_profile_handshake():
    """
    Verify that canonical financial extraction survives the complete
    FinancialExtractor -> InvestmentProfile boundary.

    This specifically protects the currency behavior fixed in the
    FinancialExtractor contract: an explicit fundraising currency must
    remain the document currency when later metrics use another currency.
    """

    document = _make_document(
        text=(
            "Reported revenue: INR 2.68 crore. "
            "The company is raising USD 2 Million."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    # Revenue must survive the extractor -> profile boundary.
    assert profile.financials.revenue == Decimal(
        "26800000"
    )

    # Fundraising amount must survive the same boundary.
    assert profile.financials.raise_amount == Decimal(
        "2000000"
    )

    # The explicit fundraising currency must remain canonical.
    assert profile.financials.currency == "USD"


# ============================================================================
# C.7.7.6.2.F — Profile/document identity consistency
# ============================================================================


def test_profile_identity_is_consistent_with_document_and_evidence():
    """
    Verify the identity portion of the production handshake.

    The InvestmentProfile must belong to the exact DocumentContent that
    entered InvestmentIntelligenceService, and all evidence must point
    into that same document.
    """

    document = _make_document(
        text=(
            "RestoMart is a B2B food-supply company. "
            "Reported revenue: INR 2.68 crore."
        )
    )

    chunks = _make_chunks(document)

    service = _make_service()

    profile = service.analyze(
        document,
        chunks,
    )

    assert profile.document_id == document.document_id

    for evidence in profile.evidence:
        assert evidence.start_offset is not None
        assert evidence.end_offset is not None
