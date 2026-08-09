"""
Startup service.

Business logic for Startup entities.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.startup import Startup
from app.repositories.startup import StartupRepository
from app.schemas.startup import StartupCreate


class StartupService:
    """Business service for Startup operations."""

    def __init__(self, session: Session):
        self._session = session
        self._repository = StartupRepository(session)

    # Query Operations
    
    def get_startup(
        self,
        startup_id,
    ) -> Startup | None:
        return self._repository.get_by_id(startup_id)
    
    
    def list_startups(
        self,
    ) -> list[Startup]:
        return self._repository.list_all()
    
    
    def list_active_startups(
        self,
    ) -> list[Startup]:
        return self._repository.list_active()
    
    
    def search_startups(
        self,
        keyword: str,
    ) -> list[Startup]:
        return self._repository.search(keyword)
    
    
    def find_by_sector(
        self,
        sector: str,
    ) -> list[Startup]:
        return self._repository.find_by_sector(sector)
    
    
    # Create : This is where business logic begins.

    def create_startup(
        self,
        payload: StartupCreate,
    ) -> Startup:
        """Create a startup."""
    
        name = payload.name.strip()
    
        if self._repository.exists_by_name(name):
            raise ValueError(
                f"Startup '{name}' already exists."
            )
    
        startup = Startup(
            **payload.model_dump()
        )
    
        startup.name = name
    
        startup = self._repository.create(startup)
    
        self._session.commit()
    
        return startup
    
    
    # Update
    def update_startup(
        self,
        startup_id: UUID,
        payload: StartupUpdate,
    ) -> Startup:
    
        startup = self._repository.get_by_id(startup_id)
    
        if startup is None:
            raise ValueError("Startup not found.")
    
        if (
            payload.name is not None
            and payload.name != startup.name
            and self._repository.exists_by_name(payload.name)
        ):
            raise ValueError("Startup already exists.")
    
        for field, value in payload.model_dump(
            exclude_unset=True,
        ).items():
            setattr(startup, field, value)
    
        startup = self._repository.update(startup)
    
        self._session.commit()
    
        return startup

    
    # Delete
    def delete_startup(
        self,
        startup_id: UUID,
    ) -> None:
    
        startup = self._repository.get_by_id(startup_id)
    
        if startup is None:
            raise ValueError("Startup not found.")
    
        self._repository.delete(startup)
    
        self._session.commit()    
