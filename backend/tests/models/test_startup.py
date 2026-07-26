# -----------------------------------------------
#
#   | Area            |     Tests |
#   | --------------- | --------: |
#   | Table metadata  |         5 |
#   | Factory         |         3 |
#   | Required fields |         3 |
#   | Enum handling   |         3 |
#   | UUID/Timestamps |         3 |
#   | Persistence     |         2 |
#   | Updates         |         1 |
#   | Relationships   |         3 |
#   | Constraints     |       1–3 |
#   | Representation  |         1 |
#   | Serialization   |         1 |
#   | **Total**       | **26–30** |
#
# -------------------------------------------------
"""
Tests for Startup ORM model.

Coverage

- Table metadata
- Default values
- Required fields
- Enum handling
- UUID/Timestamp mixins
- Constraints
- Relationships
- String representation
"""

# ------------------------------
# 1. ORM Metadata
# -----------------------------
from uuid import UUID

from app.models import Startup
from app.models.enums import StartupStage, StartupStatus


def test_tablename():
    assert Startup.__tablename__ == "startups"


def test_primary_key():
    assert Startup.__table__.c.id.primary_key


def test_uuid_column_exists():
    assert "id" in Startup.__table__.columns


def test_created_at_exists():
    assert "created_at" in Startup.__table__.columns


def test_updated_at_exists():
    assert "updated_at" in Startup.__table__.columns


# -------------------------------------
# 2.Factory
# -------------------------------------


def test_startup_factory(startup_factory):

    startup = startup_factory()

    assert startup is not None


def test_factory_generates_uuid(startup_factory):

    startup = startup_factory()

    assert startup.id is not None


def test_factory_sets_defaults(startup_factory):

    startup = startup_factory()

    assert startup.stage is not None
    assert startup.status is not None


# ----------------------------------
# 3. Required Fields
# ----------------------------------


def test_name_required(startup_factory):

    startup = startup_factory()

    assert startup.name


def test_sector_default(startup_factory):

    startup = startup_factory()

    assert startup.sector == "Semiconductor"


def test_headquarters_default(startup_factory):

    startup = startup_factory()

    assert startup.headquarters == "Bangalore"


# ----------------------------------------
# 4.Enum Tests
# ----------------------------------------
def test_stage_enum(startup_factory):

    startup = startup_factory()

    assert startup.stage == StartupStage.IDEA


def test_custom_stage(startup_factory):

    startup = startup_factory(stage=StartupStage.GROWTH)

    assert startup.stage == StartupStage.GROWTH


def test_status_enum(startup_factory):

    startup = startup_factory()

    assert startup.status == StartupStatus.ACTIVE


# ----------------------------------------------
# 5.UUID/Timestamps
# ----------------------------------------------


def test_uuid_type(startup_factory):

    startup = startup_factory()

    assert isinstance(startup.id, UUID)


def test_created_at(startup_factory):

    startup = startup_factory()

    assert startup.created_at is not None


def test_updated_at(startup_factory):

    startup = startup_factory()

    assert startup.updated_at is not None


# ----------------------------------
# 6.Persistence
# ----------------------------------


def test_insert(db_session, startup_factory):

    startup = startup_factory()

    db_session.flush()

    assert startup.id is not None


def test_query(db_session, startup_factory):

    startup = startup_factory()

    found = db_session.get(
        Startup,
        startup.id,
    )

    assert found == startup


# -----------------------------------
# 7. Update
# -----------------------------------
def test_update_name(
    db_session,
    startup_factory,
):

    startup = startup_factory()

    startup.name = "Updated"

    db_session.flush()

    assert startup.name == "Updated"


# --------------------------------
# 8. Relationships
# --------------------------------


def test_founders_relationship(
    startup_factory,
):

    startup = startup_factory()

    assert startup.founders == []


def test_documents_relationship(
    startup_factory,
):

    startup = startup_factory()

    assert startup.documents == []


def test_opportunities_relationship(
    startup_factory,
):

    startup = startup_factory()

    assert startup.opportunities == []


# ------------------------------------
# 9.Constraints
# ------------------------------------

# def test_unique_name(
#    db_session,
#    startup_factory,
# ):
#
#    startup_factory(name="OpenAI")
#
#    startup_factory(name="OpenAI")
#
#    with pytest.raises(IntegrityError):
#        db_session.flush()


# -------------------------------
# 10.Representation
# -------------------------------
def test_repr(startup_factory):

    startup = startup_factory()

    text = repr(startup)

    assert startup.name in text


# ------------------------------------
# 11. Serialization
# ------------------------------------


def test_model_dump(startup_factory):

    startup = startup_factory()

    data = startup.__dict__

    assert data["name"] == startup.name
