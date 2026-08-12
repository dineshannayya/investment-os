"""
Base interfaces for embedding providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.chunking.base import Chunk
from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)
from app.processors import DocumentContent


class EmbeddingProvider(ABC):
    """
    Base class for embedding providers.

    Implementations generate vector embeddings for text, chunks,
    and complete documents.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider/model name.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        Embedding vector dimension.
        """
        raise NotImplementedError

    #
    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------
    #

    @abstractmethod
    def embed_texts(
        self,
        texts: list[str],
    ) -> list[EmbeddingVector]:
        """
        Generate embeddings for multiple texts.
        """
        raise NotImplementedError

    #
    # ------------------------------------------------------------------
    # Convenience APIs
    # ------------------------------------------------------------------
    #

    def embed_text(
        self,
        text: str,
    ) -> EmbeddingVector:
        """
        Generate an embedding for a single text.
        """

        return self.embed_texts([text])[0]

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddingVector]:
        """
        Generate embeddings for document chunks.
        """

        return self.embed_texts(
            [chunk.text for chunk in chunks]
        )
    def embed_document(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> DocumentEmbedding:
        """
        Generate embeddings for an entire document.
        """
    
        chunk_embeddings = self.embed_chunks(chunks)
    
        document_embedding = self.embed_text(
            document.text
        )
    
        return DocumentEmbedding(
            document_id=document.document_id,
            model_name=self.name,
            dimensions=document_embedding.dimensions,
            document_embedding=document_embedding,
            chunk_embeddings=tuple(chunk_embeddings),
        )
