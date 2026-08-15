"""Tests for startup analysis schemas."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.analysis import (
    AnalysisEvidence,
    BusinessModelAnalysis,
    CompanyAnalysis,
    FinancialAnalysis,
    FounderAnalysis,
    FundraisingAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupAnalysis,
    StartupAnalysisInput,
    StartupAnalysisResult,
    TractionAnalysis,
    FinancialMetrics,
)

# ---------------------------------------------------------------------------
# CompanyAnalysis
# ---------------------------------------------------------------------------


def test_company_analysis_minimal():
    result = CompanyAnalysis(name="Example Startup")

    assert result.name == "Example Startup"
    assert result.description is None
    assert result.industry is None
    assert result.stage is None
    assert result.founded_year is None


def test_company_analysis_full():
    result = CompanyAnalysis(
        name="Example Startup",
        description="AI platform",
        industry="Technology",
        sector="Enterprise Software",
        stage="Seed",
        founded_year=2024,
        headquarters="Bengaluru, India",
    )

    assert result.name == "Example Startup"
    assert result.industry == "Technology"
    assert result.founded_year == 2024


@pytest.mark.parametrize("year", [1799, 2101])
def test_company_analysis_rejects_invalid_founded_year(year):
    with pytest.raises(ValidationError):
        CompanyAnalysis(
            name="Example Startup",
            founded_year=year,
        )


def test_analysis_schema_strips_string_whitespace():
    result = CompanyAnalysis(
        name="  Example Startup  ",
        industry="  Technology ",
    )

    assert result.name == "Example Startup"
    assert result.industry == "Technology"


# ---------------------------------------------------------------------------
# FounderAnalysis
# ---------------------------------------------------------------------------


def test_founder_analysis_defaults():
    result = FounderAnalysis(name="Founder One")

    assert result.name == "Founder One"
    assert result.previous_startups is None
    assert result.previous_exits is None
    assert result.analysis_notes is None


def test_founder_analysis_full():
    founder_id = uuid4()

    result = FounderAnalysis(
        founder_id=founder_id,
        name="Founder One",
        role="CEO",
        background="Engineering",
        relevant_experience="10 years in semiconductor industry",
        previous_startups=2,
        previous_exits=1,
        analysis_notes="Strong domain experience",
    )

    assert result.founder_id == founder_id
    assert result.previous_startups == 2
    assert result.previous_exits == 1
    assert result.analysis_notes == "Strong domain experience"


@pytest.mark.parametrize(
    "field",
    ["previous_startups", "previous_exits"],
)
def test_founder_analysis_rejects_negative_counts(field):
    with pytest.raises(ValidationError):
        FounderAnalysis(
            name="Founder One",
            **{field: -1},
        )


# ---------------------------------------------------------------------------
# ProductAnalysis
# ---------------------------------------------------------------------------


def test_product_analysis_defaults():
    result = ProductAnalysis()

    assert result.problem is None
    assert result.solution is None
    assert result.product_description is None
    assert result.target_customer is None
    assert result.differentiation is None


def test_product_analysis_full():
    result = ProductAnalysis(
        problem="Manual workflow",
        solution="AI-powered automation",
        product_description="AI workflow platform",
        target_customer="SMEs",
        value_proposition="Reduce processing time",
        product_stage="Production",
        technology="LLM",
        differentiation="Domain-specific automation",
    )

    assert result.problem == "Manual workflow"
    assert result.solution == "AI-powered automation"
    assert result.target_customer == "SMEs"
    assert result.product_stage == "Production"


# ---------------------------------------------------------------------------
# MarketAnalysis
# ---------------------------------------------------------------------------


def test_market_analysis_defaults():
    result = MarketAnalysis()

    assert result.market_description is None
    assert result.tam is None
    assert result.sam is None
    assert result.som is None
    assert result.competitors == []


def test_market_analysis_accepts_values():
    result = MarketAnalysis(
        market_description="Enterprise AI market",
        tam=Decimal("1000000000"),
        sam=Decimal("500000000"),
        som=Decimal("100000000"),
        market_growth_rate=Decimal("25.5"),
        geographic_market="India",
        competitors=["Company A", "Company B"],
    )

    assert result.tam == Decimal("1000000000")
    assert result.sam == Decimal("500000000")
    assert result.som == Decimal("100000000")
    assert result.market_growth_rate == Decimal("25.5")
    assert result.competitors == ["Company A", "Company B"]


@pytest.mark.parametrize("field", ["tam", "sam", "som"])
def test_market_analysis_rejects_negative_market_size(field):
    with pytest.raises(ValidationError):
        MarketAnalysis(**{field: Decimal("-1")})


# ---------------------------------------------------------------------------
# TractionAnalysis
# ---------------------------------------------------------------------------


def test_traction_analysis_defaults():
    result = TractionAnalysis()

    assert result.revenue is None
    assert result.revenue_growth_yoy is None
    assert result.customers is None
    assert result.paying_customers is None
    assert result.active_users is None
    assert result.repeat_customer_rate is None


def test_traction_analysis_accepts_values():
    result = TractionAnalysis(
        revenue=Decimal("10000000"),
        revenue_growth_yoy=Decimal("40"),
        customers=100,
        paying_customers=80,
        active_users=500,
        repeat_customer_rate=Decimal("65"),
        key_traction_notes="Strong customer growth",
    )

    assert result.revenue == Decimal("10000000")
    assert result.revenue_growth_yoy == Decimal("40")
    assert result.customers == 100
    assert result.paying_customers == 80
    assert result.active_users == 500


@pytest.mark.parametrize(
    "field",
    ["revenue", "customers", "paying_customers", "active_users"],
)
def test_traction_analysis_rejects_negative_non_negative_fields(field):
    with pytest.raises(ValidationError):
        TractionAnalysis(**{field: Decimal("-1")})


# ---------------------------------------------------------------------------
# FinancialAnalysis
# ---------------------------------------------------------------------------


def test_financial_analysis_defaults():
    result = FinancialAnalysis()

    assert result.revenue is None
    assert result.ebitda is None
    assert result.cash is None
    assert result.debt is None
    assert result.burn_rate is None
    assert result.runway_months is None


def test_financial_analysis_accepts_values():
    result = FinancialAnalysis(
        revenue=Decimal("100000000"),
        revenue_growth_yoy=Decimal("40"),
        gross_profit=Decimal("50000000"),
        gross_margin=Decimal("50"),
        ebitda=Decimal("20000000"),
        ebitda_margin=Decimal("20"),
        net_profit=Decimal("10000000"),
        cash=Decimal("50000000"),
        debt=Decimal("10000000"),
        burn_rate=Decimal("2000000"),
        runway_months=Decimal("25"),
    )

    assert result.revenue == Decimal("100000000")
    assert result.ebitda == Decimal("20000000")
    assert result.ebitda_margin == Decimal("20")
    assert result.runway_months == Decimal("25")


@pytest.mark.parametrize(
    "field",
    [
        "revenue",
        "cash",
        "debt",
        "burn_rate",
        "runway_months",
    ],
)
def test_financial_analysis_rejects_negative_non_negative_fields(field):
    with pytest.raises(ValidationError):
        FinancialAnalysis(**{field: Decimal("-1")})


# ---------------------------------------------------------------------------
# FundraisingAnalysis
# ---------------------------------------------------------------------------


def test_fundraising_analysis_defaults():
    result = FundraisingAnalysis()

    assert result.current_round is None
    assert result.amount_raising is None
    assert result.amount_raised is None
    assert result.pre_money_valuation is None
    assert result.post_money_valuation is None
    assert result.valuation_cap is None
    assert result.instrument is None
    assert result.investor_commitments is None


def test_fundraising_analysis_accepts_values():
    result = FundraisingAnalysis(
        current_round="Pre-Seed",
        amount_raising=Decimal("50000000"),
        amount_raised=Decimal("30000000"),
        pre_money_valuation=Decimal("200000000"),
        post_money_valuation=Decimal("250000000"),
        valuation_cap=Decimal("240000000"),
        instrument="CCD",
        investor_commitments=Decimal("30000000"),
    )

    assert result.current_round == "Pre-Seed"
    assert result.amount_raising == Decimal("50000000")
    assert result.amount_raised == Decimal("30000000")
    assert result.instrument == "CCD"


@pytest.mark.parametrize(
    "field",
    [
        "amount_raising",
        "amount_raised",
        "pre_money_valuation",
        "post_money_valuation",
        "valuation_cap",
        "investor_commitments",
    ],
)
def test_fundraising_analysis_rejects_negative_values(field):
    with pytest.raises(ValidationError):
        FundraisingAnalysis(**{field: Decimal("-1")})


# ---------------------------------------------------------------------------
# BusinessModelAnalysis
# ---------------------------------------------------------------------------


def test_business_model_analysis_defaults():
    result = BusinessModelAnalysis()

    assert result.business_model is None
    assert result.revenue_streams == []
    assert result.pricing_model is None
    assert result.gross_margin is None
    assert result.customer_acquisition_cost is None
    assert result.lifetime_value is None
    assert result.ltv_to_cac is None


def test_business_model_analysis_accepts_values():
    result = BusinessModelAnalysis(
        business_model="B2B SaaS",
        revenue_streams=["Subscription", "Usage"],
        pricing_model="Annual subscription",
        gross_margin=Decimal("75"),
        customer_acquisition_cost=Decimal("10000"),
        lifetime_value=Decimal("50000"),
        ltv_to_cac=Decimal("5"),
    )

    assert result.business_model == "B2B SaaS"
    assert result.revenue_streams == ["Subscription", "Usage"]
    assert result.ltv_to_cac == Decimal("5")


@pytest.mark.parametrize(
    "field",
    [
        "customer_acquisition_cost",
        "lifetime_value",
        "ltv_to_cac",
    ],
)
def test_business_model_analysis_rejects_negative_values(field):
    with pytest.raises(ValidationError):
        BusinessModelAnalysis(**{field: Decimal("-1")})


# ---------------------------------------------------------------------------
# FinancialMetrics
# ---------------------------------------------------------------------------


def test_finacial_metrics_defaults():
    result = FinancialMetrics()

    assert result.revenue_multiple is None
    assert result.ebitda_multiple is None
    assert result.valuation_to_growth is None


def test_finacial_metrics_accepts_values():
    result = FinancialMetrics(
        revenue_multiple=Decimal("4"),
        ebitda_multiple=Decimal("20"),
        valuation_to_growth=Decimal("0.1"),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.ebitda_multiple == Decimal("20")
    assert result.valuation_to_growth == Decimal("0.1")


# ---------------------------------------------------------------------------
# AnalysisEvidence
# ---------------------------------------------------------------------------


def test_analysis_evidence_defaults():
    result = AnalysisEvidence()

    assert result.document_id is None
    assert result.page is None
    assert result.section is None
    assert result.source_text is None
    assert result.confidence is None


def test_analysis_evidence_accepts_valid_values():
    document_id = uuid4()

    result = AnalysisEvidence(
        document_id=document_id,
        page=12,
        section="Financials",
        source_text="FY2026 revenue was ₹10 Cr.",
        confidence=Decimal("0.95"),
    )

    assert result.document_id == document_id
    assert result.page == 12
    assert result.section == "Financials"
    assert result.confidence == Decimal("0.95")


@pytest.mark.parametrize(
    "confidence",
    [Decimal("-0.01"), Decimal("1.01")],
)
def test_analysis_evidence_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        AnalysisEvidence(confidence=confidence)


def test_analysis_evidence_accepts_confidence_boundaries():
    assert AnalysisEvidence(
        confidence=Decimal("0")
    ).confidence == Decimal("0")

    assert AnalysisEvidence(
        confidence=Decimal("1")
    ).confidence == Decimal("1")


def test_analysis_evidence_rejects_invalid_page():
    with pytest.raises(ValidationError):
        AnalysisEvidence(page=0)


# ---------------------------------------------------------------------------
# StartupAnalysisInput
# ---------------------------------------------------------------------------


def test_startup_analysis_input_minimal():
    result = StartupAnalysisInput(
        company=CompanyAnalysis(
            name="Example Startup",
        ),
    )

    assert result.startup_id is None
    assert result.company.name == "Example Startup"
    assert result.founders == []
    assert result.product is None
    assert result.market is None
    assert result.traction is None
    assert result.financials is None
    assert result.fundraising is None
    assert result.business_model is None
    assert result.evidence == []


def test_startup_analysis_input_accepts_all_sections():
    result = StartupAnalysisInput(
        startup_id=uuid4(),
        company=CompanyAnalysis(
            name="Example Startup",
            industry="Technology",
        ),
        founders=[
            FounderAnalysis(name="Founder One"),
        ],
        product=ProductAnalysis(
            solution="AI platform",
        ),
        market=MarketAnalysis(
            tam=Decimal("1000000000"),
        ),
        traction=TractionAnalysis(
            revenue=Decimal("10000000"),
        ),
        financials=FinancialAnalysis(
            ebitda=Decimal("2000000"),
        ),
        fundraising=FundraisingAnalysis(
            amount_raising=Decimal("50000000"),
        ),
        business_model=BusinessModelAnalysis(
            business_model="SaaS",
        ),
        evidence=[
            AnalysisEvidence(
                page=5,
                confidence=Decimal("0.9"),
            ),
        ],
    )

    assert len(result.founders) == 1
    assert result.product is not None
    assert result.market is not None
    assert result.traction is not None
    assert result.financials is not None
    assert result.fundraising is not None
    assert result.business_model is not None
    assert len(result.evidence) == 1


def test_startup_analysis_input_requires_company():
    with pytest.raises(ValidationError):
        StartupAnalysisInput()


# ---------------------------------------------------------------------------
# StartupAnalysisResult
# ---------------------------------------------------------------------------


def test_startup_analysis_result_defaults():
    result = StartupAnalysisResult()

    assert result.company_overview is None
    assert result.strengths == []
    assert result.risks == []
    assert result.missing_information == []
    assert result.key_observations == []
    assert result.investment_thesis is None
    assert result.preliminary_recommendation == (
        "insufficient_information"
    )


@pytest.mark.parametrize(
    "recommendation",
    [
        "insufficient_information",
        "promising",
        "needs_further_diligence",
        "concerns",
    ],
)
def test_startup_analysis_result_accepts_valid_recommendation(
    recommendation,
):
    result = StartupAnalysisResult(
        preliminary_recommendation=recommendation,
    )

    assert result.preliminary_recommendation == recommendation


def test_startup_analysis_result_rejects_invalid_recommendation():
    with pytest.raises(ValidationError):
        StartupAnalysisResult(
            preliminary_recommendation="invest",
        )


def test_startup_analysis_result_accepts_qualitative_output():
    result = StartupAnalysisResult(
        company_overview="B2B SaaS startup.",
        founder_assessment="Strong domain experience.",
        product_assessment="Clear product value proposition.",
        market_assessment="Large addressable market.",
        traction_assessment="Strong revenue growth.",
        financial_assessment="Positive EBITDA.",
        valuation_assessment="Potentially expensive.",
        business_model_assessment="Recurring revenue model.",
        competitive_assessment="Differentiated product.",
        strengths=[
            "Strong founder background",
            "Good revenue growth",
        ],
        risks=[
            "High valuation",
        ],
        missing_information=[
            "Customer concentration",
        ],
        key_observations=[
            "Revenue growth is strong.",
        ],
        investment_thesis=(
            "Interesting opportunity subject to valuation diligence."
        ),
        preliminary_recommendation="needs_further_diligence",
    )

    assert len(result.strengths) == 2
    assert len(result.risks) == 1
    assert len(result.missing_information) == 1
    assert len(result.key_observations) == 1
    assert result.preliminary_recommendation == (
        "needs_further_diligence"
    )


# ---------------------------------------------------------------------------
# StartupAnalysis
# ---------------------------------------------------------------------------


def test_startup_analysis_defaults():
    analysis_input = StartupAnalysisInput(
        company=CompanyAnalysis(
            name="Example Startup",
        ),
    )

    result = StartupAnalysis(
        input=analysis_input,
        result=StartupAnalysisResult(),
    )

    assert result.startup_id is None
    assert result.metrics.revenue_multiple is None
    assert result.metrics.ebitda_multiple is None
    assert result.analysis_version == "1.0"


def test_startup_analysis_accepts_complete_analysis():
    startup_id = uuid4()

    result = StartupAnalysis(
        startup_id=startup_id,
        input=StartupAnalysisInput(
            startup_id=startup_id,
            company=CompanyAnalysis(
                name="Example Startup",
                industry="Technology",
            ),
            financials=FinancialAnalysis(
                revenue=Decimal("10000000"),
                ebitda=Decimal("2000000"),
            ),
        ),
        metrics=FinancialMetrics(
            revenue_multiple=Decimal("4"),
            ebitda_multiple=Decimal("20"),
        ),
        result=StartupAnalysisResult(
            strengths=["Strong growth"],
            risks=["High valuation"],
            preliminary_recommendation="needs_further_diligence",
        ),
    )

    assert result.startup_id == startup_id
    assert result.input.financials is not None
    assert result.input.financials.ebitda == Decimal("2000000")
    assert result.metrics.revenue_multiple == Decimal("4")
    assert result.result.preliminary_recommendation == (
        "needs_further_diligence"
    )
    assert result.analysis_version == "1.0"


# ---------------------------------------------------------------------------
# Common schema behavior
# ---------------------------------------------------------------------------


def test_analysis_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CompanyAnalysis(
            name="Example Startup",
            unknown_field="not allowed",
        )


def test_analysis_schema_rejects_unknown_nested_fields():
    with pytest.raises(ValidationError):
        StartupAnalysisInput(
            company={
                "name": "Example Startup",
                "unknown_field": "not allowed",
            },
        )


# ---------------------------------------------------------------------------
# StartupAnalysisResult — LLM output contract
# ---------------------------------------------------------------------------

def test_startup_analysis_result_accepts_llm_output():
    result = StartupAnalysisResult.model_validate(
        {
            "company_overview": "B2B SaaS startup.",
            "founder_assessment": "Strong domain experience.",
            "product_assessment": "Clear product value proposition.",
            "market_assessment": "Large addressable market.",
            "traction_assessment": "Strong revenue growth.",
            "financial_assessment": "Positive EBITDA.",
            "valuation_assessment": "Potentially expensive.",
            "business_model_assessment": "Recurring revenue model.",
            "competitive_assessment": "Differentiated product.",
            "strengths": [
                "Strong founder background",
                "Good revenue growth",
            ],
            "risks": [
                "High valuation",
            ],
            "missing_information": [
                "Customer concentration",
            ],
            "key_observations": [
                "Revenue growth is strong.",
            ],
            "investment_thesis": (
                "Interesting opportunity subject to valuation diligence."
            ),
            "preliminary_recommendation": "needs_further_diligence",
        }
    )

    assert result.company_overview == "B2B SaaS startup."
    assert len(result.strengths) == 2
    assert len(result.risks) == 1
    assert result.preliminary_recommendation == (
        "needs_further_diligence"
    )


def test_startup_analysis_result_accepts_json():
    result = StartupAnalysisResult.model_validate_json(
        """
        {
          "company_overview": "B2B SaaS startup.",
          "strengths": ["Strong growth"],
          "risks": ["High valuation"],
          "missing_information": [],
          "key_observations": ["Revenue growth is strong."],
          "preliminary_recommendation": "promising"
        }
        """
    )

    assert result.company_overview == "B2B SaaS startup."
    assert result.strengths == ["Strong growth"]
    assert result.preliminary_recommendation == "promising"


def test_startup_analysis_result_rejects_invalid_recommendation():
    with pytest.raises(ValidationError):
        StartupAnalysisResult.model_validate(
            {
                "preliminary_recommendation": "invest",
            }
        )

def test_startup_analysis_result_rejects_malformed_json():
    with pytest.raises(ValidationError):
        StartupAnalysisResult.model_validate_json(
            '{"company_overview": "Example"'
        )


