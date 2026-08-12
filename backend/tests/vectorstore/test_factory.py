"""
Tests for vector store factory.
"""

from __future__ import annotations

from uuid import UUID

from app.embeddings.models import EmbeddingVector
from app.vectorstore.base import VectorStore
from app.vectorstore.factory import VectorStoreFactory
from app.vectorstore.memory import MemoryVectorStore
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class DummyVectorStore(VectorStore):
    """Dummy vector store."""

    def __init__(self):
        self._vectors: dict[UUID, StoredVector] = {}

    #
    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    #

    def add(
        self,
        vector: StoredVector,
    ) -> None:

        self._vectors[vector.document_id] = vector

    #
    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------
    #

    def remove(
        self,
        document_id: UUID,
    ) -> bool:

        return (
            self._vectors.pop(document_id, None)
            is not None
        )

    def clear(self) -> None:

        self._vectors.clear()

    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    def get(
        self,
        document_id: UUID,
    ) -> StoredVector | None:

        return self._vectors.get(document_id)

    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:

        return []

    #
    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------
    #

    def count(self) -> int:

        return len(self._vectors)


class TestVectorStoreFactory:
    """Tests for VectorStoreFactory."""

    #
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    #

    def test_default_store(self):

        factory = VectorStoreFactory()

        assert isinstance(
            factory.store,
            MemoryVectorStore,
        )

    def test_custom_store(self):

        store = DummyVectorStore()

        factory = VectorStoreFactory(
            store=store,
        )

        assert factory.store is store

    #
    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    #

    def test_store_name(self):

        store = DummyVectorStore()

        factory = VectorStoreFactory(
            store=store,
        )

        assert (
            factory.store_name
            == "DummyVectorStore"
        )

    def test_store_identity(self):

        store = DummyVectorStore()

        factory = VectorStoreFactory(
            store=store,
        )

        assert factory.store is store

    #
    # ------------------------------------------------------------------
    # Store replacement
    # ------------------------------------------------------------------
    #

    def test_set_store(self):

        factory = VectorStoreFactory(
            store=DummyVectorStore(),
        )

        new_store = DummyVectorStore()

        factory.set_store(
            new_store,
        )

        assert factory.store is new_store

    def test_store_name_updates(self):

        class AnotherStore(
            DummyVectorStore
        ):
            pass

        factory = VectorStoreFactory(
            store=DummyVectorStore(),
        )

        factory.set_store(
            AnotherStore(),
        )

        assert (
            factory.store_name
            == "AnotherStore"
        )

    def test_set_store_replaces_previous(self):

        first = DummyVectorStore()

        second = DummyVectorStore()

        factory = VectorStoreFactory(
            store=first,
        )

        factory.set_store(second)

        assert factory.store is second

        assert factory.store is not first

    def test_default_store_type(self):
    
        factory = VectorStoreFactory()
    
        assert (
            type(factory.store)
            is factory.DEFAULT_STORE
        )

    def test_backend(self):
    
        factory = VectorStoreFactory()
    
        assert factory.backend == "memory"

    def test_store_is_vector_store(self):
    
        factory = VectorStoreFactory()
    
        assert isinstance(
            factory.store,
            VectorStore,
        )
    
