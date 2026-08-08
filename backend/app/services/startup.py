"""
Startup service.

Business logic for Startup entities.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.startup import Startup
from app.repositories.startup import StartupRepository


class StartupService:
    """Business service for Startup operations."""

    def __init__(
        self,
        repository: StartupRepository,
        session: Session,
    ) -> None:
        self._repository = repository
        self._session = session

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
        startup: Startup,
    ) -> Startup:
        """
        Create a startup.
        """
    
        if self._repository.exists_by_name(startup.name):
            raise ValueError(
                f"Startup '{startup.name}' already exists."
            )
    
        startup.name = startup.name.strip()
    
        startup = self._repository.create(startup)
    
        self._session.commit()
    
        return startup
    
    # Update
    
    def update_startup(
        self,
        startup: Startup,
    ) -> Startup:
        """
        Update startup.
        """
    
        startup = self._repository.update(startup)
    
        self._session.commit()
    
        return startup
    
    # Delete
    
    def delete_startup(
        self,
        startup: Startup,
    ) -> None:
        """
        Delete startup.
        """
    
        self._repository.delete(startup)
    
        self._session.commit()
