# -----------------------------------------
#  | Area               |        Tests |
#  | ------------------ | -----------: |
#  | ORM metadata       |            5 |
#  | Factory            |            3 |
#  | Required fields    |            4 |
#  | Foreign key        |            2 |
#  | Relationships      |            2 |
#  | Instrument enum    |            3 |
#  | Status enum        |            2 |
#  | Decimal fields     |            3 |
#  | UUID/Timestamp     |            3 |
#  | Persistence        |            2 |
#  | Updates            |            1 |
#  | Business scenarios |            6 |
#  | Representation     |            1 |
#  | **Total**          | **37 tests** |
#  ---------------------------------------------

"""
Tests for Opportunity ORM model.

Coverage

- ORM metadata
- Factory
- Foreign key
- Relationships
- Investment instrument
- Opportunity status
- Monetary fields
- UUID/Timestamp
- Persistence
- Updates
- Investment business rules
"""

from decimal import Decimal
from uuid import UUID

from app.models import Opportunity
from app.models.enums import InvestmentInstrument, OpportunityStatus


# 1 — ORM Metadata
def test_tablename():
    assert Opportunity.__tablename__ == "opportunities"


def test_primary_key():
    assert Opportunity.__table__.c.id.primary_key


def test_startup_fk_exists():
    assert "startup_id" in Opportunity.__table__.columns


def test_created_at_exists():
    assert "created_at" in Opportunity.__table__.columns


def test_updated_at_exists():
    assert "updated_at" in Opportunity.__table__.columns


# 2 — Factory
def test_factory(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity is not None


def test_factory_creates_startup(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.startup is not None


def test_factory_generates_uuid(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.id is not None


# 3 — Required Fields
def test_round_name(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.round_name


def test_currency_default(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.currency == "INR"


def test_target_raise_exists(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.target_raise is not None


def test_minimum_ticket_exists(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.minimum_ticket is not None


# 4 — Foreign Key
def test_has_startup(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.startup is not None


def test_startup_id_matches(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.startup.id == opportunity.startup_id


# 5 — Relationships
def test_startup_relationship(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity in opportunity.startup.opportunities


# 6 — Instrument Enum
def test_default_instrument(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.instrument == InvestmentInstrument.CCPS


def test_ccd(opportunity_factory):

    opportunity = opportunity_factory(instrument=InvestmentInstrument.CCD)

    assert opportunity.instrument == InvestmentInstrument.CCD


def test_safe(opportunity_factory):

    opportunity = opportunity_factory(instrument=InvestmentInstrument.SAFE)

    assert opportunity.instrument == InvestmentInstrument.SAFE


# 7 — Status Enum
def test_default_status(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.status == OpportunityStatus.OPEN


def test_closed_status(opportunity_factory):

    opportunity = opportunity_factory(status=OpportunityStatus.CLOSED)

    assert opportunity.status == OpportunityStatus.CLOSED


# 8 — Decimal Fields


def test_target_raise(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.target_raise == Decimal("50000000")


def test_minimum_ticket(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.minimum_ticket == Decimal("500000")


def test_custom_raise(opportunity_factory):

    opportunity = opportunity_factory(target_raise=Decimal("100000000"))

    assert opportunity.target_raise == Decimal("100000000")


# 9 — UUID / Timestamp


def test_uuid(opportunity_factory):

    opportunity = opportunity_factory()

    assert isinstance(opportunity.id, UUID)


def test_created_at(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.created_at is not None


def test_updated_at(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.updated_at is not None


# 10 — Persistence


def test_insert(
    db_session,
    opportunity_factory,
):

    opportunity = opportunity_factory()

    db_session.flush()

    assert opportunity.id is not None


def test_query(
    db_session,
    opportunity_factory,
):

    opportunity = opportunity_factory()

    found = db_session.get(
        Opportunity,
        opportunity.id,
    )

    assert found == opportunity


# 11 — Updates
def test_update_round_name(
    db_session,
    opportunity_factory,
):

    opportunity = opportunity_factory()

    opportunity.round_name = "Series A"

    db_session.flush()

    assert opportunity.round_name == "Series A"


# 12 — Business Scenarios
def test_seed_round(seed_round):

    opportunity = seed_round()

    assert opportunity.round_name == "Seed"


def test_series_a(series_a_round):

    opportunity = series_a_round()

    assert opportunity.round_name == "Series A"


def test_pre_series_a(pre_series_a_round):

    opportunity = pre_series_a_round()

    assert opportunity.round_name == "Pre-Series A"


def test_ticket_less_than_raise(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.minimum_ticket < opportunity.target_raise


def test_currency_inr(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.currency == "INR"


def test_default_open(opportunity_factory):

    opportunity = opportunity_factory()

    assert opportunity.status is OpportunityStatus.OPEN


# Section 13 — Representation


def test_repr(opportunity_factory):

    opportunity = opportunity_factory()

    text = repr(opportunity)

    assert opportunity.round_name in text
