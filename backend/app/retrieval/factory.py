"""
Retriever factory.
"""

from __future__ import annotations

from app.retrieval.base import Retriever
from app.retrieval.semantic import SemanticRetriever
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearchService


class RetrieverFactory:
    """
    Factory for retriever implementations.

    The factory manages a single active retriever implementation,
    allowing semantic, hybrid, keyword, or future retrieval
    strategies to be plugged in without changing application code.
    """

    DEFAULT_RETRIEVER = SemanticRetriever

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_search_service: VectorSearchService | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        if retriever is not None:
            self._retriever = retriever
        else:
            if embedding_service is None:
                raise ValueError(
                    "embedding_service is required "
                    "when retriever is not provided."
                )

            if vector_search_service is None:
                raise ValueError(
                    "vector_search_service is required "
                    "when retriever is not provided."
                )

            self._retriever = self.DEFAULT_RETRIEVER(
                embedding_service=embedding_service,
                vector_search_service=vector_search_service,
            )

    @property
    def retriever(self) -> Retriever:
        """
        Return the active retriever.
        """
        return self._retriever

    @property
    def retriever_name(self) -> str:
        """
        Return the active retriever name.
        """
        return self._retriever.__class__.__name__

    def set_retriever(
        self,
        retriever: Retriever,
    ) -> None:
        """
        Replace the active retriever.
        """
        self._retriever = retriever
