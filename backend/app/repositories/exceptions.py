"""
Repository exceptions.

Custom exceptions raised by the repository layer.

Repositories should raise these exceptions only for persistence-related
errors. Business validation belongs in the service layer.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """Base class for all repository exceptions."""


class EntityNotFoundError(RepositoryError):
    """Raised when the requested entity does not exist."""


class DuplicateEntityError(RepositoryError):
    """Raised when attempting to create a duplicate entity."""


class PersistenceError(RepositoryError):
    """Raised when a database persistence operation fails."""
