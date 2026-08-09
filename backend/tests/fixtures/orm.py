"""
Reusable ORM factories for tests.

Each factory creates one valid ORM object with sensible defaults.

Factories should:
- Create exactly one ORM object
- Persist it into the current db_session
- Allow every field to be overridden
- Never implement business scenarios

Business scenarios belong in:
    tests/investment_scenarios.py
"""

# Imports

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models import (
    Document,
    Founder,
    Investment,
    Opportunity,
    Startup,
)
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    FounderRole,
    InvestmentDecision,
    InvestmentInstrument,
    InvestmentStatus,
    OpportunityStatus,
    StartupStage,
    StartupStatus,
)

# Shared Helper
# This removes duplication.


def _persist(session, obj):
    session.add(obj)
    session.flush()
    return obj


# Startup Factory


@pytest.fixture
def startup_factory(db_session):

    def create(**kwargs) -> Startup:

        defaults = {
            "name": "Test Startup",
            "legal_name": None,
            "description": None,
            "sector": "Semiconductor",
            "industry": "AI",
            "stage": StartupStage.IDEA,
            "status": StartupStatus.ACTIVE,
            "founded_year": 2025,
            "website": None,
            "headquarters": "Bangalore",
        }

        defaults.update(kwargs)

        startup = Startup(**defaults)

        return _persist(db_session, startup)

    return create


# Founder Factory


@pytest.fixture
def founder_factory(
    db_session,
    startup_factory,
):

    def create(**kwargs) -> Founder:

        startup = kwargs.pop("startup", None)

        if startup is None:
            startup = startup_factory()

        defaults = {
            "startup": startup,
            "full_name": "John Doe",
            "designation": FounderRole.CEO,
            "email": None,
            "ownership_percent": Decimal("75.00"),
            "is_primary_contact": True,
        }

        defaults.update(kwargs)

        founder = Founder(**defaults)

        return _persist(db_session, founder)

    return create


# Opportunity Factory
@pytest.fixture
def opportunity_factory(
    db_session,
    startup_factory,
):

    def create(**kwargs) -> Opportunity:

        startup = kwargs.pop("startup", None)

        if startup is None:
            startup = startup_factory()

        defaults = {
            "startup": startup,
            "round_name": "Seed",
            "instrument": InvestmentInstrument.CCPS,
            "status": OpportunityStatus.OPEN,
            "currency": "INR",
            "target_raise": Decimal("50000000"),
            "minimum_ticket": Decimal("500000"),
            "valuation_cap": None,
            "committed_amount": Decimal("0"),
        }

        defaults.update(kwargs)

        opportunity = Opportunity(**defaults)

        return _persist(db_session, opportunity)

    return create


# Document Factory
@pytest.fixture
def document_factory(
    db_session,
    startup_factory,
):

    def create(**kwargs) -> Document:

        startup = kwargs.pop("startup", None)

        if startup is None:
            startup = startup_factory()

        defaults = {
            "startup": startup,
            "document_type": DocumentType.PITCH_DECK,
            "status": DocumentStatus.UPLOADED,
            "title": "Pitch Deck",
            "filename": f"{uuid4().hex}.pdf",
            "original_filename": "pitch.pdf",
            "mime_type": "application/pdf",
            "file_size": 12345,
            "file_hash": uuid4().hex,
            "storage_path": f"/test/{uuid4().hex}.pdf",
        }

        defaults.update(kwargs)

        document = Document(**defaults)

        return _persist(db_session, document)

    return create


# Investment Factory

# Instead of exposing only three fields, expose the complete model.


@pytest.fixture
def investment_factory(
    db_session,
    opportunity_factory,
):

    def create(**kwargs) -> Investment:

        opportunity = kwargs.pop("opportunity", None)

        if opportunity is None:
            opportunity = opportunity_factory()

        defaults = {
            "opportunity": opportunity,
            "decision": InvestmentDecision.PENDING,
            "status": InvestmentStatus.DRAFT,
            "investment_amount": Decimal("500000"),
            "ownership_target": None,
            "expected_ownership": None,
            "investment_date": None,
            "investment_lead": None,
            "committee_reference": None,
            "requires_followup": False,
            "rationale": None,
            "conditions": None,
            "notes": None,
        }

        defaults.update(kwargs)

        investment = Investment(**defaults)

        return _persist(db_session, investment)

    return create
