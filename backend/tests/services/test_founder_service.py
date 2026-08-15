"""
Tests for FounderService.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.founder import FounderCreate, FounderUpdate
from app.services.founder import FounderService


class TestFounderService:
    """Test FounderService."""

    @staticmethod
    def _create_service(db_session):
        """Create service."""

        return FounderService(db_session)

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def test_create_founder(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Create founder."""

        startup = startup_factory()

        payload = FounderCreate(
            startup_id=startup.id,
            full_name="John Doe",
            designation="CEO",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
        )

        service = self._create_service(db_session)

        founder = service.create_founder(payload)

        assert founder.created_at is not None
        assert founder.id is not None
        assert founder.full_name == "John Doe"
        assert founder.email == "john@example.com"
        assert founder.startup_id == startup.id

    def test_create_duplicate_email(
        self,
        db_session,
        startup_factory,
        founder_factory,
    ) -> None:
        """Duplicate email should fail."""

        startup = startup_factory()

        founder_factory(
            startup=startup,
            email="john@example.com",
        )

        payload = FounderCreate(
            startup_id=startup.id,
            full_name="John Doe",
            designation="CEO",
            email="john@example.com",
            linkedin_url=None,
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.create_founder(payload)

    def test_create_unknown_startup(
        self,
        db_session,
    ) -> None:
        """Unknown startup should fail."""

        payload = FounderCreate(
            startup_id=uuid4(),
            full_name="John Doe",
            designation="CEO",
            email="john@example.com",
            linkedin_url=None,
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.create_founder(payload)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def test_get_founder(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Get founder."""

        founder = founder_factory()

        service = self._create_service(db_session)

        result = service.get_founder(founder.id)

        assert result == founder

    def test_get_unknown_founder(
        self,
        db_session,
    ) -> None:
        """Unknown founder."""

        service = self._create_service(db_session)

        assert service.get_founder(uuid4()) is None

    def test_list_founders(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """List founders."""

        founder_factory()
        founder_factory()

        service = self._create_service(db_session)

        founders = service.list_founders()

        assert len(founders) == 2

    def test_list_founders_by_startup(
        self,
        db_session,
        startup_factory,
        founder_factory,
    ) -> None:
        """List founders by startup."""

        startup1 = startup_factory()
        startup2 = startup_factory()

        founder_factory(startup=startup1)
        founder_factory(startup=startup1)
        founder_factory(startup=startup2)

        service = self._create_service(db_session)

        founders = service.list_founders_by_startup(
            startup1.id,
        )

        assert all(
            founder.startup_id == startup1.id
            for founder in founders
        )


    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def test_update_founder(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Update founder."""

        founder = founder_factory()

        payload = FounderUpdate(
            designation="CTO",
        )

        service = self._create_service(db_session)

        updated = service.update_founder(
            founder.id,
            payload,
        )

        assert updated.designation == "CTO"
        assert updated.full_name == founder.full_name
        assert updated.email == founder.email

        reloaded = service.get_founder(
            founder.id,
        )
        assert reloaded.designation == "CTO"

    def test_update_unknown_founder(
        self,
        db_session,
    ) -> None:
        """Unknown founder."""

        payload = FounderUpdate(
            designation="CTO",
        )

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.update_founder(
                uuid4(),
                payload,
            )

    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    def test_delete_founder(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Delete founder."""

        founder = founder_factory()

        service = self._create_service(db_session)

        service.delete_founder(founder.id)

        assert service.get_founder(founder.id) is None
        assert len(service.list_founders()) == 0

    def test_delete_unknown_founder(
        self,
        db_session,
    ) -> None:
        """Unknown founder."""

        service = self._create_service(db_session)

        with pytest.raises(ValueError):
            service.delete_founder(uuid4())

    def test_update_duplicate_email(
        self,
        db_session,
        founder_factory,
    ):
        founder1 = founder_factory(
            email="one@example.com",
        )
    
        founder2 = founder_factory(
            email="two@example.com",
        )
    
        payload = FounderUpdate(
            email="one@example.com",
        )
    
        service = self._create_service(db_session)
    
        with pytest.raises(ValueError):
            service.update_founder(
                founder2.id,
                payload,
            )

    def test_list_founders_empty_startup(
        self,
        db_session,
        startup_factory,
    ):
        startup = startup_factory()
    
        service = self._create_service(db_session)
    
        assert (
            service.list_founders_by_startup(
                startup.id,
            )
            == []
        )
        
