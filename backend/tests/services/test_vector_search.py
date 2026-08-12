"""
Tests for VectorSearchService.
"""

from __future__ import annotations

from uuid import uuid4

from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)
from app.services.vector_search import VectorSearchService
from app.vectorstore.base import VectorStore
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class DummyVectorStore(VectorStore):
    """Dummy vector store for testing."""

    def __init__(self):
        self._vectors: dict = {}

        self.add_called = False
        self.add_many_called = False
        self.remove_called = False
        self.clear_called = False
        self.search_called = False

        self.last_request = None

    #
    # Storage
    #

    def add(
        self,
        vector: StoredVector,
    ) -> None:

        self.add_called = True

        self._vectors[vector.document_id] = vector

    def add_many(
        self,
        vectors: list[StoredVector],
    ) -> None:

        self.add_many_called = True

        super().add_many(vectors)

    #
    # Removal
    #

    def remove(
        self,
        document_id,
    ) -> bool:

        self.remove_called = True

        return (
            self._vectors.pop(document_id, None)
            is not None
        )

    def clear(self):

        self.clear_called = True

        self._vectors.clear()

    #
    # Retrieval
    #

    def get(
        self,
        document_id,
    ):

        return self._vectors.get(document_id)

    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:

        self.search_called = True

        self.last_request = request

        return []

    #
    # Information
    #

    def count(self):

        return len(self._vectors)


class DummyFactory:
    """Dummy factory."""

    def __init__(self, store):

        self.store = store


class TestVectorSearchService:

    @staticmethod
    def create_embedding() -> DocumentEmbedding:

        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        return DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=3,
            document_embedding=vector,
        )

    #
    # Constructor
    #

    def test_factory_property(self):

        factory = DummyFactory(
            DummyVectorStore(),
        )

        service = VectorSearchService(
            factory=factory,
        )

        assert service.factory is factory

    def test_store_property(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        assert service.store is store

    #
    # Indexing
    #

    def test_index_document(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        embedding = self.create_embedding()

        service.index_document(
            embedding,
        )

        assert store.add_called

        assert store.count() == 1

    def test_index_documents(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        embeddings = [
            self.create_embedding(),
            self.create_embedding(),
        ]

        service.index_documents(
            embeddings,
        )

        assert store.add_many_called

        assert store.count() == 2

    #
    # Removal
    #

    def test_remove_document(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        embedding = self.create_embedding()

        service.index_document(
            embedding,
        )

        assert service.remove_document(
            embedding.document_id,
        )

        assert store.remove_called

    def test_clear(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        service.index_document(
            self.create_embedding(),
        )

        service.clear()

        assert store.clear_called

        assert store.count() == 0

    #
    # Search
    #

    def test_search(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        results = service.search(
            vector,
            top_k=10,
            threshold=0.8,
        )

        assert store.search_called

        assert results == []

        assert store.last_request.top_k == 10

        assert (
            store.last_request.threshold
            == 0.8
        )

    #
    # Information
    #

    def test_count(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        assert service.count() == 0

    def test_is_empty(self):

        store = DummyVectorStore()

        service = VectorSearchService(
            factory=DummyFactory(store),
        )

        assert service.is_empty()

        service.index_document(
            self.create_embedding(),
        )

        assert not service.is_empty()
