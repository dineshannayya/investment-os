"""Tests for StartupAnalysisInputBuilder."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.enums import (
    FounderRole,
    InvestmentInstrument,
    OpportunityStatus,
    StartupStage,
)
from app.models.founder import Founder
from app.models.opportunity import Opportunity
from app.models.startup import Startup
from app.services.startup_analysis_input_builder import (
    StartupAnalysisInputBuilder,
)


def make_startup() -> Startup:
    """Build a representative startup aggregate without database access."""
    startup = Startup(
        name="Example AI Technologies",
        description="AI-powered edge analytics company.",
        industry="Artificial Intelligence",
        sector="Surveillance",
        stage=StartupStage.MVP,
        founded_year=2024,
        headquarters="Bengaluru, India",
    )
    startup.id = uuid4()

    founder = Founder(
        startup=startup,
        full_name="Jane Doe",
        designation=FounderRole.CTO,
        experience_years=12,
        education="M.Tech in Computer Science",
        previous_companies="Company A; Company B",
        notes="Technical founder",
    )
    founder.id = uuid4()

    return startup


def make_opportunity(
    startup: Startup,
    *,
    status: OpportunityStatus = OpportunityStatus.OPEN,
    round_name: str = "Pre-Series A",
    instrument: InvestmentInstrument = InvestmentInstrument.CCPS,
) -> Opportunity:
    """Build a representative fundraising opportunity."""
    opportunity = Opportunity(
        startup=startup,
        round_name=round_name,
        instrument=instrument,
        status=status,
        target_raise=5_000_000,
        minimum_ticket=500_000,
        valuation_cap=25_000_000,
        pre_money_valuation=20_000_000,
        post_money_valuation=25_000_000,
        committed_amount=3_000_000,
        soft_committed_amount=1_000_000,
        investment_thesis="Scale the core product.",
        risk_summary="Execution and market expansion risk.",
        analyst_notes="Current fundraising round.",
    )
    opportunity.id = uuid4()

    return opportunity


def test_build_maps_company_information():
    startup = make_startup()

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.startup_id == startup.id
    assert result.company.name == "Example AI Technologies"
    assert result.company.description == "AI-powered edge analytics company."
    assert result.company.industry == "Artificial Intelligence"
    assert result.company.sector == "Surveillance"
    assert result.company.stage == "mvp"
    assert result.company.founded_year == 2024
    assert result.company.headquarters == "Bengaluru, India"


def test_build_maps_founder_information():
    startup = make_startup()

    result = StartupAnalysisInputBuilder().build(startup)

    assert len(result.founders) == 1

    founder = result.founders[0]

    assert founder.founder_id == startup.founders[0].id
    assert founder.name == "Jane Doe"
    assert founder.role == "CTO"
    assert founder.background == "M.Tech in Computer Science"
    assert founder.relevant_experience == (
        "12 years experience; Previous companies: Company A; Company B"
    )
    assert founder.previous_startups is None
    assert founder.previous_exits is None
    assert founder.analysis_notes == "Technical founder"


def test_build_without_founders_returns_empty_list():
    startup = Startup(
        name="Minimal Startup",
        stage=StartupStage.IDEA,
    )
    startup.id = uuid4()

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.founders == []


def test_build_without_opportunities_returns_no_fundraising():
    startup = make_startup()

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is None


def test_build_maps_open_opportunity_to_fundraising():
    startup = make_startup()
    opportunity = make_opportunity(startup)

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is not None

    fundraising = result.fundraising

    assert fundraising.current_round == "Pre-Series A"
    assert fundraising.amount_raising == 5_000_000

    # A commitment is not necessarily capital already raised.
    assert fundraising.amount_raised is None

    assert fundraising.pre_money_valuation == 20_000_000
    assert fundraising.post_money_valuation == 25_000_000
    assert fundraising.valuation_cap == 25_000_000

    assert fundraising.instrument == "CCPS"

    # Opportunity.committed_amount represents investor commitments.
    assert fundraising.investor_commitments == 3_000_000


def test_build_uses_instrument_enum_value():
    startup = make_startup()

    make_opportunity(
        startup,
        instrument=InvestmentInstrument.CCD,
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is not None
    assert result.fundraising.instrument == "CCD"


def test_build_ignores_closed_opportunity():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.CLOSED,
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is None


def test_build_ignores_fully_subscribed_opportunity():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.FULLY_SUBSCRIBED,
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is None


def test_build_ignores_cancelled_opportunity():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.CANCELLED,
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is None


def test_build_ignores_closed_opportunity_when_open_opportunity_exists():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.CLOSED,
        round_name="Seed",
    )

    make_opportunity(
        startup,
        status=OpportunityStatus.OPEN,
        round_name="Series A",
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is not None
    assert result.fundraising.current_round == "Series A"


def test_build_rejects_multiple_open_opportunities():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.OPEN,
        round_name="Seed",
    )

    make_opportunity(
        startup,
        status=OpportunityStatus.OPEN,
        round_name="Series A",
    )

    with pytest.raises(
        ValueError,
        match="multiple OPEN fundraising opportunities",
    ):
        StartupAnalysisInputBuilder().build(startup)


def test_build_does_not_map_soft_committed_amount_to_amount_raised():
    startup = make_startup()

    make_opportunity(
        startup,
        status=OpportunityStatus.OPEN,
    )

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is not None
    assert result.fundraising.amount_raised is None
    assert result.fundraising.investor_commitments == 3_000_000


def test_build_does_not_invent_unavailable_analysis_sections():
    startup = make_startup()

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.product is None
    assert result.market is None
    assert result.traction is None
    assert result.financials is None
    assert result.fundraising is None
    assert result.business_model is None
    assert result.evidence == []


def test_build_preserves_unavailable_sections_when_fundraising_exists():
    startup = make_startup()
    make_opportunity(startup)

    result = StartupAnalysisInputBuilder().build(startup)

    assert result.fundraising is not None
    assert result.product is None
    assert result.market is None
    assert result.traction is None
    assert result.financials is None
    assert result.business_model is None
    assert result.evidence == []


def test_build_does_not_copy_private_founder_contact_information():
    startup = make_startup()

    startup.founders[0].email = "jane@example.com"
    startup.founders[0].phone = "+91-9999999999"
    startup.founders[0].linkedin_url = (
        "https://linkedin.com/in/janedoe"
    )

    result = StartupAnalysisInputBuilder().build(startup)

    payload = result.founders[0].model_dump()

    assert "email" not in payload
    assert "phone" not in payload
    assert "linkedin_url" not in payload
