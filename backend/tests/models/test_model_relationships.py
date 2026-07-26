"""
Integration tests for SQLAlchemy model relationships.

Coverage
--------
- Startup <-> Founder
- Startup <-> Opportunity
- Startup <-> Document
- Opportunity <-> Investment
- Full navigation graph
- Reverse navigation
- Multiple children
- Persistence
"""


# Section 1 — Startup ↔ Founder
def test_startup_founder_relationship(
    startup_factory,
    founder_factory,
):
    startup = startup_factory()
    founder = founder_factory(startup=startup)

    assert founder.startup == startup
    assert founder in startup.founders


def test_multiple_founders(
    startup_factory,
    founder_factory,
):
    startup = startup_factory()

    founder_factory(startup=startup)
    founder_factory(startup=startup)
    founder_factory(startup=startup)

    assert len(startup.founders) == 3


# Section 2 — Startup ↔ Opportunity


def test_startup_opportunity_relationship(
    startup_factory,
    opportunity_factory,
):
    startup = startup_factory()
    opportunity = opportunity_factory(startup=startup)

    assert opportunity.startup == startup
    assert opportunity in startup.opportunities


def test_multiple_opportunities(
    startup_factory,
    opportunity_factory,
):
    startup = startup_factory()

    opportunity_factory(startup=startup)
    opportunity_factory(startup=startup)

    assert len(startup.opportunities) == 2


# Section 3 — Startup ↔ Document


def test_startup_document_relationship(
    startup_factory,
    document_factory,
):
    startup = startup_factory()
    document = document_factory(startup=startup)

    assert document.startup == startup
    assert document in startup.documents


def test_multiple_documents(
    startup_factory,
    document_factory,
):
    startup = startup_factory()

    document_factory(startup=startup)
    document_factory(startup=startup)
    document_factory(startup=startup)

    assert len(startup.documents) == 3


# Section 4 — Opportunity ↔ Investment


def test_opportunity_investment_relationship(
    opportunity_factory,
    investment_factory,
):
    opportunity = opportunity_factory()
    investment = investment_factory(opportunity=opportunity)

    assert investment.opportunity == opportunity
    assert investment in opportunity.investments


def test_multiple_investments(
    opportunity_factory,
    investment_factory,
):
    opportunity = opportunity_factory()

    investment_factory(opportunity=opportunity)
    investment_factory(opportunity=opportunity)

    assert len(opportunity.investments) == 2


# Section 5 — Complete navigation graph

# This is the most important section.


def test_investment_to_startup_navigation(
    investment_factory,
):
    investment = investment_factory()

    assert investment.opportunity.startup is not None


def test_startup_to_investment_navigation(
    investment_factory,
):
    investment = investment_factory()

    startup = investment.opportunity.startup

    assert investment in startup.opportunities[0].investments


def test_document_and_founder_same_startup(
    startup_factory,
    founder_factory,
    document_factory,
):
    startup = startup_factory()

    founder = founder_factory(startup=startup)
    document = document_factory(startup=startup)

    assert founder.startup == document.startup


# Section 6 — Reverse navigation
def test_reverse_founder_navigation(
    founder_factory,
):
    founder = founder_factory()

    assert founder in founder.startup.founders


def test_reverse_document_navigation(
    document_factory,
):
    document = document_factory()

    assert document in document.startup.documents


def test_reverse_investment_navigation(
    investment_factory,
):
    investment = investment_factory()

    assert investment in investment.opportunity.investments


# Section 7 — Persistence
def test_relationships_survive_flush(
    db_session,
    investment_factory,
):
    investment = investment_factory()

    db_session.flush()

    loaded = db_session.get(
        type(investment),
        investment.id,
    )

    assert loaded.opportunity is not None
    assert loaded.opportunity.startup is not None


def test_relationships_survive_commit(
    db_session,
    investment_factory,
):
    investment = investment_factory()

    db_session.commit()

    loaded = db_session.get(
        type(investment),
        investment.id,
    )

    assert loaded.opportunity.startup is not None
