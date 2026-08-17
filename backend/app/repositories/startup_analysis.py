"""
Startup analysis repository.

Database access layer for StartupAnalysis entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
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

    def get_by_startup_and_id(
        self,
        startup_id: UUID,
        analysis_id: UUID,
    ) -> StartupAnalysis | None:
        """
        Return a startup analysis belonging to a specific startup.

        The startup_id constraint is intentionally part of the database
        query so an analysis belonging to another startup cannot be
        returned through this history API boundary.
        """

        stmt = select(StartupAnalysis).where(
            StartupAnalysis.id == analysis_id,
            StartupAnalysis.startup_id == startup_id,
        )

        return self.session.scalar(stmt)

    def list_by_startup(
        self,
        startup_id: UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[StartupAnalysis], int]:
        """
        Return paginated analysis history for a startup.

        Results are ordered newest first by created_at.

        Returns
        -------
        tuple[list[StartupAnalysis], int]
            The requested page of analyses and the total number of
            matching analyses.
        """

        count_stmt = (
            select(func.count())
            .select_from(StartupAnalysis)
            .where(
                StartupAnalysis.startup_id == startup_id,
            )
        )

        total_items = self.session.scalar(count_stmt) or 0

        offset = (page - 1) * per_page

        stmt = (
            select(StartupAnalysis)
            .where(
                StartupAnalysis.startup_id == startup_id,
            )
            .order_by(
                StartupAnalysis.created_at.desc(),
                StartupAnalysis.id.desc(),
            )
            .offset(offset)
            .limit(per_page)
        )

        items = list(self.session.scalars(stmt).all())

        return items, total_items

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
