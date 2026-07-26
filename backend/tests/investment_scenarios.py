"""
Business scenario fixtures.

These fixtures build complete investment scenarios used by
repository, service and API tests.
"""

from decimal import Decimal

import pytest

from app.models.enums import (
    DocumentType,
    FounderRole,
    InvestmentDecision,
    InvestmentInstrument,
    InvestmentStatus,
    OpportunityStatus,
    StartupStage,
)


@pytest.fixture
def semiconductor_startup(
    startup_factory,
    founder_factory,
):
    def create(**kwargs):

        startup = startup_factory(
            name=kwargs.get(
                "name",
                "BigEndian Semiconductor",
            ),
            sector="Semiconductor",
            industry="Fabless ASIC",
            stage=StartupStage.MVP,
            headquarters="Bangalore",
        )

        founder_factory(
            startup=startup,
            full_name="Founder",
            designation=FounderRole.CEO,
            ownership_percent=Decimal("82.50"),
        )

        return startup

    return create


@pytest.fixture
def healthcare_startup(
    startup_factory,
    founder_factory,
):
    def create(**kwargs):

        startup = startup_factory(
            name="HealthAI",
            sector="Healthcare",
            industry="Medical Devices",
            stage=StartupStage.EARLY_REVENUE,
        )

        founder_factory(
            startup=startup,
            designation=FounderRole.CEO,
        )

        return startup

    return create


@pytest.fixture
def ai_startup(
    startup_factory,
    founder_factory,
):
    def create(**kwargs):

        startup = startup_factory(
            name="Vision AI",
            sector="Artificial Intelligence",
            industry="Computer Vision",
            stage=StartupStage.GROWTH,
        )

        founder_factory(
            startup=startup,
            designation=FounderRole.CTO,
        )

        return startup

    return create


@pytest.fixture
def seed_round(
    semiconductor_startup,
    opportunity_factory,
):
    def create(**kwargs):

        startup = kwargs.get(
            "startup",
            semiconductor_startup(),
        )

        return opportunity_factory(
            startup=startup,
            round_name="Seed",
            instrument=InvestmentInstrument.CCPS,
            target_raise=Decimal("50000000"),
            minimum_ticket=Decimal("500000"),
        )

    return create


# This represents a startup preparing for institutional funding.
@pytest.fixture
def pre_series_a_round(
    ai_startup,
    opportunity_factory,
):
    def create(**kwargs):

        startup = kwargs.get(
            "startup",
            ai_startup(),
        )

        return opportunity_factory(
            startup=startup,
            round_name="Pre-Series A",
            instrument=InvestmentInstrument.CCPS,
            target_raise=Decimal("500000000"),  # ₹50 Cr
            minimum_ticket=Decimal("5000000"),  # ₹50 L
            valuation_cap=Decimal("2000000000"),  # ₹200 Cr
            committed_amount=Decimal("300000000"),  # ₹30 Cr
            status=OpportunityStatus.OPEN,
        )

    return create


@pytest.fixture
def series_a_round(
    ai_startup,
    opportunity_factory,
):
    def create(**kwargs):

        startup = kwargs.get(
            "startup",
            ai_startup(),
        )

        return opportunity_factory(
            startup=startup,
            round_name="Series A",
            instrument=InvestmentInstrument.EQUITY,
            target_raise=Decimal("250000000"),
            minimum_ticket=Decimal("5000000"),
        )

    return create


# Represents a healthy founder ownership structure.
@pytest.fixture
def founder_friendly_cap_table(
    startup_factory,
    founder_factory,
):
    def create():

        startup = startup_factory(
            name="Founder Friendly Startup",
        )

        founder_factory(
            startup=startup,
            full_name="Founder One",
            designation=FounderRole.CEO,
            ownership_percent=Decimal("42.5"),
        )

        founder_factory(
            startup=startup,
            full_name="Founder Two",
            designation=FounderRole.CTO,
            ownership_percent=Decimal("27.5"),
        )

        return startup

    return create


# This models one of the scenarios you've repeatedly highlighted in your startup reviews.
@pytest.fixture
def founder_concentrated_cap_table(
    startup_factory,
    founder_factory,
):
    def create():

        startup = startup_factory(
            name="Founder Concentrated",
        )

        founder_factory(
            startup=startup,
            full_name="Solo Founder",
            designation=FounderRole.CEO,
            ownership_percent=Decimal("92.0"),
        )

        return startup

    return create


# Represents incomplete due diligence.
@pytest.fixture
def missing_sha_documents(
    semiconductor_startup,
    document_factory,
):
    def create():

        startup = semiconductor_startup()

        document_factory(
            startup=startup,
            document_type=DocumentType.PITCH_DECK,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.CAP_TABLE,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.FINANCIAL_MODEL,
        )

        # SHA intentionally omitted

        return startup

    return create


# Represents an ideal investment opportunity.
@pytest.fixture
def complete_due_diligence(
    semiconductor_startup,
    document_factory,
):
    def create():

        startup = semiconductor_startup()

        document_factory(
            startup=startup,
            document_type=DocumentType.PITCH_DECK,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.SHA,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.CAP_TABLE,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.FINANCIAL_MODEL,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.GST,
        )

        document_factory(
            startup=startup,
            document_type=DocumentType.ROC,
        )

        return startup

    return create


@pytest.fixture
def watchlist_investment(
    seed_round,
    investment_factory,
):
    def create(**kwargs):

        opportunity = kwargs.get(
            "opportunity",
            seed_round(),
        )

        return investment_factory(
            opportunity=opportunity,
            decision=InvestmentDecision.WATCHLIST,
            status=InvestmentStatus.UNDER_REVIEW,
        )

    return create


@pytest.fixture
def approved_investment(
    seed_round,
    investment_factory,
):
    def create(**kwargs):

        opportunity = kwargs.get(
            "opportunity",
            seed_round(),
        )

        return investment_factory(
            opportunity=opportunity,
            decision=InvestmentDecision.APPROVED,
            status=InvestmentStatus.EXECUTED,
            investment_amount=Decimal("2000000"),
        )

    return create


@pytest.fixture
def rejected_investment(
    seed_round,
    investment_factory,
):
    def create():

        opportunity = seed_round()

        return investment_factory(
            opportunity=opportunity,
            decision=InvestmentDecision.REJECTED,
            status=InvestmentStatus.DECLINED,
            rationale="High founder concentration and incomplete legal documents.",
        )

    return create


# Represents a completed investment lifecycle.
@pytest.fixture
def exited_investment(
    series_a_round,
    investment_factory,
):
    def create():

        opportunity = series_a_round()

        return investment_factory(
            opportunity=opportunity,
            decision=InvestmentDecision.APPROVED,
            status=InvestmentStatus.EXITED,
            investment_amount=Decimal("5000000"),
            expected_ownership=Decimal("4.25"),
            notes="Exited through strategic acquisition.",
        )

    return create
