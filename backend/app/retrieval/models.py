"""
Retrieval domain models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from uuid import UUID

from app.embeddings.models import EmbeddingVector

# ----------------------------------------------------------------------
# Query
# ----------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class Query:
    """
    Represents a semantic search query.
    """

    text: str

    embedding: EmbeddingVector | None = None

    top_k: int = 5

    threshold: float = 0.0


# ----------------------------------------------------------------------
# Retrieved Chunk
# ----------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class RetrievedChunk:
    """
    One retrieved chunk.
    """

    document_id: UUID

    chunk_id: UUID

    text: str

    similarity: float

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )


# ----------------------------------------------------------------------
# Retrieved Document
# ----------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class RetrievedDocument:
    """
    Retrieved document with one or more relevant chunks.
    """

    document_id: UUID

    score: float

    chunks: tuple[RetrievedChunk, ...] = ()

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    @property
    def chunk_count(self) -> int:
        """
        Return the number of retrieved chunks.
        """
        return len(self.chunks)
    
    
    @property
    def best_similarity(self) -> float:
        """
        Highest chunk similarity.
        """
        if not self.chunks:
            return 0.0
    
        return max(
            chunk.similarity
            for chunk in self.chunks
        )

# ----------------------------------------------------------------------
# Retrieval Result
# ----------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class RetrievalResult:
    """
    Complete retrieval result.
    """

    query: Query

    documents: tuple[RetrievedDocument, ...] = ()

    retrieval_time_ms: float = 0.0
