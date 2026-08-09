"""
Tests for FounderRepository.
"""

from __future__ import annotations

from app.models.founder import Founder
from app.repositories.founder import FounderRepository
from uuid import uuid4

class TestFounderRepository:
    """Test FounderRepository."""

    def test_create_founder(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Create founder."""

        founder = founder_factory()

        repository = FounderRepository(db_session)

        found = repository.get_by_id(founder.id)

        assert found is not None
        assert found.id == founder.id

    def test_get_by_id(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Get founder by id."""

        founder = founder_factory()

        repository = FounderRepository(db_session)

        result = repository.get_by_id(founder.id)

        assert result == founder

    def test_get_unknown_founder(
        self,
        db_session,
    ):
        repository = FounderRepository(db_session)
    
        assert repository.get_by_id(uuid4()) is None


    def test_list_all(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """List all founders."""

        founder_factory()
        founder_factory()

        repository = FounderRepository(db_session)

        founders = repository.list_all()

        assert len(founders) == 2

    def test_list_by_startup(
        self,
        db_session,
        founder_factory,
        startup_factory,
    ) -> None:
        """List founders belonging to one startup."""

        startup1 = startup_factory()
        startup2 = startup_factory()

        founder1 = founder_factory(startup=startup1)
        founder2 = founder_factory(startup=startup1)

        founder_factory(startup=startup2)

        repository = FounderRepository(db_session)

        founders = repository.list_by_startup(startup1.id)

        assert len(founders) == 2
        assert founder1 in founders
        assert founder2 in founders

    def test_find_by_email(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Find founder by email."""

        founder = founder_factory()

        repository = FounderRepository(db_session)

        found = repository.find_by_email(founder.email)

        assert found == founder

    def test_find_unknown_email(
        self,
        db_session,
    ) -> None:
        """Unknown email returns None."""

        repository = FounderRepository(db_session)

        assert repository.find_by_email(
            "missing@example.com",
        ) is None

    def test_exists_by_email(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Existing email returns True."""

        founder = founder_factory()

        repository = FounderRepository(db_session)

        assert repository.exists_by_email(
            founder.email,
        )

    def test_exists_by_email_false(
        self,
        db_session,
    ) -> None:
        """Unknown email returns False."""

        repository = FounderRepository(db_session)

        assert not repository.exists_by_email(
            "missing@example.com",
        )

    def test_search(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Search founders by name."""

        founder_factory(full_name="Alice Johnson")
        founder_factory(full_name="Bob Smith")
        founder_factory(full_name="Alice Brown")

        repository = FounderRepository(db_session)

        results = repository.search("Alice")

        assert len(results) == 2

    def test_search_no_match(
        self,
        db_session,
        founder_factory,
    ) -> None:
        """Search with no matches."""

        founder_factory(full_name="Alice")

        repository = FounderRepository(db_session)

        assert repository.search("Charlie") == []
