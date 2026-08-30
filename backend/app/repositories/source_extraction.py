"""
Source extraction repository.

Repositories are responsible for database persistence only.

Business logic belongs in the service layer.
Transactions (commit/rollback) are managed by the service layer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_extraction_orm import SourceExtractionORM
from app.repositories.base import BaseRepository


class SourceExtractionRepository(BaseRepository):
    """Repository for SourceExtractionORM entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        extraction_id: uuid.UUID,
    ) -> SourceExtractionORM | None:
        """Return an extraction by ID."""

        stmt = select(SourceExtractionORM).where(
            SourceExtractionORM.id == extraction_id,
        )

        return self.session.scalar(stmt)

    def get_by_source_version(
        self,
        source_id: uuid.UUID,
        source_sha256: str,
    ) -> SourceExtractionORM | None:
        """
        Return the extraction for an exact source version.

        A source version is uniquely identified by:

            source_id + source_sha256
        """

        stmt = select(SourceExtractionORM).where(
            SourceExtractionORM.source_id == source_id,
            SourceExtractionORM.source_sha256 == source_sha256,
        )

        return self.session.scalar(stmt)

    def get_latest_by_source_id(
        self,
        source_id: uuid.UUID,
    ) -> SourceExtractionORM | None:
        """
        Return the newest extraction record for a source.

        A source may have multiple persisted extraction records
        across refreshes or source versions.

        Newest is determined by:

            updated_at DESC
            created_at DESC
        """

        stmt = (
            select(SourceExtractionORM)
            .where(
                SourceExtractionORM.source_id == source_id,
            )
            .order_by(
                SourceExtractionORM.updated_at.desc(),
                SourceExtractionORM.created_at.desc(),
            )
            .limit(1)
        )

        return self.session.scalar(stmt)

    def get_latest_by_source_sha256(
        self,
        source_sha256: str,
    ) -> SourceExtractionORM | None:
        """
        Return the newest extraction record for an exact source SHA256.
    
        This lookup is useful when downstream document processing knows
        the content hash but does not have the source_id.
        """
    
        stmt = (
            select(SourceExtractionORM)
            .where(
                SourceExtractionORM.source_sha256 == source_sha256,
            )
            .order_by(
                SourceExtractionORM.updated_at.desc(),
                SourceExtractionORM.created_at.desc(),
            )
            .limit(1)
        )
    
        return self.session.scalar(stmt)


    # -------------------------------------------------------------------------
    # Existence
    # -------------------------------------------------------------------------

    def exists_by_source_version(
        self,
        source_id: uuid.UUID,
        source_sha256: str,
    ) -> bool:
        """Return True if an extraction exists for the source version."""

        return (
            self.get_by_source_version(
                source_id=source_id,
                source_sha256=source_sha256,
            )
            is not None
        )

    # -------------------------------------------------------------------------
    # Source history
    # -------------------------------------------------------------------------

    def list_by_source(
        self,
        source_id: uuid.UUID,
    ) -> list[SourceExtractionORM]:
        """
        Return all extraction records for a source.

        Newest extraction records are returned first.
        """

        stmt = (
            select(SourceExtractionORM)
            .where(
                SourceExtractionORM.source_id == source_id,
            )
            .order_by(
                SourceExtractionORM.created_at.desc(),
            )
        )

        return list(self.session.scalars(stmt))

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def create(
        self,
        extraction: SourceExtractionORM,
    ) -> SourceExtractionORM:
        """Create a source extraction."""

        return self.save(extraction)

    def update(
        self,
        extraction: SourceExtractionORM,
    ) -> SourceExtractionORM:
        """Update a source extraction."""

        return self.save(extraction)

    def delete(
        self,
        extraction: SourceExtractionORM,
    ) -> None:
        """Delete a source extraction."""

        self.remove(extraction)
