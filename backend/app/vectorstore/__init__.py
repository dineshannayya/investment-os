"""
Vector store framework.

This package provides abstractions and implementations for storing,
indexing, and searching embedding vectors.
"""

from app.vectorstore.base import VectorStore
from app.vectorstore.factory import VectorStoreFactory
from app.vectorstore.memory import MemoryVectorStore
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)

__all__ = [
    "MemoryVectorStore",
    "SearchRequest",
    "SearchResult",
    "StoredVector",
    "VectorStore",
    "VectorStoreFactory",
]
