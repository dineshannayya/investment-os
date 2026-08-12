"""
Vector search service.
"""

from __future__ import annotations

from uuid import UUID

from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)
from app.vectorstore import (
    SearchRequest,
    SearchResult,
    StoredVector,
    VectorStoreFactory,
)


class VectorSearchService:
    """
    Service responsible for indexing and searching embeddings.
    """

    def __init__(
        self,
        factory: VectorStoreFactory,
    ) -> None:
        self._factory = factory

    @property
    def factory(self) -> VectorStoreFactory:
        """
        Return the configured vector store factory.
        """
        return self._factory

    @property
    def store(self):
        """
        Return the active vector store.
        """
        return self._factory.store

    #
    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    #

    def index_document(
        self,
        embedding: DocumentEmbedding,
    ) -> None:
        """
        Index a document embedding.
        """

        stored = StoredVector(
            document_id=embedding.document_id,
            vector=embedding.document_embedding,
        )

        self.store.add(stored)

    def index_documents(
        self,
        embeddings: list[DocumentEmbedding],
    ) -> None:
        """
        Index multiple document embeddings.
        """

        vectors = [
            StoredVector(
                document_id=e.document_id,
                vector=e.document_embedding,
            )
            for e in embeddings
        ]

        self.store.add_many(vectors)

    #
    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------
    #

    def remove_document(
        self,
        document_id: UUID,
    ) -> bool:
        """
        Remove a document from the vector store.
        """

        return self.store.remove(document_id)

    def clear(self) -> None:
        """
        Remove all indexed vectors.
        """

        self.store.clear()

    #
    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    #

    def search(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[SearchResult]:
        """
        Search for similar vectors.
        """

        request = SearchRequest(
            vector=vector,
            top_k=top_k,
            threshold=threshold,
        )

        return self.store.search(request)

    #
    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------
    #

    def count(self) -> int:
        """
        Return the number of indexed vectors.
        """

        return self.store.count()

    def is_empty(self) -> bool:
        """
        Return True if the vector store is empty.
        """

        return self.store.is_empty()

    def similar_documents(
        self,
        embedding: DocumentEmbedding,
        *,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[SearchResult]:
        """
        Find documents similar to the supplied document embedding.
        """
    
        return self.search(
            embedding.document_embedding,
            top_k=top_k,
            threshold=threshold,
        )
    
