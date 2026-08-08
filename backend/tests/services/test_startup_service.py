"""
Tests for StartupService.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.repositories.startup import StartupRepository
from app.services.startup import StartupService
from app.schemas.startup import StartupCreate
from app.schemas.startup import StartupUpdate


class TestStartupService:
    """Tests for StartupService."""

    # -------------------------------------------------------------------------
    # Fixtures
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_service(
        db_session,
    ) -> StartupService:
        """Create a StartupService."""

        repository = StartupRepository(db_session)

        return StartupService(
            repository=repository,
            session=db_session,
        )


    # Query methods: These simply verify delegation.
    
    def test_get_startup(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test retrieving a startup."""
    
        service = self._create_service(db_session)
    
        startup = startup_factory()
    
        result = service.get_startup(startup.id)
    
        assert result is not None
        assert result.id == startup.id
    
    def test_get_startup_not_found(
        self,
        db_session,
    ) -> None:
        """Unknown startup returns None."""
    
        service = self._create_service(db_session)
    
        assert service.get_startup(uuid4()) is None
    
    def test_list_startups(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """List startups."""
    
        service = self._create_service(db_session)
    
        startup_factory()
        startup_factory()
    
        startups = service.list_startups()
    
        assert len(startups) >= 2
    
    def test_search_startups(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Search startups."""
    
        service = self._create_service(db_session)
    
        startup_factory(
            name="Investment OS",
        )
    
        results = service.search_startups(
            "Investment",
        )
    
        assert len(results) == 1
    
    # Create
    
    def test_create_startup(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Create startup."""
    
        service = self._create_service(db_session)

        payload = StartupCreate(
            name="New Startup",
            stage=startup_factory().stage,
            status=startup_factory().status,
        )
        
        created = service.create_startup(payload)
        
        assert created.id is not None
        assert created.name == "New Startup"

    
    
    # Duplicate
    
    def test_create_duplicate_startup(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Duplicate startup names are rejected."""
    
        service = self._create_service(db_session)
    
        startup_factory(
            name="Duplicate",
        )

        duplicate = StartupCreate(
            name="Duplicate",
            stage=startup_factory().stage,
            status=startup_factory().status,
        )
        
        with pytest.raises(ValueError):
            service.create_startup(duplicate)
    
    
    # Update
    
    def test_update_startup(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Update startup."""
    
        service = self._create_service(db_session)
    
        startup = startup_factory()
    
        payload = StartupUpdate(
            description="Updated",
        )
        
        updated = service.update_startup(
            startup.id,
            payload,
        )
        
        assert updated.description == "Updated"
    
    
    
    # Delete
    
    def test_delete_startup(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Delete startup."""
    
        service = self._create_service(db_session)
    
        startup = startup_factory()

        service.delete_startup(startup.id)
        
        assert service.get_startup(startup.id) is None

    def test_update_unknown_startup(
        self,
        db_session,
    ):
        service = self._create_service(db_session)
    
        payload = StartupUpdate(
            description="Updated",
        )
    
        with pytest.raises(ValueError):
            service.update_startup(
                uuid4(),
                payload,
            )
    
    def test_delete_unknown_startup(
        self,
        db_session,
    ):
        service = self._create_service(db_session)
    
        with pytest.raises(ValueError):
            service.delete_startup(uuid4())
        
