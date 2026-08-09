"""
Tests for DocumentService.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
)
from app.services.document import DocumentService


class TestDocumentService:
    """Test DocumentService."""

    @staticmethod
    def _create_service(db_session):
        """Create service."""

        return DocumentService(db_session)

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def test_create_document(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Create document."""

        startup = startup_factory()

        payload = DocumentCreate(
            startup_id=startup.id,
            document_type="PITCH_DECK",
            title="Pitch Deck",
            filename="pitch.pdf",
            original_filename="pitch.pdf",
            mime_type="application/pdf",
            file_size=12345,
            file_hash="hash-001",
            storage_path="/tmp/pitch.pdf",
        )

        service = self._create_service(db_session)

        document = service.create_document(payload)

        assert document.id is not None
        assert document.title == "Pitch Deck"
        assert document.file_hash == "hash-001"
        assert document.startup_id == startup.id

    def test_create_duplicate_hash(
        self,
        db_session,
        startup_factory,
        document_factory,
    ) -> None:
        """Duplicate file hash should fail."""

        startup = startup_factory()

        document_factory(
            startup=startup,
            file_hash="duplicate-hash",
        )

        payload = DocumentCreate(
            startup_id=startup.id,
            document_type="PITCH_DECK",
            title="Pitch Deck",
            filename="pitch.pdf",
            original_filename="pitch.pdf",
            mime_type="application/pdf",
            file_size=12345,
            file_hash="duplicate-hash",
            storage_path="/tmp/pitch.pdf",
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.create_document(payload)

    def test_create_unknown_startup(
        self,
        db_session,
    ) -> None:
        """Unknown startup should fail."""

        payload = DocumentCreate(
            startup_id=uuid4(),
            document_type="PITCH_DECK",
            title="Pitch Deck",
            filename="pitch.pdf",
            original_filename="pitch.pdf",
            mime_type="application/pdf",
            file_size=12345,
            file_hash="hash-001",
            storage_path="/tmp/pitch.pdf",
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.create_document(payload)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def test_get_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Get document."""

        document = document_factory()

        service = self._create_service(db_session)

        result = service.get_document(document.id)

        assert result == document

    def test_get_unknown_document(
        self,
        db_session,
    ) -> None:
        """Unknown document."""

        service = self._create_service(db_session)

        assert service.get_document(uuid4()) is None

    def test_list_documents(
        self,
        db_session,
        document_factory,
    ) -> None:
        """List documents."""

        document_factory()
        document_factory()

        service = self._create_service(db_session)

        documents = service.list_documents()

        assert len(documents) == 2

    def test_list_documents_by_startup(
        self,
        db_session,
        startup_factory,
        document_factory,
    ) -> None:
        """List documents by startup."""

        startup1 = startup_factory()
        startup2 = startup_factory()

        document_factory(startup=startup1)
        document_factory(startup=startup1)
        document_factory(startup=startup2)

        service = self._create_service(db_session)

        documents = service.list_documents_by_startup(startup1.id)

        assert len(documents) == 2
        assert all(
            doc.startup_id == startup1.id
            for doc in documents
        )

    def test_search_documents(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Search documents."""

        document_factory(title="Pitch Deck")
        document_factory(title="Financial Model")

        service = self._create_service(db_session)

        documents = service.search_documents("Pitch")

        assert len(documents) == 1

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def test_update_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Update document."""

        document = document_factory()

        payload = DocumentUpdate(
            title="Updated Pitch Deck",
        )

        service = self._create_service(db_session)

        updated = service.update_document(
            document.id,
            payload,
        )

        assert updated.title == "Updated Pitch Deck"

    def test_update_duplicate_hash(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Duplicate hash should fail."""

        doc1 = document_factory(
            file_hash="hash-001",
        )

        doc2 = document_factory(
            file_hash="hash-002",
        )

        payload = DocumentUpdate(
            file_hash="hash-001",
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.update_document(
                doc2.id,
                payload,
            )

    def test_update_unknown_document(
        self,
        db_session,
    ) -> None:
        """Unknown document."""

        payload = DocumentUpdate(
            title="Updated",
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.update_document(
                uuid4(),
                payload,
            )

    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    def test_delete_document(
        self,
        db_session,
        document_factory,
    ) -> None:
        """Delete document."""

        document = document_factory()

        service = self._create_service(db_session)

        service.delete_document(document.id)

        assert service.get_document(document.id) is None

    def test_delete_unknown_document(
        self,
        db_session,
    ) -> None:
        """Unknown document."""

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.delete_document(uuid4())
