"""
Retrieval service.

Coordinates semantic retrieval and context construction.
"""

from __future__ import annotations

from app.context.builder import ContextBuilder
from app.context.models import PromptContext
from app.retrieval.base import Retriever
from app.retrieval.models import Query


class RetrievalService:
    """
    Application service for end-to-end retrieval.

    Coordinates:
        Query
          ↓
        Retriever
          ↓
        RetrievedChunk[]
          ↓
        ContextBuilder
          ↓
        PromptContext
    """

    def __init__(
        self,
        *,
        retriever: Retriever,
        context_builder: ContextBuilder,
    ) -> None:
        self._retriever = retriever
        self._context_builder = context_builder

    @property
    def retriever(self) -> Retriever:
        """Return the configured retriever."""
        return self._retriever

    @property
    def context_builder(self) -> ContextBuilder:
        """Return the configured context builder."""
        return self._context_builder

    def retrieve(
        self,
        query: Query,
    ) -> PromptContext:
        """
        Retrieve relevant documents/chunks and build prompt context.
        """
    
        result = self._retriever.retrieve(query)
    
        chunks = tuple(
            chunk
            for document in result.documents
            for chunk in document.chunks
        )
    
        return self._context_builder.build(
            chunks,
            query=query.text,
        )
    
