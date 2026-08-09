"""
Founder service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.founder import Founder
from app.repositories.founder import FounderRepository
from app.repositories.startup import StartupRepository
from app.schemas.founder import FounderCreate, FounderUpdate


class FounderService:
    """Business service for Founder entities."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = FounderRepository(session)
        self._startup_repository = StartupRepository(session)

    @staticmethod
    def _normalize_schema_data(
        data: dict,
    ) -> dict:
        if data.get("linkedin_url") is not None:
            data["linkedin_url"] = str(
                data["linkedin_url"]
            )
    
        return data


    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_founder(
        self,
        founder_id: UUID,
    ) -> Founder | None:
        """Return a founder by ID."""

        return self._repository.get_by_id(founder_id)

    def list_founders(self) -> list[Founder]:
        """Return all founders."""

        return self._repository.list_all()

    def list_founders_by_startup(
        self,
        startup_id: UUID,
    ) -> list[Founder]:
        """Return founders belonging to a startup."""

        return self._repository.list_by_startup(startup_id)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def create_founder(
        self,
        payload: FounderCreate,
    ) -> Founder:
        """Create a founder."""

        startup = self._startup_repository.get_by_id(
            payload.startup_id,
        )

        if startup is None:
            raise ValueError("Startup not found.")

        if (
            payload.email
            and self._repository.exists_by_email(payload.email)
        ):
            raise ValueError(
                f"Founder '{payload.email}' already exists."
            )

        data = self._normalize_schema_data( payload.model_dump())

        founder = Founder(**data)

        founder = self._repository.create(founder)

        self._session.commit()

        return founder

    def update_founder(
        self,
        founder_id: UUID,
        payload: FounderUpdate,
    ) -> Founder:
        """Update a founder."""

        founder = self._repository.get_by_id(founder_id)

        if founder is None:
            raise ValueError("Founder not found.")

        if (
            payload.email
            and payload.email != founder.email
            and self._repository.exists_by_email(payload.email)
        ):
            raise ValueError(
                f"Founder '{payload.email}' already exists."
            )

        updates = self._normalize_schema_data(
            payload.model_dump(
                exclude_unset=True,
            )
        )

        for field, value in updates.items():
            setattr(founder, field, value)


        founder = self._repository.update(founder)

        self._session.commit()

        return founder

    def delete_founder(
        self,
        founder_id: UUID,
    ) -> None:
        """Delete a founder."""

        founder = self._repository.get_by_id(founder_id)

        if founder is None:
            raise ValueError("Founder not found.")

        self._repository.delete(founder)

        self._session.commit()
