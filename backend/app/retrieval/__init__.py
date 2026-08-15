"""
Retrieval framework.

This package provides abstractions and implementations for semantic
retrieval over indexed document embeddings.
"""

from app.retrieval.base import Retriever
from app.retrieval.factory import RetrieverFactory
from app.retrieval.models import (
    Query,
    RetrievalResult,
    RetrievedChunk,
    RetrievedDocument,
)
from app.retrieval.semantic import SemanticRetriever

__all__ = [
    "Query",
    "RetrievedChunk",
    "RetrievedDocument",
    "RetrievalResult",
    "Retriever",
    "RetrieverFactory",
    "SemanticRetriever",
]
