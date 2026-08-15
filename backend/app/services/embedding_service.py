"""
Embedding service.
"""

from __future__ import annotations

from app.chunking.base import Chunk
from app.embeddings import (
    DocumentEmbedding,
    EmbeddingFactory,
    EmbeddingProvider,
)
from app.processors import DocumentContent


class EmbeddingService:
    """
    Service responsible for generating document embeddings.

    The service delegates embedding generation to the configured
    EmbeddingProvider.
    """

    def __init__(
        self,
        factory: EmbeddingFactory,
    ) -> None:
        self._factory = factory

    @property
    def factory(self) -> EmbeddingFactory:
        """
        Return the configured embedding factory.
        """
        return self._factory

    @property
    def provider(self) -> EmbeddingProvider:
        """
        Return the active embedding provider.
        """
        return self._factory.provider

    def embed(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> DocumentEmbedding:
        """
        Generate embeddings for a processed document.

        Parameters
        ----------
        document:
            Processed document.

        chunks:
            Document chunks.

        Returns
        -------
        DocumentEmbedding
            Document-level and chunk-level embeddings.
        """

        return self.provider.embed_document(
            document=document,
            chunks=chunks,
        )

    def embed_text(
        self,
        text: str,
    ):
        """
        Generate an embedding for a single text.
        """

        return self.provider.embed_text(text)

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ):
        """
        Generate embeddings for document chunks.
        """

        return self.provider.embed_chunks(chunks)

    def embed_query(
        self,
        query: str,
    ):
        """
        Generate an embedding for a search query.
        """
    
        return self.provider.embed_text(query)

