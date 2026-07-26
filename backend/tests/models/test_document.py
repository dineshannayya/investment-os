# ------------------------------------------
# | Area                    |        Tests |
# | ----------------------- | -----------: |
# | ORM metadata            |            5 |
# | Factory                 |            3 |
# | Required fields         |            4 |
# | Foreign key             |            2 |
# | Document type enum      |            4 |
# | Status enum             |            4 |
# | UUID/Timestamps         |            3 |
# | Persistence             |            2 |
# | Updates                 |            1 |
# | Due diligence scenarios |            5 |
# | Representation          |            1 |
# | **Total**               | **34 tests** |
# -------------------------------------------

from app.models.enums import DocumentStatus, DocumentType

# Coverage
"""
Tests for Document ORM model.

Coverage

- ORM metadata
- Factory
- Foreign key
- Relationships
- Document type
- Document status
- File metadata
- UUID/Timestamps
- Persistence
- Updates
- Due diligence scenarios
"""

# Section 1 — ORM Metadata

from app.models import Document


def test_tablename():
    assert Document.__tablename__ == "documents"

def test_primary_key():
    assert Document.__table__.c.id.primary_key

def test_startup_fk_exists():
    assert "startup_id" in Document.__table__.columns

def test_created_at_exists():
    assert "created_at" in Document.__table__.columns

def test_updated_at_exists():
    assert "updated_at" in Document.__table__.columns

# Section 2 — Factory

def test_factory(document_factory):

    document = document_factory()

    assert document is not None

def test_factory_creates_startup(document_factory):

    document = document_factory()

    assert document.startup is not None

def test_factory_generates_uuid(document_factory):

    document = document_factory()

    assert document.id is not None

# Section 3 — Required Fields

def test_filename(document_factory):

    document = document_factory()

    assert document.filename

def test_storage_path(document_factory):

    document = document_factory()

    assert document.storage_path

def test_file_size(document_factory):

    document = document_factory()

    assert document.file_size > 0

def test_mime_type(document_factory):

    document = document_factory()

    assert document.mime_type

# Section 4 — Foreign Key

def test_document_has_startup(document_factory):

    document = document_factory()

    assert document.startup is not None

def test_startup_relationship(document_factory):

    document = document_factory()

    assert document in document.startup.documents

# Section 5 — Document Type Enum

def test_default_document_type(document_factory):

    document = document_factory()

    assert document.document_type == DocumentType.PITCH_DECK

def test_sha_document(document_factory):

    document = document_factory(
        document_type=DocumentType.SHA
    )

    assert document.document_type == DocumentType.SHA

def test_cap_table(document_factory):

    document = document_factory(
        document_type=DocumentType.CAP_TABLE
    )

    assert document.document_type == DocumentType.CAP_TABLE

def test_financial_model(document_factory):

    document = document_factory(
        document_type=DocumentType.FINANCIAL_MODEL
    )

    assert document.document_type == DocumentType.FINANCIAL_MODEL

#Section 6 — Status Enum

def test_default_status(document_factory):

    document = document_factory()

    assert document.status == DocumentStatus.UPLOADED

def test_processing(document_factory):

    document = document_factory(
        status=DocumentStatus.PROCESSING
    )

    assert document.status == DocumentStatus.PROCESSING

def test_processed(document_factory):

    document = document_factory(
        status=DocumentStatus.PROCESSED
    )

    assert document.status == DocumentStatus.PROCESSED

def test_failed(document_factory):

    document = document_factory(
        status=DocumentStatus.FAILED
    )

    assert document.status == DocumentStatus.FAILED

# Section 7 — UUID / Timestamp

from uuid import UUID


def test_uuid(document_factory):

    document = document_factory()

    assert isinstance(document.id, UUID)

def test_created_at(document_factory):

    document = document_factory()

    assert document.created_at is not None

def test_updated_at(document_factory):

    document = document_factory()

    assert document.updated_at is not None

# Section 8 — Persistence

def test_insert(
    db_session,
    document_factory,
):

    document = document_factory()

    db_session.flush()

    assert document.id is not None

def test_query(
    db_session,
    document_factory,
):

    document = document_factory()

    found = db_session.get(
        Document,
        document.id,
    )

    assert found == document

# Section 9 — Update
def test_update_filename(
    db_session,
    document_factory,
):

    document = document_factory()

    document.filename = "updated.pdf"

    db_session.flush()

    assert document.filename == "updated.pdf"


# Section 10 — Due Diligence Scenarios
# 
# This is where the model starts supporting your AI Due Diligence Agent.

# Missing SHA
def test_missing_sha_documents(
    missing_sha_documents,
):

    startup = missing_sha_documents()

    types = {
        doc.document_type
        for doc in startup.documents
    }

    assert DocumentType.SHA not in types

# Complete Package
def test_complete_due_diligence(
    complete_due_diligence,
):

    startup = complete_due_diligence()

    assert len(startup.documents) >= 5


# Pitch Deck Exists
def test_pitch_deck_exists(
    complete_due_diligence,
):

    startup = complete_due_diligence()

    assert any(
        d.document_type == DocumentType.PITCH_DECK
        for d in startup.documents
    )

#SHA Exists
def test_sha_exists(
    complete_due_diligence,
):

    startup = complete_due_diligence()

    assert any(
        d.document_type == DocumentType.SHA
        for d in startup.documents
    )

# Financial Model Exists
def test_financial_model_exists(
    complete_due_diligence,
):

    startup = complete_due_diligence()

    assert any(
        d.document_type == DocumentType.FINANCIAL_MODEL
        for d in startup.documents
    )

#Section 11 — Representation
def test_repr(document_factory):

    document = document_factory()

    text = repr(document)

    assert document.filename in text
