"""
Vector store domain models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.embeddings.models import EmbeddingVector


@dataclass(slots=True, frozen=True)
class StoredVector:
    """
    Vector stored in the vector store.
    """

    document_id: UUID

    vector: EmbeddingVector

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )


@dataclass(slots=True, frozen=True)
class SearchRequest:
    """
    Search request submitted to a vector store.
    """

    vector: EmbeddingVector

    top_k: int = 5

    threshold: float = 0.0


@dataclass(slots=True, frozen=True)
class SearchResult:
    """
    Result returned from a vector search.
    """

    document_id: UUID

    similarity: float

    vector: EmbeddingVector

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    @property
    def score(self) -> float:
        """
        Alias for similarity.
        """
        return self.similarity
