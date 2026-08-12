"""
Embedding framework.

This package provides abstractions and implementations for generating
vector embeddings from documents, chunks, and text.
"""

from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import EmbeddingFactory
from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)
from app.embeddings.sentence_transformers import (
    SentenceTransformerProvider,
)

__all__ = [
    "DocumentEmbedding",
    "EmbeddingFactory",
    "EmbeddingProvider",
    "EmbeddingVector",
    "SentenceTransformerProvider",
]
