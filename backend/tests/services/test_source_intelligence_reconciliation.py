"""
Tests for source intelligence reconciliation.

These tests verify that source-supported facts are reconciled
deterministically and that material conflicts are preserved rather
than silently overwritten.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
    MarketAnalysis,
    SourceAuthority,
    SourceStatus,
    SourceValue,
    StartupAnalysisInput,
    TractionAnalysis,
)
from app.services.source_intelligence_reconciliation import (
    SourceIntelligenceReconciliationService,
)


@pytest.fixture
def service() -> SourceIntelligenceReconciliationService:
    return SourceIntelligenceReconciliationService()


@pytest.fixture
def startup_input() -> StartupAnalysisInput:
    return StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="RestoMart",
            description="B2B food-supply and restaurant procurement company",
            industry="B2B Food Supply",
            sector="Food Supply / Restaurant Technology",
            stage="early_revenue",
            founded_year=2023,
            headquarters="India",
        ),
        founders=[],
        product=None,
        market=MarketAnalysis(),
        traction=TractionAnalysis(),
        financials=FinancialAnalysis(),
        fundraising=FundraisingAnalysis(),
        business_model=None,
    )


def fact(
    field: str,
    value,
    *,
    authority: SourceAuthority,
    source_name: str,
    period: str | None = "FY25-26",
    document_id=None,
    section: str | None = None,
) -> SourceValue:
    return SourceValue(
        field=field,
        value=value,
        status=SourceStatus.FACT,
        source_document_id=document_id or uuid4(),
        source_name=source_name,
        source_authority=authority,
        period=period,
        section=section,
    )


# ---------------------------------------------------------------------------
# 1. Identical values from multiple sources
# ---------------------------------------------------------------------------


def test_identical_revenue_from_multiple_sources_is_not_a_conflict(
    service,
    startup_input,
):
    mis = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    investment_note = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
    )

    result = service.reconcile(
        startup_input,
        [mis, investment_note],
    )

    assert result.financials is not None
    assert result.financials.revenue == Decimal("24995415.44")
    assert result.source_conflicts == []


# ---------------------------------------------------------------------------
# 2. Gross sales vs net revenue
# ---------------------------------------------------------------------------


def test_gross_sales_and_net_revenue_are_separate_facts(
    service,
    startup_input,
):
    gross_sales = fact(
        "gross_sales",
        Decimal("26814564.67"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    net_revenue = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    result = service.reconcile(
        startup_input,
        [gross_sales, net_revenue],
    )

    assert result.financials is not None

    assert result.financials.gross_sales == Decimal(
        "26814564.67"
    )

    assert result.financials.revenue == Decimal(
        "24995415.44"
    )

    assert result.source_conflicts == []


# ---------------------------------------------------------------------------
# 3. EBITDA conflict
# ---------------------------------------------------------------------------


def test_conflicting_ebitda_values_are_preserved_as_conflict(
    service,
    startup_input,
):
    mis_ebitda = fact(
        "ebitda",
        Decimal("336997.88"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    investment_note_ebitda = fact(
        "ebitda",
        Decimal("844000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
    )

    result = service.reconcile(
        startup_input,
        [
            mis_ebitda,
            investment_note_ebitda,
        ],
    )

    assert result.financials is not None

    # No source should silently win.
    assert result.financials.ebitda is None

    assert len(result.source_conflicts) == 1

    conflict = result.source_conflicts[0]

    assert conflict.field == "ebitda"
    assert conflict.status == SourceStatus.CONFLICT
    assert conflict.requires_diligence is True
    assert conflict.resolution is None

    assert len(conflict.values) == 2

    values = {
        Decimal(str(value.value))
        for value in conflict.values
    }

    assert values == {
        Decimal("336997.88"),
        Decimal("844000"),
    }

    assert all(
        value.status == SourceStatus.FACT
        for value in conflict.values
    )


# ---------------------------------------------------------------------------
# 4. EBITDA margin conflict
# ---------------------------------------------------------------------------


def test_conflicting_ebitda_margins_are_preserved_as_conflict(
    service,
    startup_input,
):
    mis_margin = fact(
        "ebitda_margin",
        Decimal("0.01348"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    investment_note_margin = fact(
        "ebitda_margin",
        Decimal("0.03376"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
    )

    result = service.reconcile(
        startup_input,
        [
            mis_margin,
            investment_note_margin,
        ],
    )

    assert result.financials is not None
    assert result.financials.ebitda_margin is None

    conflicts = [
        conflict
        for conflict in result.source_conflicts
        if conflict.field == "ebitda_margin"
    ]

    assert len(conflicts) == 1

    conflict = conflicts[0]

    assert conflict.status == SourceStatus.CONFLICT
    assert conflict.requires_diligence is True

    assert {
        Decimal(str(value.value))
        for value in conflict.values
    } == {
        Decimal("0.01348"),
        Decimal("0.03376"),
    }


# ---------------------------------------------------------------------------
# 5. Formal transaction document wins over valuation-cap wording
# ---------------------------------------------------------------------------


def test_formal_pre_money_valuation_is_used_for_transaction_terms(
    service,
    startup_input,
):
    pre_money = fact(
        "pre_money_valuation",
        Decimal("92500000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
        period=None,
    )

    valuation_cap = fact(
        "valuation_cap",
        Decimal("92500000"),
        authority=SourceAuthority.INVESTOR_SUMMARY,
        source_name="restomart_fundraise.txt",
        period=None,
    )

    instrument = fact(
        "instrument",
        "CCPS",
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
        period=None,
    )

    result = service.reconcile(
        startup_input,
        [
            pre_money,
            valuation_cap,
            instrument,
        ],
    )

    assert result.fundraising is not None

    assert result.fundraising.pre_money_valuation == Decimal(
        "92500000"
    )

    assert result.fundraising.instrument == "CCPS"

    # Formal transaction terminology should prevent the
    # informal "valuation cap" terminology from becoming
    # the canonical transaction field.
    assert result.fundraising.valuation_cap is None

    # These are not competing values for the same normalized
    # transaction field, therefore no conflict is expected.
    assert result.source_conflicts == []


# ---------------------------------------------------------------------------
# 6. Projections must not populate current actual financials
# ---------------------------------------------------------------------------


def test_projection_revenue_does_not_populate_actual_revenue(
    service,
    startup_input,
):
    projected_revenue = SourceValue(
        field="revenue",
        value=Decimal("60276000"),
        status=SourceStatus.PROJECTION,
        source_document_id=uuid4(),
        source_name="restomart_3_year_projections.xlsx",
        source_authority=SourceAuthority.FINANCIAL_MODEL,
        period="FY26-27",
    )

    result = service.reconcile(
        startup_input,
        [projected_revenue],
    )

    assert result.financials is not None

    assert result.financials.revenue is None

    assert result.source_conflicts == []

    assert len(result.source_facts) == 1
    assert result.source_facts[0].status == SourceStatus.PROJECTION


# ---------------------------------------------------------------------------
# 7. Assumptions must not become actual facts
# ---------------------------------------------------------------------------


def test_assumption_does_not_populate_actual_financials(
    service,
    startup_input,
):
    order_size = SourceValue(
        field="average_order_weight_kg",
        value=Decimal("20"),
        status=SourceStatus.ASSUMPTION,
        source_document_id=uuid4(),
        source_name="restomart_3_year_projections.xlsx",
        source_authority=SourceAuthority.FINANCIAL_MODEL,
        period="FY26-27",
    )

    result = service.reconcile(
        startup_input,
        [order_size],
    )

    assert result.financials is not None
    assert result.financials.revenue is None

    assert result.source_conflicts == []

    assert result.source_facts[0].status == SourceStatus.ASSUMPTION


# ---------------------------------------------------------------------------
# 8. Traction metrics are reconciled
# ---------------------------------------------------------------------------


def test_restomart_traction_metrics_are_reconciled(
    service,
    startup_input,
):
    orders = fact(
        "orders",
        4019,
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    cac = fact(
        "customer_acquisition_cost",
        Decimal("680"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    aov = fact(
        "average_order_value",
        Decimal("6130"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    concentration = fact(
        "top_customer_concentration",
        Decimal("0.5484"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        period="Mar-26",
    )

    result = service.reconcile(
        startup_input,
        [
            orders,
            cac,
            aov,
            concentration,
        ],
    )

    assert result.traction is not None

    assert result.traction.orders == 4019
    assert result.traction.customer_acquisition_cost == Decimal(
        "680"
    )
    assert result.traction.average_order_value == Decimal(
        "6130"
    )
    assert result.traction.top_customer_concentration == Decimal(
        "0.5484"
    )


# ---------------------------------------------------------------------------
# 9. Competitors are aggregated
# ---------------------------------------------------------------------------


def test_competitors_are_aggregated_without_duplicates(
    service,
    startup_input,
):
    competitors = [
        fact(
            "competitor",
            "Zomato Hyperpure",
            authority=SourceAuthority.TRANSACTION_DOCUMENT,
            source_name="restomart_investor_note.pdf",
        ),
        fact(
            "competitor",
            "Swiggy Assure",
            authority=SourceAuthority.TRANSACTION_DOCUMENT,
            source_name="restomart_investor_note.pdf",
        ),
        fact(
            "competitor",
            "Zomato Hyperpure",
            authority=SourceAuthority.INVESTOR_SUMMARY,
            source_name="restomart_business_model.txt",
        ),
    ]

    result = service.reconcile(
        startup_input,
        competitors,
    )

    assert result.market is not None

    assert result.market.competitors == [
        "Zomato Hyperpure",
        "Swiggy Assure",
    ]


# ---------------------------------------------------------------------------
# 10. Duplicate source facts are removed
# ---------------------------------------------------------------------------


def test_duplicate_source_facts_are_deduplicated(
    service,
    startup_input,
):
    document_id = uuid4()

    first = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        document_id=document_id,
    )

    duplicate = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        document_id=document_id,
    )

    result = service.reconcile(
        startup_input,
        [first, duplicate],
    )

    assert len(result.source_facts) == 1
    assert result.source_conflicts == []

    assert result.financials is not None
    assert result.financials.revenue == Decimal(
        "24995415.44"
    )


# ---------------------------------------------------------------------------
# 11. Source authority is used when identical facts have different
#     confidence levels
# ---------------------------------------------------------------------------


def test_source_authority_is_used_for_preferred_candidate(
    service,
    startup_input,
):
    investor_summary = fact(
        "revenue",
        Decimal("25000000"),
        authority=SourceAuthority.INVESTOR_SUMMARY,
        source_name="restomart_business_model.txt",
    )

    mis = fact(
        "revenue",
        Decimal("25000000"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    result = service.reconcile(
        startup_input,
        [
            investor_summary,
            mis,
        ],
    )

    assert result.financials is not None
    assert result.financials.revenue == Decimal(
        "25000000"
    )

    assert result.source_conflicts == []


# ---------------------------------------------------------------------------
# 12. Conflict in one field must not block reconciliation of other fields
# ---------------------------------------------------------------------------


def test_conflict_does_not_block_other_financial_fields(
    service,
    startup_input,
):
    mis_ebitda = fact(
        "ebitda",
        Decimal("336997.88"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    note_ebitda = fact(
        "ebitda",
        Decimal("844000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
    )

    revenue = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    gross_margin = fact(
        "gross_margin",
        Decimal("0.1146"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    result = service.reconcile(
        startup_input,
        [
            mis_ebitda,
            note_ebitda,
            revenue,
            gross_margin,
        ],
    )

    assert result.financials is not None

    # Conflicting field remains unresolved.
    assert result.financials.ebitda is None

    # Non-conflicting fields still reconcile.
    assert result.financials.revenue == Decimal(
        "24995415.44"
    )

    assert result.financials.gross_margin == Decimal(
        "0.1146"
    )

    assert len(result.source_conflicts) == 1
    assert result.source_conflicts[0].field == "ebitda"

def test_gross_profit_reconciles(
    service,
    startup_input,
):
    gross_profit = fact(
        "gross_profit",
        Decimal("2864984.88"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    result = service.reconcile(
        startup_input,
        [gross_profit],
    )

    assert result.financials is not None
    assert result.financials.gross_profit == Decimal("2864984.88")
    assert result.source_conflicts == []


def test_fundraising_amount_and_valuation_are_reconciled(
    service,
    startup_input,
):
    raise_amount = fact(
        "raise_amount",
        Decimal("20000000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_fundraise.txt",
        period=None,
    )

    valuation = fact(
        "pre_money_valuation",
        Decimal("92500000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
        period=None,
    )

    result = service.reconcile(
        startup_input,
        [raise_amount, valuation],
    )

    assert result.fundraising is not None
    assert result.fundraising.amount_raising == Decimal("20000000")
    assert result.fundraising.pre_money_valuation == Decimal("92500000")
    assert result.source_conflicts == []


def test_conflicting_pre_money_valuation_requires_diligence(
    service,
    startup_input,
):
    formal = fact(
        "pre_money_valuation",
        Decimal("92500000"),
        authority=SourceAuthority.TRANSACTION_DOCUMENT,
        source_name="restomart_investor_note.pdf",
        period=None,
    )

    summary = fact(
        "pre_money_valuation",
        Decimal("100000000"),
        authority=SourceAuthority.INVESTOR_SUMMARY,
        source_name="restomart_investor_brief.txt",
        period=None,
    )

    result = service.reconcile(
        startup_input,
        [formal, summary],
    )

    assert result.fundraising is not None
    assert result.fundraising.pre_money_valuation is None

    conflicts = [
        c
        for c in result.source_conflicts
        if c.field == "pre_money_valuation"
    ]

    assert len(conflicts) == 1
    assert conflicts[0].status == SourceStatus.CONFLICT
    assert conflicts[0].requires_diligence is True

def test_actual_revenue_is_not_conflicted_by_projection(
    service,
    startup_input,
):
    actual = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        period="FY25-26",
    )

    projection = SourceValue(
        field="revenue",
        value=Decimal("60276000"),
        status=SourceStatus.PROJECTION,
        source_document_id=uuid4(),
        source_name="restomart_3_year_projections.xlsx",
        source_authority=SourceAuthority.FINANCIAL_MODEL,
        period="FY26-27",
    )

    result = service.reconcile(
        startup_input,
        [actual, projection],
    )

    assert result.financials is not None
    assert result.financials.revenue == Decimal("24995415.44")
    assert result.source_conflicts == []


def test_actual_ebitda_is_not_conflicted_by_projection(
    service,
    startup_input,
):
    actual = fact(
        "ebitda",
        Decimal("336997.88"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        period="FY25-26",
    )

    projection = SourceValue(
        field="ebitda",
        value=Decimal("5000000"),
        status=SourceStatus.PROJECTION,
        source_document_id=uuid4(),
        source_name="restomart_3_year_projections.xlsx",
        source_authority=SourceAuthority.FINANCIAL_MODEL,
        period="FY26-27",
    )

    result = service.reconcile(
        startup_input,
        [actual, projection],
    )

    assert result.financials is not None
    assert result.financials.ebitda == Decimal("336997.88")
    assert result.source_conflicts == []


def test_multiple_market_descriptions_are_aggregated(
    service,
    startup_input,
):
    facts = [
        fact(
            "market_description",
            "B2B food supply",
            authority=SourceAuthority.MIS,
            source_name="restomart_mis.xlsx",
        ),
        fact(
            "market_description",
            "restaurant procurement",
            authority=SourceAuthority.INVESTOR_SUMMARY,
            source_name="restomart_business_model.txt",
        ),
    ]

    result = service.reconcile(
        startup_input,
        facts,
    )

    assert result.market is not None
    assert result.market.market_description is not None
    assert "B2B food supply" in result.market.market_description
    assert "restaurant procurement" in result.market.market_description
    assert result.source_conflicts == []

def test_multiple_business_model_descriptions_are_aggregated(
    service,
    startup_input,
):
    facts = [
        fact(
            "business_model",
            "B2B",
            authority=SourceAuthority.MIS,
            source_name="restomart_mis.xlsx",
        ),
        fact(
            "business_model",
            "marketplace",
            authority=SourceAuthority.INVESTOR_SUMMARY,
            source_name="restomart_business_model.txt",
        ),
    ]

    result = service.reconcile(
        startup_input,
        facts,
    )

    assert result.business_model is not None
    assert "B2B" in result.business_model.business_model
    assert "marketplace" in result.business_model.business_model
    assert result.source_conflicts == []

def test_missing_source_values_are_ignored(
    service,
    startup_input,
):
    revenue = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
    )

    result = service.reconcile(
        startup_input,
        [revenue],
    )

    assert result.financials is not None
    assert result.financials.revenue == Decimal("24995415.44")
    assert result.source_conflicts == []

def test_source_provenance_is_preserved(
    service,
    startup_input,
):
    document_id = uuid4()

    source = fact(
        "revenue",
        Decimal("24995415.44"),
        authority=SourceAuthority.MIS,
        source_name="restomart_mis.xlsx",
        document_id=document_id,
        section="financials",
    )

    result = service.reconcile(
        startup_input,
        [source],
    )

    assert len(result.source_facts) == 1

    persisted = result.source_facts[0]

    assert persisted.source_document_id == document_id
    assert persisted.source_name == "restomart_mis.xlsx"
    assert persisted.source_authority == SourceAuthority.MIS
    assert persisted.section == "financials"

