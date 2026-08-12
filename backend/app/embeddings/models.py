"""
Embedding domain models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True, frozen=True)
class EmbeddingVector:
    """
    Represents a single embedding vector.
    """

    values: tuple[float, ...]

    model_name: str

    dimensions: int

    confidence: float = 1.0


@dataclass(slots=True, frozen=True)
class DocumentEmbedding:
    """
    Embeddings generated for a processed document.
    """

    document_id: UUID

    model_name: str

    dimensions: int

    document_embedding: EmbeddingVector

    chunk_embeddings: tuple[EmbeddingVector, ...] = field(
        default_factory=tuple,
    )
