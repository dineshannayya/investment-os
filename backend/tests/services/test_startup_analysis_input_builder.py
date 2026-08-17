"""Tests for StartupAnalysisInputBuilder."""

from __future__ import annotations

from uuid import uuid4

from app.models.enums import FounderRole, StartupStage
from app.models.founder import Founder
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


def test_build_does_not_copy_private_founder_contact_information():
    startup = make_startup()
    startup.founders[0].email = "jane@example.com"
    startup.founders[0].phone = "+91-9999999999"
    startup.founders[0].linkedin_url = "https://linkedin.com/in/janedoe"

    result = StartupAnalysisInputBuilder().build(startup)

    payload = result.founders[0].model_dump()
    assert "email" not in payload
    assert "phone" not in payload
    assert "linkedin_url" not in payload
