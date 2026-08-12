"""
Base interfaces for vector stores.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class VectorStore(ABC):
    """
    Base class for vector store implementations.

    Implementations are responsible for storing, indexing,
    and searching embedding vectors.
    """

    #
    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def add(
        self,
        vector: StoredVector,
    ) -> None:
        """
        Add or replace a stored vector.
        """
        raise NotImplementedError

    def add_many(
        self,
        vectors: list[StoredVector],
    ) -> None:
        """
        Add multiple vectors.
        """

        for vector in vectors:
            self.add(vector)

    #
    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def remove(
        self,
        document_id: UUID,
    ) -> bool:
        """
        Remove a vector by document identifier.

        Returns
        -------
        bool
            True if the vector existed.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all stored vectors.
        """
        raise NotImplementedError

    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def get(
        self,
        document_id: UUID,
    ) -> StoredVector | None:
        """
        Return a stored vector.
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:
        """
        Perform a similarity search.
        """
        raise NotImplementedError

    #
    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def count(self) -> int:
        """
        Return the number of stored vectors.
        """
        raise NotImplementedError

    def is_empty(self) -> bool:
        """
        Return True if the store contains no vectors.
        """

        return self.count() == 0
