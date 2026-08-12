"""
Base interfaces for retrieval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.retrieval.models import (
    Query,
    RetrievedChunk,
    RetrievedDocument,
    RetrievalResult,
)


class Retriever(ABC):
    """
    Base class for retrieval implementations.

    A retriever is responsible for locating the most relevant
    document chunks for a semantic query.
    """

    @property
    def supports_filters(self) -> bool:
        """
        Return True if the retriever supports metadata filtering.
        """
        return False


    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def retrieve(
        self,
        query: Query,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        """
        raise NotImplementedError

    #
    # ------------------------------------------------------------------
    # Convenience Methods
    # ------------------------------------------------------------------
    #

    def retrieve_documents(
        self,
        query: Query,
    ) -> tuple[RetrievedDocument, ...]:
        """
        Retrieve matching documents.
        """

        return self.retrieve(query).documents

    def retrieve_chunks(
        self,
        query: Query,
    ) -> tuple[RetrievedChunk, ...]:
        """
        Retrieve all matching chunks.
        """

        chunks: list[RetrievedChunk] = []

        for document in self.retrieve(query).documents:
            chunks.extend(document.chunks)

        return tuple(chunks)
