"""
Base repository.

Provides common persistence operations shared by all repositories.

Repositories are responsible for database persistence only.
Business logic belongs in the service layer.

Transactions (commit/rollback) are managed by the service layer.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Base class for all repositories."""

    def __init__(self, session: Session) -> None:
        self._session = session


    @property
    def session(self) -> Session:
        """Return the underlying SQLAlchemy session."""
        return self._session

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(
        self,
        entity: ModelT,
    ) -> ModelT:
        """
        Add or update an entity.

        The entity is flushed but not committed.
        """

        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)

        return entity

    def remove(
        self,
        entity: ModelT,
    ) -> None:
        """
        Mark an entity for deletion.

        The deletion is flushed but not committed.
        """

        self._session.delete(entity)
        self._session.flush()

    def flush(self) -> None:
        """
        Flush all pending changes.

        Services remain responsible for commit/rollback.
        """

        self._session.flush()
