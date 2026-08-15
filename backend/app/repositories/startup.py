"""
Startup repository.

Database access layer for Startup entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select

from app.models.enums import StartupStatus
from app.models.startup import Startup
from app.repositories.base import BaseRepository


class StartupRepository(BaseRepository[Startup]):
    """Repository for Startup persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        startup_id: UUID,
    ) -> Startup | None:
        """Return a startup by ID."""

        stmt = select(Startup).where(
            Startup.id == startup_id,
        )

        return self.session.scalar(stmt)

    def get_by_name(
        self,
        name: str,
    ) -> Startup | None:
        """Return startup by company name."""

        stmt = select(Startup).where(
            Startup.name == name,
        )

        return self.session.scalar(stmt)

    def exists_by_name(
        self,
        name: str,
    ) -> bool:
        """Check whether a startup exists."""

        return self.get_by_name(name) is not None

    def list_all(
        self,
    ) -> list[Startup]:
        """Return all startups."""

        stmt = (
            select(Startup)
            .order_by(Startup.name.asc())
        )

        return list(self.session.scalars(stmt))

    def list_active(
        self,
    ) -> list[Startup]:
        """Return active startups."""

        stmt = (
            select(Startup)
            .where(
                Startup.status == StartupStatus.ACTIVE,
            )
            .order_by(Startup.name)
        )

        return list(self.session.scalars(stmt))

    def find_by_sector(
        self,
        sector: str,
    ) -> list[Startup]:
        """Return startups within a sector."""

        stmt = (
            select(Startup)
            .where(
                Startup.sector == sector,
            )
            .order_by(Startup.name)
        )

        return list(self.session.scalars(stmt))

    def search(
        self,
        keyword: str,
    ) -> list[Startup]:
        """Search startups."""

        pattern = f"%{keyword}%"

        stmt = (
            select(Startup)
            .where(
                or_(
                    Startup.name.ilike(pattern),
                    Startup.legal_name.ilike(pattern),
                )
            )
            .order_by(Startup.name)
        )

        return list(self.session.scalars(stmt))

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def create(
        self,
        startup: Startup,
    ) -> Startup:
        """Persist a new startup."""

        return self.save(startup)

    def update(
        self,
        startup: Startup,
    ) -> Startup:
        """Persist startup changes."""

        return self.save(startup)

    def delete(
        self,
        startup: Startup,
    ) -> None:
        """Delete a startup."""

        self.remove(startup)
