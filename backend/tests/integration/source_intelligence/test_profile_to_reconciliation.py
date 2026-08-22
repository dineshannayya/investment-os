"""
Production handshake integration tests:

    InvestmentProfile
        -> StartupAnalysisDocumentIntelligenceService
        -> SourceValue[]
        -> SourceIntelligenceReconciliationService
        -> StartupAnalysisInput

These tests intentionally do NOT invoke:
    - Qwen
    - real document processing
    - filesystem/storage
    - document processors

The document-processing and intelligence boundaries are replaced with
small deterministic fakes. The production mapping and reconciliation
services remain real.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.chunking.base import Chunk
from app.intelligence.models import (
    DocumentMetadata,
    FinancialMetrics as IntelligenceFinancialMetrics,
    InvestmentEntities,
    InvestmentProfile,
    InvestmentSignals,
    RiskAssessment,
)
from app.processors.base import DocumentContent
from app.schemas.analysis import (
    CompanyAnalysis,
    SourceAuthority,
    SourceStatus,
    StartupAnalysisInput,
)
from app.services.source_intelligence_reconciliation import (
    SourceIntelligenceReconciliationService,
)
from app.services.startup_analysis_document_intelligence import (
    StartupAnalysisDocumentIntelligenceService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _document(
    document_id: UUID,
    *,
    title: str,
    document_type: str = "FINANCIAL_MODEL",
):
    """
    Build the smallest document-like object required by the production
    StartupAnalysisDocumentIntelligenceService.
    """
    return SimpleNamespace(
        id=document_id,
        title=title,
        type=document_type,
    )


def _content(document_id: UUID) -> DocumentContent:
    """Build deterministic processed document content."""
    return DocumentContent(
        document_id=document_id,
        text="Synthetic integration-test document.",
        title="Synthetic document",
        page_count=1,
    )


def _chunks() -> list[Chunk]:
    """Build deterministic chunks for the fake processing boundary."""
    return [
        Chunk(
            index=0,
            text="Synthetic integration-test document.",
            start_offset=0,
            end_offset=37,
        )
    ]


def _profile(
    document_id: UUID,
    *,
    title: str,
    document_type: str = "FINANCIAL_MODEL",
    revenue: Decimal | None = None,
    raise_amount: Decimal | None = None,
    valuation: Decimal | None = None,
    runway_months: int | None = None,
    business_models: tuple[str, ...] = (),
    markets: tuple[str, ...] = (),
    geographies: tuple[str, ...] = (),
    confidence: Decimal = Decimal("0.95"),
) -> InvestmentProfile:
    """
    Construct a production-shaped InvestmentProfile.

    This is intentionally an InvestmentProfile rather than SourceValue so
    that the test exercises the real Profile -> SourceValue mapping.
    """
    return InvestmentProfile(
        document_id=document_id,
        metadata=DocumentMetadata(
            title=title,
            document_type=document_type,
            page_count=1,
        ),
        entities=InvestmentEntities(),
        financials=IntelligenceFinancialMetrics(
            currency="INR",
            revenue=revenue,
            raise_amount=raise_amount,
            valuation=valuation,
            runway_months=runway_months,
        ),
        signals=InvestmentSignals(
            business_models=business_models,
            markets=markets,
            geographies=geographies,
        ),
        risks=RiskAssessment(),
        evidence=(),
        extras={},
        confidence=float(confidence),
    )


class FakeDocumentProcessingService:
    """
    Deterministic replacement for DocumentProcessingService.

    The production service still receives and processes the returned
    DocumentContent through the real StartupAnalysisDocumentIntelligenceService.
    """

    def __init__(self) -> None:
        self.calls: list[UUID] = []

    def process_and_chunk(
        self,
        document_id: UUID,
    ) -> tuple[DocumentContent, list[Chunk]]:
        self.calls.append(document_id)
        return _content(document_id), _chunks()


class FakeInvestmentIntelligenceService:
    """
    Deterministic replacement for InvestmentIntelligenceService.

    It returns pre-built InvestmentProfiles, allowing the test to exercise
    the real Profile -> SourceValue -> reconciliation path.
    """

    def __init__(
        self,
        profiles: dict[UUID, InvestmentProfile],
    ) -> None:
        self._profiles = profiles
        self.calls: list[UUID] = []

    def analyze(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentProfile:
        self.calls.append(document.document_id)
        return self._profiles[document.document_id]


class RecordingReconciliationService:
    """
    Spy around the real reconciliation service.

    The delegate remains the production implementation. The spy only records
    the exact SourceValue objects crossing the handshake boundary.
    """

    def __init__(
        self,
        delegate: SourceIntelligenceReconciliationService,
    ) -> None:
        self._delegate = delegate
        self.received_facts: list = []
        self.received_analysis_input: StartupAnalysisInput | None = None

    def reconcile(
        self,
        analysis_input: StartupAnalysisInput,
        source_facts,
    ) -> StartupAnalysisInput:
        self.received_analysis_input = analysis_input
        self.received_facts = list(source_facts)

        return self._delegate.reconcile(
            analysis_input,
            source_facts,
        )


def _startup(
    *,
    documents: list,
):
    """
    Build a minimal startup aggregate suitable for enrich().
    """
    startup_id = uuid4()

    return SimpleNamespace(
        id=startup_id,
        name="RestoMart",
        documents=documents,
    )


def _analysis_input() -> StartupAnalysisInput:
    """
    Minimal canonical input entering document intelligence.
    """
    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="RestoMart",
        ),
    )


def _build_service(
    profiles: dict[UUID, InvestmentProfile],
):
    """
    Build the production document-intelligence service with only external
    document-processing/intelligence boundaries replaced.
    """
    document_processing = FakeDocumentProcessingService()
    intelligence = FakeInvestmentIntelligenceService(profiles)

    reconciliation = RecordingReconciliationService(
        SourceIntelligenceReconciliationService()
    )

    service = StartupAnalysisDocumentIntelligenceService(
        document_processing=document_processing,
        intelligence=intelligence,
        reconciliation=reconciliation,
    )

    return (
        service,
        document_processing,
        intelligence,
        reconciliation,
    )


def _facts_by_field(
    reconciliation: RecordingReconciliationService,
) -> dict[str, list]:
    """
    Group SourceValue objects crossing the Profile -> Reconciliation boundary.
    """
    result: dict[str, list] = {}

    for fact in reconciliation.received_facts:
        result.setdefault(fact.field, []).append(fact)

    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_profile_financial_facts_reach_reconciliation() -> None:
    """
    InvestmentProfile financial fields must become SourceValue objects and
    reach the real reconciliation service with provenance intact.
    """
    document_id = uuid4()

    document = _document(
        document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
    )

    profile = _profile(
        document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
        revenue=Decimal("26800000"),
        raise_amount=Decimal("50000000"),
        valuation=Decimal("92500000"),
        runway_months=24,
    )

    (
        service,
        _document_processing,
        _intelligence,
        reconciliation,
    ) = _build_service(
        {document_id: profile}
    )

    startup = _startup(documents=[document])
    analysis_input = _analysis_input()

    enriched = service.enrich(
        startup,
        analysis_input,
    )

    facts = _facts_by_field(reconciliation)

    assert facts["revenue"][0].value == Decimal("26800000")
    assert facts["raise_amount"][0].value == Decimal("50000000")
    assert facts["valuation"][0].value == Decimal("92500000")
    assert facts["runway_months"][0].value == 24

    for field in (
        "revenue",
        "raise_amount",
        "valuation",
        "runway_months",
    ):
        fact = facts[field][0]

        assert fact.status == SourceStatus.FACT
        assert fact.source_document_id == document_id
        assert fact.source_name == "RestoMart Financial Summary"
        assert fact.source_authority == SourceAuthority.FINANCIAL_MODEL

    assert enriched.financials is not None
    assert enriched.financials.revenue == Decimal("26800000")
    assert enriched.financials.runway_months == 24


def test_profile_raise_amount_reaches_canonical_amount_raising() -> None:
    """
    Validate the important schema alias handshake:

        InvestmentProfile.financials.raise_amount
            -> SourceValue(field="raise_amount")
            -> reconciliation
            -> FundraisingAnalysis.amount_raising
    """
    document_id = uuid4()

    document = _document(
        document_id,
        title="RestoMart Fundraising Information",
        document_type="FINANCIAL_MODEL",
    )

    profile = _profile(
        document_id,
        title="RestoMart Fundraising Information",
        document_type="FINANCIAL_MODEL",
        raise_amount=Decimal("50000000"),
    )

    (
        service,
        _document_processing,
        _intelligence,
        reconciliation,
    ) = _build_service(
        {document_id: profile}
    )

    startup = _startup(documents=[document])
    analysis_input = _analysis_input()

    enriched = service.enrich(
        startup,
        analysis_input,
    )

    facts = _facts_by_field(reconciliation)

    assert "raise_amount" in facts
    assert len(facts["raise_amount"]) == 1
    assert facts["raise_amount"][0].value == Decimal("50000000")

    assert enriched.fundraising is not None
    assert (
        enriched.fundraising.amount_raising
        == Decimal("50000000")
    )

    assert not any(
        conflict.field == "amount_raising"
        for conflict in enriched.source_conflicts
    )


def test_two_profiles_with_same_fact_do_not_conflict() -> None:
    """
    Multiple documents agreeing on the same fact must not produce a
    material source conflict.
    """
    financial_document_id = uuid4()
    investor_document_id = uuid4()

    financial_document = _document(
        financial_document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
    )

    investor_document = _document(
        investor_document_id,
        title="RestoMart Investor Brief",
        document_type="OTHER",
    )

    financial_profile = _profile(
        financial_document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
        revenue=Decimal("26800000"),
    )

    investor_profile = _profile(
        investor_document_id,
        title="RestoMart Investor Brief",
        document_type="OTHER",
        revenue=Decimal("26800000"),
    )

    (
        service,
        _document_processing,
        _intelligence,
        reconciliation,
    ) = _build_service(
        {
            financial_document_id: financial_profile,
            investor_document_id: investor_profile,
        }
    )

    startup = _startup(
        documents=[
            financial_document,
            investor_document,
        ]
    )

    enriched = service.enrich(
        startup,
        _analysis_input(),
    )

    facts = _facts_by_field(reconciliation)

    assert len(facts["revenue"]) == 2
    assert {
        fact.value
        for fact in facts["revenue"]
    } == {
        Decimal("26800000")
    }

    assert enriched.financials is not None
    assert enriched.financials.revenue == Decimal("26800000")

    assert not any(
        conflict.field == "revenue"
        for conflict in enriched.source_conflicts
    )


def test_two_profiles_with_conflicting_facts_require_diligence() -> None:
    """
    Conflicting FACT values from separate source documents must survive
    the Profile -> SourceValue boundary and become a reconciliation conflict.

    The reconciliation layer must not silently choose one value.
    """
    financial_document_id = uuid4()
    investor_document_id = uuid4()

    financial_document = _document(
        financial_document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
    )

    investor_document = _document(
        investor_document_id,
        title="RestoMart Investor Brief",
        document_type="OTHER",
    )

    financial_profile = _profile(
        financial_document_id,
        title="RestoMart Financial Summary",
        document_type="FINANCIAL_MODEL",
        revenue=Decimal("26800000"),
    )

    investor_profile = _profile(
        investor_document_id,
        title="RestoMart Investor Brief",
        document_type="OTHER",
        revenue=Decimal("30000000"),
    )

    (
        service,
        _document_processing,
        _intelligence,
        reconciliation,
    ) = _build_service(
        {
            financial_document_id: financial_profile,
            investor_document_id: investor_profile,
        }
    )

    startup = _startup(
        documents=[
            financial_document,
            investor_document,
        ]
    )

    enriched = service.enrich(
        startup,
        _analysis_input(),
    )

    facts = _facts_by_field(reconciliation)

    assert len(facts["revenue"]) == 2
    assert {
        fact.value
        for fact in facts["revenue"]
    } == {
        Decimal("26800000"),
        Decimal("30000000"),
    }

    revenue_conflicts = [
        conflict
        for conflict in enriched.source_conflicts
        if conflict.field == "revenue"
    ]

    assert len(revenue_conflicts) == 1

    conflict = revenue_conflicts[0]

    assert conflict.status == SourceStatus.CONFLICT
    assert conflict.requires_diligence is True
    assert len(conflict.values) == 2

    assert enriched.financials is not None

    # A material conflict must not be silently resolved to one source.
    assert enriched.financials.revenue is None


# ---------------------------------------------------------------------------
# Optional signal handshake
# ---------------------------------------------------------------------------


def test_profile_signal_facts_reach_reconciliation() -> None:
    """
    Validate the signal-side Profile -> SourceValue handshake:

        business_models -> business_model
        markets        -> market_description
        geographies    -> geographic_market
    """
    document_id = uuid4()

    document = _document(
        document_id,
        title="RestoMart Business Model",
        document_type="BUSINESS_PLAN",
    )

    profile = _profile(
        document_id,
        title="RestoMart Business Model",
        document_type="BUSINESS_PLAN",
        business_models=("b2b",),
        markets=("restaurant procurement",),
        geographies=("India",),
    )

    (
        service,
        _document_processing,
        _intelligence,
        reconciliation,
    ) = _build_service(
        {document_id: profile}
    )

    startup = _startup(documents=[document])

    enriched = service.enrich(
        startup,
        _analysis_input(),
    )

    facts = _facts_by_field(reconciliation)

    assert facts["business_model"][0].value == "b2b"
    assert (
        facts["market_description"][0].value
        == "restaurant procurement"
    )
    assert facts["geographic_market"][0].value == "India"

    assert enriched.business_model is not None
    assert enriched.business_model.business_model == "b2b"

    assert enriched.market is not None
    assert (
        enriched.market.market_description
        == "restaurant procurement"
    )
    assert enriched.market.geographic_market == "India"
