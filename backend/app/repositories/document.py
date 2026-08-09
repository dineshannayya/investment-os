"""
Document repository.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.enums import (
    DocumentStatus,
    DocumentType,
)
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Repository for Document entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        """Return a document by ID."""

        stmt = select(Document).where(
            Document.id == document_id,
        )

        return self.session.scalar(stmt)

    def get_by_file_hash(
        self,
        file_hash: str,
    ) -> Document | None:
        """
        Return document by file hash.
        """
    
        return (
            self._session.query(Document)
            .filter(Document.file_hash == file_hash)
            .first()
        )


    def list_all(self) -> list[Document]:
        """Return all documents."""

        stmt = (
            select(Document)
            .order_by(
                Document.created_at.desc(),
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def list_by_startup(
        self,
        startup_id: uuid.UUID,
    ) -> list[Document]:
        """Return all documents for a startup."""

        stmt = (
            select(Document)
            .where(
                Document.startup_id == startup_id,
            )
            .order_by(
                Document.created_at.desc(),
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------


    def exists_by_hash(
        self,
        file_hash: str,
    ) -> bool:
        """Return True if a document hash already exists."""

        return self.get_by_file_hash(file_hash) is not None

    def search_title(
        self,
        query: str,
    ) -> list[Document]:
        """Search documents by title."""

        stmt = (
            select(Document)
            .where(
                Document.title.ilike(f"%{query}%")
            )
            .order_by(
                Document.title.asc(),
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def list_by_type(
        self,
        document_type: DocumentType,
    ) -> list[Document]:
        """Return documents of a given type."""

        stmt = (
            select(Document)
            .where(
                Document.document_type == document_type,
            )
            .order_by(
                Document.created_at.desc(),
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    def list_by_status(
        self,
        status: DocumentStatus,
    ) -> list[Document]:
        """Return documents by processing status."""

        stmt = (
            select(Document)
            .where(
                Document.status == status,
            )
            .order_by(
                Document.created_at.desc(),
            )
        )

        return list(
            self.session.scalars(stmt)
        )

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def create(
        self,
        document: Document,
    ) -> Document:
        """Create a document."""

        return self.save(document)

    def update(
        self,
        document: Document,
    ) -> Document:
        """Update a document."""

        return self.save(document)

    def delete(
        self,
        document: Document,
    ) -> None:
        """Delete a document."""

        self.remove(document)
