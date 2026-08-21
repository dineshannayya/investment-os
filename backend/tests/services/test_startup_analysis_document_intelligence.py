from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.intelligence.models import (
    IntelligenceEvidence,
    InvestmentEntities,
    InvestmentProfile,
    InvestmentSignals,
    FinancialMetrics as IntelligenceFinancialMetrics,
)

from app.schemas.analysis import (
    AnalysisEvidence,
    CompanyAnalysis,
    FinancialAnalysis,
    StartupAnalysisInput,
)
from app.services.startup_analysis_document_intelligence import (
    StartupAnalysisDocumentIntelligenceService,
)


def make_input():
    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example Startup",
        ),
    )


def make_profile(
    *,
    document_id=None,
    products=(),
    technologies=(),
    markets=(),
    geographies=(),
    business_models=(),
    revenue=None,
    ebitda=None,
    margin=None,
    burn_rate=None,
    runway_months=None,
    evidence=(),
):
    return InvestmentProfile(
        document_id=document_id or uuid4(),
        metadata=Mock(),
        entities=InvestmentEntities(
            products=products,
            technologies=technologies,
        ),
        financials=IntelligenceFinancialMetrics(
            revenue=revenue,
            ebitda=ebitda,
            margin=margin,
            burn_rate=burn_rate,
            runway_months=runway_months,
        ),
        signals=InvestmentSignals(
            markets=markets,
            geographies=geographies,
            business_models=business_models,
        ),
        evidence=evidence,
    )


def make_service(
    *,
    profiles=(),
):
    processing = Mock()
    intelligence = Mock()

    profiles = list(profiles)

    processing.process_and_chunk.side_effect = [
        (Mock(), [Mock()])
        for _ in profiles
    ]

    intelligence.analyze.side_effect = profiles

    service = StartupAnalysisDocumentIntelligenceService(
        document_processing=processing,
        intelligence=intelligence,
    )

    return service, processing, intelligence


def test_no_documents_returns_original_input():
    startup = SimpleNamespace(
        id=uuid4(),
        documents=[],
    )

    analysis_input = make_input()

    service, processing, intelligence = make_service()

    result = service.enrich(
        startup,
        analysis_input,
    )

    assert result == analysis_input
    processing.process_and_chunk.assert_not_called()
    intelligence.analyze.assert_not_called()


def test_single_document_enriches_financials():
    document_id = uuid4()

    profile = make_profile(
        document_id=document_id,
        revenue=Decimal("10000000"),
        ebitda=Decimal("2000000"),
        margin=Decimal("20"),
        burn_rate=Decimal("500000"),
        runway_months=18,
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, processing, intelligence = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    assert result.financials == FinancialAnalysis(
        revenue=Decimal("10000000"),
        ebitda=Decimal("2000000"),
        ebitda_margin=Decimal("20"),
        burn_rate=Decimal("500000"),
        runway_months=18,
    )

    processing.process_and_chunk.assert_called_once_with(
        document_id,
    )

    intelligence.analyze.assert_called_once()


def test_single_document_enriches_product_market_business_model():
    document_id = uuid4()

    profile = make_profile(
        document_id=document_id,
        products=("EdgeVision",),
        technologies=("AI", "Computer Vision"),
        markets=("Surveillance",),
        geographies=("India",),
        business_models=("B2B SaaS",),
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    assert result.product is not None
    assert result.product.product_description == "EdgeVision"
    assert result.product.technology == (
        "AI, Computer Vision"
    )

    assert result.market is not None
    assert result.market.market_description == "Surveillance"
    assert result.market.geographic_market == "India"

    assert result.business_model is not None
    assert result.business_model.business_model == "B2B SaaS"


def test_multiple_documents_merge_unique_values():
    profile_one = make_profile(
        products=("Product A", "Product B"),
        technologies=("AI",),
        markets=("India",),
        business_models=("B2B",),
        revenue=Decimal("100"),
    )

    profile_two = make_profile(
        products=("Product B", "Product C"),
        technologies=("AI", "Vision"),
        markets=("Europe",),
        business_models=("B2B", "Subscription"),
        revenue=Decimal("200"),
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=profile_one.document_id),
            SimpleNamespace(id=profile_two.document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[
            profile_one,
            profile_two,
        ],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    assert result.product.product_description == (
        "Product A, Product B, Product C"
    )

    assert result.product.technology == (
        "AI, Vision"
    )

    assert result.market.market_description == (
        "India, Europe"
    )

    assert result.business_model.business_model == (
        "B2B, Subscription"
    )

    # First non-None document value wins for scalar facts.
    assert result.financials.revenue == Decimal("100")


def test_existing_input_fields_are_preserved():
    analysis_input = make_input()

    analysis_input = analysis_input.model_copy(
        update={
            "financials": FinancialAnalysis(
                revenue=Decimal("999"),
            ),
        },
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[],
    )

    service, _, _ = make_service()

    result = service.enrich(
        startup,
        analysis_input,
    )

    assert result.financials.revenue == Decimal("999")


def test_evidence_is_preserved_and_not_generated():
    analysis_input = make_input()

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[],
    )

    service, _, _ = make_service()

    result = service.enrich(
        startup,
        analysis_input,
    )

    assert result.evidence == []

def test_document_evidence_is_converted_and_merged_into_analysis_input():
    document_id = uuid4()

    intelligence_evidence = (
        IntelligenceEvidence(
            extractor="financial_extractor",
            field_name="revenue",
            chunk_index=2,
            start_offset=10,
            end_offset=32,
            text="Revenue: ₹2.68 crore",
            metadata={
                "page": 3,
                "section": "Financials",
            },
        ),
    )

    profile = make_profile(
        document_id=document_id,
        evidence=intelligence_evidence,
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    assert len(result.evidence) == 1

    evidence = result.evidence[0]

    assert isinstance(evidence, AnalysisEvidence)
    assert evidence.document_id == document_id
    assert evidence.page == 3
    assert evidence.section == "Financials"
    assert evidence.source_text == "Revenue: ₹2.68 crore"
    assert evidence.confidence == Decimal("1.0")


def test_existing_and_document_evidence_are_merged():
    document_id = uuid4()


    existing_evidence = (
        AnalysisEvidence(
            document_id=None,
            section="Company",
            source_text="RestoMart",
            confidence=Decimal("1.0"),
        ),
    )
    
    document_evidence = (
        AnalysisEvidence(
            document_id=document_id,
            section="Financials",
            source_text="Revenue: ₹2.68 crore",
            confidence=Decimal("0.95"),
        ),
    )

    analysis_input = make_input().model_copy(
        update={
            "evidence": list(existing_evidence),
        }
    )

    profile = make_profile(
        document_id=document_id,
        evidence=document_evidence,
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        analysis_input,
    )

    assert result.evidence == [
        *existing_evidence,
        *document_evidence,
    ]

def test_document_evidence_uses_field_name_when_section_missing():
    document_id = uuid4()

    intelligence_evidence = (
        IntelligenceEvidence(
            extractor="financial_extractor",
            field_name="revenue",
            chunk_index=2,
            start_offset=10,
            end_offset=32,
            text="Revenue: ₹2.68 crore",
            metadata={
                "page": 3,
            },
        ),
    )

    profile = make_profile(
        document_id=document_id,
        evidence=intelligence_evidence,
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    evidence = result.evidence[0]

    assert evidence.section == "revenue"


def test_existing_and_document_evidence_are_merged():
    document_id = uuid4()

    existing_evidence = (
        AnalysisEvidence(
            document_id=None,
            page=None,
            section="Company",
            source_text="RestoMart",
            confidence=Decimal("1.0"),
        ),
    )

    document_evidence = (
        IntelligenceEvidence(
            extractor="financial_extractor",
            field_name="revenue",
            chunk_index=1,
            start_offset=0,
            end_offset=25,
            text="Revenue: ₹2.68 crore",
            metadata={
                "page": 2,
                "section": "Financials",
            },
        ),
    )

    profile = make_profile(
        document_id=document_id,
        evidence=document_evidence,
    )

    analysis_input = make_input().model_copy(
        update={
            "evidence": list(existing_evidence),
        }
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        analysis_input,
    )

    assert len(result.evidence) == 2

    assert result.evidence[0] == existing_evidence[0]

    assert result.evidence[1].document_id == document_id
    assert result.evidence[1].page == 2
    assert result.evidence[1].section == "Financials"
    assert result.evidence[1].source_text == "Revenue: ₹2.68 crore"


def test_multiple_document_evidence_items_are_preserved():
    document_id = uuid4()

    intelligence_evidence = (
        IntelligenceEvidence(
            extractor="financial_extractor",
            field_name="revenue",
            chunk_index=1,
            text="Revenue: ₹2.68 crore",
            metadata={"page": 2, "section": "Financials"},
        ),
        IntelligenceEvidence(
            extractor="financial_extractor",
            field_name="raise_amount",
            chunk_index=2,
            text="Seeking INR 2 crore",
            metadata={"page": 4, "section": "Fundraising"},
        ),
    )

    profile = make_profile(
        document_id=document_id,
        evidence=intelligence_evidence,
    )

    startup = SimpleNamespace(
        id=uuid4(),
        documents=[
            SimpleNamespace(id=document_id),
        ],
    )

    service, _, _ = make_service(
        profiles=[profile],
    )

    result = service.enrich(
        startup,
        make_input(),
    )

    assert len(result.evidence) == 2

    assert result.evidence[0].section == "Financials"
    assert result.evidence[0].source_text == "Revenue: ₹2.68 crore"

    assert result.evidence[1].section == "Fundraising"
    assert result.evidence[1].source_text == "Seeking INR 2 crore"
