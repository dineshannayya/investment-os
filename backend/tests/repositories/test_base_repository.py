"""
Tests for BaseRepository.
"""

from __future__ import annotations

from app.repositories.base import BaseRepository

# Test class

class TestBaseRepository:
    """Tests for the generic repository."""

    # 1. Constructor
    
    def test_initialization(self, db_session):
        """Repository stores the SQLAlchemy session."""
    
        repository = BaseRepository(db_session)
    
        assert repository.session is db_session
    
    # 2. Save
    
    def test_save_entity(
        self,
        db_session,
        role_factory,
    ):
        """Save persists an entity."""
    
        repository = BaseRepository(db_session)
    
        role = role_factory(
            name="repository-test",
            display_name="Repository Test",
        )
    
        role.description = "Updated"
    
        saved = repository.save(role)
    
        assert saved is role
        assert saved.description == "Updated"
    
    # 3. Flush
    
    def test_flush(
        self,
        db_session,
    ):
        """Flush executes without error."""
    
        repository = BaseRepository(db_session)
    
        repository.flush()
    
    # 4. Remove
    
    def test_remove_entity(
        self,
        db_session,
        role_factory,
    ):
        """Remove deletes an entity."""
    
        repository = BaseRepository(db_session)
    
        role = role_factory(
            name="delete-test",
            display_name="Delete Test",
        )
    
        repository.remove(role)
    
        assert db_session.get(type(role), role.id) is None
    
    # 5. Save after modification
    
    def test_save_updates_existing_entity(
        self,
        db_session,
        role_factory,
    ):
        """Save persists modifications."""
    
        repository = BaseRepository(db_session)
    
        role = role_factory(
            name="update-test",
            display_name="Update Test",
        )
    
        role.display_name = "Updated"
    
        repository.save(role)
    
        refreshed = db_session.get(type(role), role.id)
    
        assert refreshed is not None
        assert refreshed.display_name == "Updated"


