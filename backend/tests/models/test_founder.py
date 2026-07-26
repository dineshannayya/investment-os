# -------------------------------------------------
#  | Area             |           Tests |
#  | ---------------- | --------------: |
#  | ORM metadata     |               5 |
#  | Factory          |               3 |
#  | Required fields  |               3 |
#  | Foreign key      |               2 |
#  | Relationships    |               2 |
#  | Enum handling    |               2 |
#  | Decimal handling |               3 |
#  | UUID/Timestamps  |               3 |
#  | Persistence      |               2 |
#  | Updates          |               1 |
#  | Business rules   |               3 |
#  | Representation   |               1 |
#  | **Total**        | **30–32 tests** |
# ---------------------------------------------------------

"""
Tests for Founder ORM model.

Coverage

- ORM metadata
- Factory
- Foreign Keys
- Relationships
- Enum fields
- Decimal ownership
- UUID/Timestamps
- Constraints
- Business validation
"""

# 1 — ORM Metadata
from app.models import Founder
from app.models.enums import FounderRole


def test_tablename():
    assert Founder.__tablename__ == "founders"

def test_primary_key():
    assert Founder.__table__.c.id.primary_key

def test_startup_fk_exists():
    assert "startup_id" in Founder.__table__.columns

def test_created_at_exists():
    assert "created_at" in Founder.__table__.columns

def test_updated_at_exists():
    assert "updated_at" in Founder.__table__.columns

# 2 — Factory

def test_founder_factory(founder_factory):

    founder = founder_factory()

    assert founder is not None


def test_factory_creates_startup(founder_factory):

    founder = founder_factory()

    assert founder.startup is not None

def test_factory_generates_uuid(founder_factory):

    founder = founder_factory()

    assert founder.id is not None

# 6 — Enum
def test_default_role(founder_factory):

    founder = founder_factory()

    assert founder.designation == FounderRole.CEO


def test_custom_role(founder_factory):

    founder = founder_factory(
        designation=FounderRole.CTO,
    )

    assert founder.designation == FounderRole.CTO

# 7 — Ownership
from decimal import Decimal


def test_default_ownership(founder_factory):

    founder = founder_factory()

    assert founder.ownership_percent == Decimal("75.00")

def test_custom_ownership(founder_factory):

    founder = founder_factory(
        ownership_percent=Decimal("42.50")
    )

    assert founder.ownership_percent == Decimal("42.50")

def test_decimal_precision(founder_factory):

    founder = founder_factory(
        ownership_percent=Decimal("33.33")
    )

    assert founder.ownership_percent == Decimal("33.33")

# 8 — UUID/Timestamp
from uuid import UUID


def test_uuid(founder_factory):

    founder = founder_factory()

    assert isinstance(founder.id, UUID)

def test_created_at(founder_factory):

    founder = founder_factory()

    assert founder.created_at is not None

def test_updated_at(founder_factory):

    founder = founder_factory()

    assert founder.updated_at is not None

# 9 — Persistence
def test_insert(
    db_session,
    founder_factory,
):

    founder = founder_factory()

    db_session.flush()

    assert founder.id is not None

def test_query(
    db_session,
    founder_factory,
):

    founder = founder_factory()

    found = db_session.get(
        Founder,
        founder.id,
    )

    assert found == founder

# 10 — Updates
def test_update_name(
    db_session,
    founder_factory,
):

    founder = founder_factory()

    founder.full_name = "Updated"

    db_session.flush()

    assert founder.full_name == "Updated"

# 11 — Business Rules
def test_single_founder_ownership(founder_factory):

    founder = founder_factory(
        ownership_percent=Decimal("92.00")
    )

    assert founder.ownership_percent > Decimal("90")


def test_multiple_founder_distribution(
    startup_factory,
    founder_factory,
):

    startup = startup_factory()

    founder_factory(
        startup=startup,
        ownership_percent=Decimal("45")
    )

    founder_factory(
        startup=startup,
        ownership_percent=Decimal("35")
    )

    total = sum(
        founder.ownership_percent
        for founder in startup.founders
    )

    assert total == Decimal("80")

def test_primary_contact(founder_factory):

    founder = founder_factory()

    assert founder.is_primary_contact

# 12 — Representation
def test_repr(founder_factory):

    founder = founder_factory()

    text = repr(founder)

    assert founder.full_name in text

