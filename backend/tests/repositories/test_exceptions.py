"""
Tests for repository exceptions.
"""

from __future__ import annotations

import pytest

from app.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    PersistenceError,
    RepositoryError,
)


class TestRepositoryExceptions:
    """Tests for repository exception hierarchy."""

    # -------------------------------------------------------------------------
    # RepositoryError
    # -------------------------------------------------------------------------

    def test_repository_error(self) -> None:
        """RepositoryError should derive from Exception."""

        error = RepositoryError("Repository error")

        assert isinstance(error, Exception)
        assert str(error) == "Repository error"

    # -------------------------------------------------------------------------
    # EntityNotFoundError
    # -------------------------------------------------------------------------

    def test_entity_not_found_error(self) -> None:
        """EntityNotFoundError should derive from RepositoryError."""

        error = EntityNotFoundError("Entity not found")

        assert isinstance(error, RepositoryError)
        assert str(error) == "Entity not found"

    # -------------------------------------------------------------------------
    # DuplicateEntityError
    # -------------------------------------------------------------------------

    def test_duplicate_entity_error(self) -> None:
        """DuplicateEntityError should derive from RepositoryError."""

        error = DuplicateEntityError("Duplicate entity")

        assert isinstance(error, RepositoryError)
        assert str(error) == "Duplicate entity"

    # -------------------------------------------------------------------------
    # PersistenceError
    # -------------------------------------------------------------------------

    def test_persistence_error(self) -> None:
        """PersistenceError should derive from RepositoryError."""

        error = PersistenceError("Persistence error")

        assert isinstance(error, RepositoryError)
        assert str(error) == "Persistence error"

    # -------------------------------------------------------------------------
    # Raising Exceptions
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "exception_type",
        [
            RepositoryError,
            EntityNotFoundError,
            DuplicateEntityError,
            PersistenceError,
        ],
    )
    def test_raise_repository_exceptions(
        self,
        exception_type: type[RepositoryError],
    ) -> None:
        """Repository exceptions should be raisable."""

        with pytest.raises(exception_type):
            raise exception_type("Test exception")

