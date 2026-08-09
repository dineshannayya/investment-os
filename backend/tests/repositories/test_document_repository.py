"""
Tests for DocumentRepository.
"""

from __future__ import annotations

import uuid

from app.models.enums import (
    DocumentStatus,
    DocumentType,
)
from app.repositories.document import DocumentRepository


class TestDocumentRepository:
    """Test DocumentRepository."""

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def test_get_by_id(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Get document by ID."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        result = repository.get_by_id(document.id)

        assert result == document

    def test_get_unknown_document(
        self,
        db_session,
    ) -> None:
        """Unknown document returns None."""

        repository = DocumentRepository(db_session)

        assert repository.get_by_id(uuid.uuid4()) is None

    def test_list_all(
        self,
        db_session,
        document_factory,
    ) -> None:
        """List all documents."""

        document_factory()
        document_factory()

        repository = DocumentRepository(db_session)

        documents = repository.list_all()

        assert len(documents) == 2

    def test_list_by_startup(
        self,
        db_session,
        startup_factory,
        document_factory,
    ) -> None:
        """List documents for a startup."""

        startup1 = startup_factory()
        startup2 = startup_factory()

        document_factory(startup=startup1)
        document_factory(startup=startup1)
        document_factory(startup=startup2)

        repository = DocumentRepository(db_session)

        documents = repository.list_by_startup(startup1.id)

        assert len(documents) == 2
        assert all(
            document.startup_id == startup1.id
            for document in documents
        )

    # -------------------------------------------------------------------------
    # Hash
    # -------------------------------------------------------------------------

    def test_get_by_file_hash(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Find document by file hash."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        found = repository.get_by_file_hash(
            document.file_hash,
        )

        assert found == document

    def test_find_unknown_hash(
        self,
        db_session,
    ) -> None:
        """Unknown hash returns None."""

        repository = DocumentRepository(db_session)

        assert (
            repository.get_by_file_hash(
                "unknown_hash",
            )
            is None
        )

    def test_exists_by_hash(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Existing hash returns True."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        assert repository.exists_by_hash(
            document.file_hash,
        )

    def test_exists_by_hash_false(
        self,
        db_session,
    ) -> None:
        """Unknown hash returns False."""

        repository = DocumentRepository(db_session)

        assert not repository.exists_by_hash(
            "unknown_hash",
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def test_search_title(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Search documents by title."""

        document_factory(title="Pitch Deck")
        document_factory(title="Financial Model")
        document_factory(title="Pitch Presentation")

        repository = DocumentRepository(db_session)

        documents = repository.search_title("Pitch")

        assert len(documents) == 2

    def test_search_title_no_match(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Search title with no match."""

        document_factory(title="Pitch Deck")

        repository = DocumentRepository(db_session)

        assert repository.search_title("Legal") == []

    # -------------------------------------------------------------------------
    # Type
    # -------------------------------------------------------------------------

    def test_list_by_type(
        self,
        db_session,
        document_factory,
    ) -> None:
        """List documents by type."""

        document_factory(
            document_type=DocumentType.PITCH_DECK,
        )

        document_factory(
            document_type=DocumentType.PITCH_DECK,
        )

        document_factory(
            document_type=DocumentType.FINANCIAL_MODEL,
        )

        repository = DocumentRepository(db_session)

        documents = repository.list_by_type(
            DocumentType.PITCH_DECK,
        )

        assert len(documents) == 2

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def test_list_by_status(
        self,
        db_session,
        document_factory,
    ) -> None:
        """List documents by status."""

        document_factory(
            status=DocumentStatus.UPLOADED,
        )

        document_factory(
            status=DocumentStatus.UPLOADED,
        )

        document_factory(
            status=DocumentStatus.PROCESSING,
        )

        repository = DocumentRepository(db_session)

        documents = repository.list_by_status(
            DocumentStatus.UPLOADED,
        )

        assert len(documents) == 2

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def test_create_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Create document."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        found = repository.get_by_id(document.id)

        assert found is not None

    def test_update_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Update document."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        document.title = "Updated Title"

        repository.update(document)

        updated = repository.get_by_id(document.id)

        assert updated.title == "Updated Title"

    def test_delete_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Delete document."""

        document = document_factory()

        repository = DocumentRepository(db_session)

        repository.delete(document)

        assert repository.get_by_id(document.id) is None
