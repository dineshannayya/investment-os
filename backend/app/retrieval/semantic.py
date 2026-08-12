"""
Semantic retriever implementation.
"""

from __future__ import annotations

from time import perf_counter
from types import MappingProxyType

from app.embeddings.models import EmbeddingVector
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearchService
from app.retrieval.base import Retriever
from app.retrieval.models import (
    Query,
    RetrievedChunk,
    RetrievedDocument,
    RetrievalResult,
)


class SemanticRetriever(Retriever):
    """
    Retriever based on semantic vector similarity.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_search_service: VectorSearchService,
    ) -> None:

        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """
        Return the embedding service.
        """

        return self._embedding_service

    @property
    def vector_search_service(self) -> VectorSearchService:
        """
        Return the vector search service.
        """

        return self._vector_search_service

    def retrieve(
        self,
        query: Query,
    ) -> RetrievalResult:
        """
        Retrieve documents semantically similar to the query.
        """

        start = perf_counter()

        embedding = (
            query.embedding
            if query.embedding is not None
            else self.embedding_service.embed_text(
                query.text,
            )
        )

        results = self.vector_search_service.search(
            embedding,
            top_k=query.top_k,
            threshold=query.threshold,
        )

        documents: list[RetrievedDocument] = []

        for result in results:

            chunk = RetrievedChunk(
                document_id=result.document_id,
                chunk_id=result.chunk_id,
                text=result.text,
                similarity=result.similarity,
                metadata=result.metadata,
            )

            documents.append(
                RetrievedDocument(
                    document_id=result.document_id,
                    score=result.similarity,
                    chunks=(chunk,),
                    metadata=result.metadata,
                )
            )

        elapsed = (
            perf_counter() - start
        ) * 1000.0

        return RetrievalResult(
            query=Query(
                text=query.text,
                embedding=embedding,
                top_k=query.top_k,
                threshold=query.threshold,
            ),
            documents=tuple(documents),
            retrieval_time_ms=elapsed,
        )
