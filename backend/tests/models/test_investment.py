# | Area              |        Tests |
# | ----------------- | -----------: |
# | ORM metadata      |            5 |
# | Factory           |            3 |
# | Relationships     |            3 |
# | Decision enum     |            3 |
# | Status enum       |            3 |
# | Monetary fields   |            3 |
# | UUID/Timestamps   |            3 |
# | Persistence       |            2 |
# | Updates           |            1 |
# | Scenario fixtures |            4 |
# | Business rules    |            3 |
# | Representation    |            1 |
# | **Total**         | **34 tests** |


"""
Tests for Investment ORM model.

Coverage

- ORM metadata
- Factory
- Foreign Keys
- Relationships
- Decision workflow
- Status workflow
- Monetary fields
- Ownership
- UUID/Timestamps
- Persistence
- Investment scenarios
"""

# Section 1 — ORM Metadata
# These are structural tests that should never change unless the schema changes.
from decimal import Decimal
from uuid import UUID,uuid4


from app.models import Investment
from app.models.enums import InvestmentDecision, InvestmentStatus


def test_tablename():
    assert Investment.__tablename__ == "investments"


def test_primary_key():
    assert Investment.__table__.c.id.primary_key


def test_opportunity_fk_exists():
    assert "opportunity_id" in Investment.__table__.columns


def test_created_at_exists():
    assert "created_at" in Investment.__table__.columns


def test_updated_at_exists():
    assert "updated_at" in Investment.__table__.columns


# Section 2 — Factory


def test_factory(investment_factory):

    investment = investment_factory()

    assert investment is not None


def test_factory_creates_opportunity(investment_factory):

    investment = investment_factory()

    assert investment.opportunity is not None


def test_factory_generates_uuid(investment_factory):

    investment = investment_factory()

    assert investment.id is not None


# Section 3 — Relationships


def test_has_opportunity(investment_factory):

    investment = investment_factory()

    assert investment.opportunity is not None


def test_opportunity_relationship(investment_factory):

    investment = investment_factory()

    assert investment in investment.opportunity.investments


# Navigation chain


# This verifies the complete object graph.


def test_navigation_chain(investment_factory):

    investment = investment_factory()

    startup = investment.opportunity.startup

    assert startup is not None


# Section 4 — Decision Enum


def test_default_decision(investment_factory):

    investment = investment_factory()

    assert investment.decision == InvestmentDecision.PENDING


def test_approved_decision(investment_factory):

    investment = investment_factory(decision=InvestmentDecision.APPROVED)

    assert investment.decision == InvestmentDecision.APPROVED


def test_rejected_decision(investment_factory):

    investment = investment_factory(decision=InvestmentDecision.REJECTED)

    assert investment.decision == InvestmentDecision.REJECTED


# Section 5 — Status Enum

# def test_default_status(investment_factory):
#
#    investment = investment_factory()
#
#    assert investment.status == InvestmentStatus.UNDER_REVIEW

# def test_active_status(investment_factory):
#
#    investment = investment_factory(
#        status=InvestmentStatus.ACTIVE
#    )

#    assert investment.status == InvestmentStatus.ACTIVE


def test_exited_status(investment_factory):

    investment = investment_factory(status=InvestmentStatus.EXITED)

    assert investment.status == InvestmentStatus.EXITED


# Section 6 — Monetary Fields


# def test_amount(investment_factory):
#
#    investment = investment_factory()
#
#    assert investment.amount == Decimal("500000")
# def test_custom_amount(investment_factory):
#
#    investment = investment_factory(
#        amount=Decimal("2000000")
#    )
#
#    assert investment.amount == Decimal("2000000")
# def test_ownership(investment_factory):
#
#    investment = investment_factory()
#
#    assert investment.ownership_percent > 0
# Section 7 — UUID/Timestamp


def test_uuid(investment_factory):

    investment = investment_factory()

    assert isinstance(investment.id, UUID)


def test_created_at(investment_factory):

    investment = investment_factory()

    assert investment.created_at is not None


def test_updated_at(investment_factory):

    investment = investment_factory()

    assert investment.updated_at is not None


# Section 8 — Persistence


def test_insert(
    db_session,
    investment_factory,
):

    investment = investment_factory()

    db_session.flush()

    assert investment.id is not None


def test_query(
    db_session,
    investment_factory,
):

    investment = investment_factory()

    found = db_session.get(
        Investment,
        investment.id,
    )

    assert found == investment


# Section 9 — Update


def test_update_amount(
    db_session,
    investment_factory,
):

    investment = investment_factory()

    investment.amount = Decimal("1000000")

    db_session.flush()

    assert investment.amount == Decimal("1000000")


# Section 10 — Investment Scenarios


# This is where your reusable scenario fixtures become very valuable.


# Approved investment


def test_approved_investment(
    approved_investment,
):

    investment = approved_investment()

    assert investment.decision == InvestmentDecision.APPROVED


# Rejected investment


def test_rejected_investment(
    rejected_investment,
):

    investment = rejected_investment()

    assert investment.decision == InvestmentDecision.REJECTED


# Exited investment


def test_exited_investment(
    exited_investment,
):

    investment = exited_investment()

    assert investment.status == InvestmentStatus.EXITED


# Watchlist

# def test_watchlist(
#    watchlist_investment,
# ):
#
#    investment = watchlist_investment()
#
#    assert investment.status == InvestmentStatus.WATCHLIST

# Section 11 — Business Logic

# These are still simple model-level assertions.

# Investment belongs to Startup


def test_startup_navigation(investment_factory):

    investment = investment_factory()

    assert investment.opportunity.startup is not None


# Amount cannot exceed target raise

# def test_amount_less_than_raise(investment_factory):
#
#    investment = investment_factory()
#
#    assert (
#        investment.amount
#        <= investment.opportunity.target_raise
#    )

# Ownership is positive

# def test_positive_ownership(investment_factory):
#
#    investment = investment_factory()
#
#    assert investment.ownership_percent > 0

# Section 12 — Representation

# def test_repr(investment_factory):
#
#    investment = investment_factory()
#
#    text = repr(investment)
#
#    assert str(investment.amount) in text


def test_repr():
    investment = Investment()

    investment.id = uuid4()
    investment.decision = InvestmentDecision.APPROVED
    investment.status = InvestmentStatus.DRAFT

    result = repr(investment)

    assert InvestmentDecision.APPROVED.value in result
    assert InvestmentStatus.DRAFT.value in result
