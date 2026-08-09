"""
Founder repository.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.founder import Founder
from app.repositories.base import BaseRepository


class FounderRepository(BaseRepository[Founder]):
    """Repository for Founder entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)


    # ------------------------------------------------------------------
    # Lookup Methods
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        founder_id: UUID,
    ) -> Founder | None:
        """Return a founder by ID."""

        stmt = select(Founder).where(
            Founder.id == founder_id,
        )
        return self.session.scalar(stmt)


    def list_all(self) -> list[Founder]:
        """Return all founders."""

        statement = (
            select(Founder)
            .order_by(Founder.full_name.asc())
        )

        return list(
            self.session.scalars(statement)
        )

    def list_by_startup(
        self,
        startup_id: UUID,
    ) -> list[Founder]:
        """Return founders belonging to a startup."""

        statement = (
            select(Founder)
            .where(
                Founder.startup_id == startup_id,
            )
            .order_by(
                Founder.created_at.asc(),
            )
        )

        return list(
            self.session.scalars(statement)
        )

    # ------------------------------------------------------------------
    # Search Helpers
    # ------------------------------------------------------------------

    def exists_by_email(
        self,
        email: str,
    ) -> bool:
        """Return True if a founder email already exists."""

        statement = (
            select(Founder.id)
            .where(
                Founder.email == email,
            )
            .limit(1)
        )

        return (
            self.session.scalar(statement)
            is not None
        )

    def find_by_email(
        self,
        email: str,
    ) -> Founder | None:
        """Return founder by email."""

        statement = (
            select(Founder)
            .where(
                Founder.email == email,
            )
        )

        return self.session.scalar(statement)

    def search(
        self,
        query: str,
    ) -> list[Founder]:
        """Search founders by name."""

        pattern = f"%{query}%"
        
        stmt = (
            select(Founder)
            .where(
                Founder.full_name.ilike(pattern)
            )
            .order_by(Founder.full_name)
        )
        
        return list(self.session.scalars(stmt))



    def create(
        self,
        founder: Founder,
    ) -> Founder:
        return self.save(founder)
    
    
    def update(
        self,
        founder: Founder,
    ) -> Founder:
        return self.save(founder)
    
    
    def delete(
        self,
        founder: Founder,
    ) -> None:
        self.remove(founder)
    
