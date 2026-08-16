"""
Startup analysis repository.

Database access layer for StartupAnalysis entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import StartupAnalysis
from app.repositories.base import BaseRepository


class StartupAnalysisRepository(BaseRepository[StartupAnalysis]):
    """Repository for StartupAnalysis persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        analysis_id: UUID,
    ) -> StartupAnalysis | None:
        """Return a startup analysis by ID."""

        stmt = select(StartupAnalysis).where(
            StartupAnalysis.id == analysis_id,
        )

        return self.session.scalar(stmt)

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def create(
        self,
        analysis: StartupAnalysis,
    ) -> StartupAnalysis:
        """Persist a new startup analysis."""

        return self.save(analysis)

    def update(
        self,
        analysis: StartupAnalysis,
    ) -> StartupAnalysis:
        """Persist startup analysis changes."""

        return self.save(analysis)

    def delete(
        self,
        analysis: StartupAnalysis,
    ) -> None:
        """Delete a startup analysis."""

        self.remove(analysis)
