"""
Tests for StartupRepository.
"""

from __future__ import annotations

from app.models.enums import StartupStatus
from app.models.startup import Startup
from app.repositories.startup import StartupRepository


class TestStartupRepository:
    """Tests for StartupRepository."""

    # -------------------------------------------------------------------------
    # Fixtures
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_repository(db_session) -> StartupRepository:
        """Create a StartupRepository instance."""

        return StartupRepository(db_session)

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def test_get_by_id(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test retrieving a startup by ID."""

        repository = self._create_repository(db_session)

        startup = startup_factory()

        result = repository.get_by_id(startup.id)

        assert result is not None
        assert result.id == startup.id

    def test_get_by_id_not_found(
        self,
        db_session,
    ) -> None:
        """Test retrieving a non-existent startup."""

        from uuid import uuid4

        repository = self._create_repository(db_session)

        assert repository.get_by_id(uuid4()) is None

    def test_get_by_name(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test retrieving a startup by name."""

        repository = self._create_repository(db_session)

        startup = startup_factory(name="Investment OS")

        result = repository.get_by_name("Investment OS")

        assert result is not None
        assert result.id == startup.id

    def test_exists_by_name(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test checking startup existence."""

        repository = self._create_repository(db_session)

        startup_factory(name="BigEndian")

        assert repository.exists_by_name("BigEndian") is True
        assert repository.exists_by_name("Unknown") is False

    def test_list_all(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test listing all startups."""

        repository = self._create_repository(db_session)

        startup_factory(name="Alpha")
        startup_factory(name="Beta")

        startups = repository.list_all()

        assert len(startups) >= 2

    def test_list_active(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test listing active startups."""

        repository = self._create_repository(db_session)

        startup_factory(
            name="Active Startup",
            status=StartupStatus.ACTIVE,
        )

        startup_factory(
            name="Archived Startup",
            status=StartupStatus.ARCHIVED,
        )

        startups = repository.list_active()

        assert all(
            startup.status == StartupStatus.ACTIVE
            for startup in startups
        )

    def test_find_by_sector(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test filtering startups by sector."""

        repository = self._create_repository(db_session)

        startup_factory(
            name="AI Startup",
            sector="AI",
        )

        startup_factory(
            name="Health Startup",
            sector="Healthcare",
        )

        startups = repository.find_by_sector("AI")

        assert len(startups) == 1
        assert startups[0].sector == "AI"

    def test_search(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test searching startups."""

        repository = self._create_repository(db_session)

        startup_factory(
            name="Investment OS",
            legal_name="Investment OS Private Limited",
        )

        results = repository.search("Investment")

        assert len(results) == 1
        assert results[0].name == "Investment OS"

    # -------------------------------------------------------------------------
    # Persistence Methods
    # -------------------------------------------------------------------------

    def test_create(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test creating a startup."""

        repository = self._create_repository(db_session)

        startup = startup_factory(
            name="Created Startup",
        )

        result = repository.create(startup)

        assert result.id == startup.id

    def test_update(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test updating a startup."""

        repository = self._create_repository(db_session)

        startup = startup_factory()

        startup.description = "Updated description"

        result = repository.update(startup)

        assert result.description == "Updated description"

    def test_delete(
        self,
        db_session,
        startup_factory,
    ) -> None:
        """Test deleting a startup."""

        repository = self._create_repository(db_session)

        startup = startup_factory()

        repository.delete(startup)

        assert repository.get_by_id(startup.id) is None

