"""
Tests for RetrieverFactory.
"""

from __future__ import annotations

from app.embeddings.models import EmbeddingVector
from app.retrieval.base import Retriever
from app.retrieval.factory import RetrieverFactory
from app.retrieval.models import (
    Query,
    RetrievalResult,
)
from app.retrieval.semantic import SemanticRetriever


class DummyEmbeddingService:
    """Dummy embedding service."""

    def embed_text(
        self,
        text: str,
    ) -> EmbeddingVector:

        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )


class DummyVectorSearchService:
    """Dummy vector search service."""

    def search(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int,
        threshold: float,
    ):
        return []


class DummyRetriever(Retriever):
    """Dummy retriever."""

    def retrieve(
        self,
        query: Query,
    ) -> RetrievalResult:

        return RetrievalResult(
            query=query,
        )


class TestRetrieverFactory:
    """Tests for RetrieverFactory."""

    #
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    #

    def test_default_retriever(self):

        factory = RetrieverFactory(
            embedding_service=DummyEmbeddingService(),
            vector_search_service=DummyVectorSearchService(),
        )

        assert isinstance(
            factory.retriever,
            SemanticRetriever,
        )

    def test_custom_retriever(self):

        retriever = DummyRetriever()

        factory = RetrieverFactory(
            retriever=retriever,
        )

        assert factory.retriever is retriever

    #
    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    #

    def test_retriever_name(self):

        factory = RetrieverFactory(
            retriever=DummyRetriever(),
        )

        assert (
            factory.retriever_name
            == "DummyRetriever"
        )

    def test_retriever_identity(self):

        retriever = DummyRetriever()

        factory = RetrieverFactory(
            retriever=retriever,
        )

        assert factory.retriever is retriever

    #
    # ------------------------------------------------------------------
    # Replacement
    # ------------------------------------------------------------------
    #

    def test_set_retriever(self):

        factory = RetrieverFactory(
            retriever=DummyRetriever(),
        )

        new_retriever = DummyRetriever()

        factory.set_retriever(
            new_retriever,
        )

        assert (
            factory.retriever
            is new_retriever
        )

    def test_retriever_name_updates(self):

        class AnotherRetriever(
            DummyRetriever
        ):
            pass

        factory = RetrieverFactory(
            retriever=DummyRetriever(),
        )

        factory.set_retriever(
            AnotherRetriever(),
        )

        assert (
            factory.retriever_name
            == "AnotherRetriever"
        )

    #
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    #

    def test_requires_services_when_default_retriever_used(self):

        try:
            RetrieverFactory()
            assert False, (
                "Expected ValueError"
            )
        except ValueError:
            pass

    def test_default_retriever_type(self):

        factory = RetrieverFactory(
            embedding_service=DummyEmbeddingService(),
            vector_search_service=DummyVectorSearchService(),
        )

        assert (
            type(factory.retriever)
            is factory.DEFAULT_RETRIEVER
        )

    def test_set_retriever_replaces_previous(self):
    
        first = DummyRetriever()
        second = DummyRetriever()
    
        factory = RetrieverFactory(
            retriever=first,
        )
    
        factory.set_retriever(second)
    
        assert factory.retriever is second
        assert factory.retriever is not first
    
