"""
In-memory vector store implementation.
"""

from __future__ import annotations

import math
from heapq import nlargest
from uuid import UUID

from app.vectorstore.base import VectorStore
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class MemoryVectorStore(VectorStore):
    """
    In-memory implementation of VectorStore.

    Intended for development, testing, and small datasets.
    """

    def __init__(self) -> None:
        self._vectors: dict[UUID, StoredVector] = {}

    #
    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    #

    def add(
        self,
        vector: StoredVector,
    ) -> None:

        self._vectors[vector.document_id] = vector

    #
    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------
    #

    def remove(
        self,
        document_id: UUID,
    ) -> bool:

        return (
            self._vectors.pop(document_id, None)
            is not None
        )

    def clear(self) -> None:

        self._vectors.clear()

    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    def get(
        self,
        document_id: UUID,
    ) -> StoredVector | None:

        return self._vectors.get(document_id)

    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:
    
        results: list[SearchResult] = []
    
        query = request.vector.values
    
        for stored in self._vectors.values():
    
            similarity = self._compute_similarity(
                query,
                stored.vector.values,
            )
    
            if similarity < request.threshold:
                continue
    
            results.append(
                SearchResult(
                    document_id=stored.document_id,
                    chunk_id=stored.chunk_id,
                    text=stored.text,
                    similarity=similarity,
                    metadata=stored.metadata,
                )
            )
    
        return nlargest(
            request.top_k,
            results,
            key=lambda r: r.similarity,
        )

    #
    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------
    #

    def count(self) -> int:

        return len(self._vectors)

    #
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    #

    @staticmethod
    def _compute_similarity(
        left: tuple[float, ...],
        right: tuple[float, ...],
    ) -> float:
        """
        Compute cosine similarity between two vectors.
        """

        if len(left) != len(right):
            raise ValueError(
                "Vector dimensions do not match."
            )

        dot = sum(a * b for a, b in zip(left, right))

        left_norm = math.sqrt(
            sum(a * a for a in left)
        )

        right_norm = math.sqrt(
            sum(b * b for b in right)
        )

        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0

        return dot / (left_norm * right_norm)
