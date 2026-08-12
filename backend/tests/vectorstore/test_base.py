"""
Tests for vector store base classes.
"""

from __future__ import annotations

from uuid import uuid4

from app.embeddings.models import EmbeddingVector
from app.vectorstore.base import VectorStore
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class DummyVectorStore(VectorStore):
    """Simple vector store used for testing."""

    def __init__(self):
        self._vectors: dict = {}

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
        document_id,
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
        document_id,
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


class TestVectorStore:

    @staticmethod
    def create_vector() -> StoredVector:
    
        return StoredVector(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example chunk",
            vector=EmbeddingVector(
                values=(1.0, 2.0, 3.0),
                model_name="dummy",
                dimensions=3,
            ),
        )
    
    
    #
    # ------------------------------------------------------------------
    # add()
    # ------------------------------------------------------------------
    #

    def test_add(self):

        store = DummyVectorStore()

        vector = self.create_vector()

        store.add(vector)

        assert store.count() == 1

        assert store.get(
            vector.document_id
        ) is vector

    #
    # ------------------------------------------------------------------
    # add_many()
    # ------------------------------------------------------------------
    #

    def test_add_many(self):

        store = DummyVectorStore()

        vectors = [
            self.create_vector(),
            self.create_vector(),
            self.create_vector(),
        ]

        store.add_many(vectors)

        assert store.count() == 3

    #
    # ------------------------------------------------------------------
    # remove()
    # ------------------------------------------------------------------
    #

    def test_remove_existing(self):

        store = DummyVectorStore()

        vector = self.create_vector()

        store.add(vector)

        assert store.remove(
            vector.document_id
        )

        assert store.count() == 0

    def test_remove_missing(self):

        store = DummyVectorStore()

        assert not store.remove(
            uuid4()
        )

    #
    # ------------------------------------------------------------------
    # clear()
    # ------------------------------------------------------------------
    #

    def test_clear(self):

        store = DummyVectorStore()

        store.add_many(
            [
                self.create_vector(),
                self.create_vector(),
            ]
        )

        store.clear()

        assert store.count() == 0

    #
    # ------------------------------------------------------------------
    # get()
    # ------------------------------------------------------------------
    #

    def test_get_existing(self):

        store = DummyVectorStore()

        vector = self.create_vector()

        store.add(vector)

        assert (
            store.get(
                vector.document_id
            )
            is vector
        )

    def test_get_missing(self):

        store = DummyVectorStore()

        assert (
            store.get(uuid4())
            is None
        )

    #
    # ------------------------------------------------------------------
    # search()
    # ------------------------------------------------------------------
    #

    def test_search(self):

        store = DummyVectorStore()

        results = store.search(
            SearchRequest(
                vector=EmbeddingVector(
                    values=(1.0, 2.0, 3.0),
                    model_name="dummy",
                    dimensions=3,
                )
            )
        )

        assert results == []

    #
    # ------------------------------------------------------------------
    # count()
    # ------------------------------------------------------------------
    #

    def test_count(self):

        store = DummyVectorStore()

        assert store.count() == 0

        store.add(
            self.create_vector()
        )

        assert store.count() == 1

    #
    # ------------------------------------------------------------------
    # is_empty()
    # ------------------------------------------------------------------
    #

    def test_is_empty_true(self):

        store = DummyVectorStore()

        assert store.is_empty()

    def test_is_empty_false(self):

        store = DummyVectorStore()

        store.add(
            self.create_vector()
        )

        assert not store.is_empty()

class RecordingStore(DummyVectorStore):

    def __init__(self):
        super().__init__()
        self.calls = 0

    def add(self, vector):
        self.calls += 1
        super().add(vector)

    def test_add_replaces_existing(self):
    
        store = DummyVectorStore()
    
        document_id = uuid4()
    
        first = StoredVector(
            document_id=document_id,
            vector=EmbeddingVector(
                values=(1.0,),
                model_name="a",
                dimensions=1,
            ),
        )
    
        second = StoredVector(
            document_id=document_id,
            vector=EmbeddingVector(
                values=(2.0,),
                model_name="b",
                dimensions=1,
            ),
        )
    
        store.add(first)
        store.add(second)
    
        assert store.count() == 1
        assert store.get(document_id) is second
    
