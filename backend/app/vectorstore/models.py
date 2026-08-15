"""
Vector store domain models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from uuid import UUID

from app.embeddings.models import EmbeddingVector


@dataclass(slots=True, frozen=True)
class StoredVector:
    """
    Vector stored in a vector store.

    The vector is associated with the source document and chunk so
    retrieval can return the original content without requiring
    another lookup.
    """

    document_id: UUID
    vector: EmbeddingVector
    chunk_id: UUID | None = None
    text: str = ""
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )


@dataclass(slots=True, frozen=True)
class SearchRequest:
    """
    Vector similarity search request.
    """

    vector: EmbeddingVector

    top_k: int = 5

    threshold: float = 0.0


@dataclass(slots=True, frozen=True)
class SearchResult:
    """
    Result returned by a vector similarity search.
    """

    document_id: UUID

    chunk_id: UUID

    text: str

    similarity: float

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )
