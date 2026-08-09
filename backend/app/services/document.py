"""
Document service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.repositories.startup import StartupRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
)


class DocumentService:
    """Business service for Document entities."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._startup_repository = StartupRepository(session)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_document_data(data: dict) -> dict:
        """Normalize schema data for ORM persistence."""

        return data

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_document(
        self,
        document_id: UUID,
    ) -> Document | None:
        """Return a document by ID."""

        return self._repository.get_by_id(document_id)

    def get_by_file_hash(
        self,
        file_hash: str,
    ) -> Document | None:
        """
        Return a document by file hash.
        """
    
        return self._repository.get_by_file_hash(file_hash)


    def list_documents(self) -> list[Document]:
        """Return all documents."""

        return self._repository.list_all()

    def list_documents_by_startup(
        self,
        startup_id: UUID,
    ) -> list[Document]:
        """Return all documents for a startup."""

        return self._repository.list_by_startup(startup_id)

    def search_documents(
        self,
        query: str,
    ) -> list[Document]:
        """Search documents by title."""

        return self._repository.search_title(query)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def create_document(
        self,
        payload: DocumentCreate,
    ) -> Document:
        """Create a document."""

        startup = self._startup_repository.get_by_id(
            payload.startup_id,
        )

        if startup is None:
            raise ValueError("Startup not found.")

        if self._repository.exists_by_hash(
            payload.file_hash,
        ):
            raise ValueError(
                "Document with the same file hash already exists."
            )

        data = self._normalize_document_data(
            payload.model_dump()
        )

        document = Document(**data)

        document = self._repository.create(document)

        self._session.commit()

        return document

    def update_document(
        self,
        document_id: UUID,
        payload: DocumentUpdate,
    ) -> Document:
        """Update a document."""

        document = self._repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Document not found.")

        updates = self._normalize_document_data(
            payload.model_dump(
                exclude_unset=True,
            )
        )

        if (
            "file_hash" in updates
            and updates["file_hash"] != document.file_hash
            and self._repository.exists_by_hash(
                updates["file_hash"]
            )
        ):
            raise ValueError(
                "Document with the same file hash already exists."
            )

        for field, value in updates.items():
            setattr(document, field, value)

        document = self._repository.update(document)

        self._session.commit()

        return document

    def delete_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete a document."""

        document = self._repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Document not found.")

        self._repository.delete(document)

        self._session.commit()
