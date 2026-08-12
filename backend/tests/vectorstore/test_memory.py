"""
Tests for MemoryVectorStore.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.embeddings.models import EmbeddingVector
from app.vectorstore.memory import MemoryVectorStore
from app.vectorstore.models import (
    SearchRequest,
    StoredVector,
)


class TestMemoryVectorStore:

    @staticmethod
    def create_vector(
        values: tuple[float, ...],
        document_id=None,
    ) -> StoredVector:

        return StoredVector(
            document_id=document_id or uuid4(),
            vector=EmbeddingVector(
                values=values,
                model_name="dummy",
                dimensions=len(values),
            ),
        )

    #
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    #

    def test_empty_store(self):

        store = MemoryVectorStore()

        assert store.count() == 0

        assert store.is_empty()

    #
    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    #

    def test_add(self):

        store = MemoryVectorStore()

        vector = self.create_vector((1.0, 0.0))

        store.add(vector)

        assert store.count() == 1

        assert store.get(vector.document_id) is vector

    def test_add_replaces_existing(self):

        store = MemoryVectorStore()

        document_id = uuid4()

        first = self.create_vector(
            (1.0, 0.0),
            document_id,
        )

        second = self.create_vector(
            (0.0, 1.0),
            document_id,
        )

        store.add(first)

        store.add(second)

        assert store.count() == 1

        assert store.get(document_id) is second

    def test_add_many(self):

        store = MemoryVectorStore()

        store.add_many(
            [
                self.create_vector((1.0,)),
                self.create_vector((2.0,)),
                self.create_vector((3.0,)),
            ]
        )

        assert store.count() == 3

    #
    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------
    #

    def test_remove_existing(self):

        store = MemoryVectorStore()

        vector = self.create_vector((1.0,))

        store.add(vector)

        assert store.remove(
            vector.document_id
        )

        assert store.count() == 0

    def test_remove_missing(self):

        store = MemoryVectorStore()

        assert not store.remove(uuid4())

    def test_clear(self):

        store = MemoryVectorStore()

        store.add_many(
            [
                self.create_vector((1.0,)),
                self.create_vector((2.0,)),
            ]
        )

        store.clear()

        assert store.is_empty()

    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    def test_get_missing(self):

        store = MemoryVectorStore()

        assert store.get(uuid4()) is None

    #
    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    #

    def test_search_empty_store(self):

        store = MemoryVectorStore()

        request = SearchRequest(
            vector=EmbeddingVector(
                values=(1.0, 0.0),
                model_name="dummy",
                dimensions=2,
            )
        )

        assert store.search(request) == []

    def test_search_exact_match(self):

        store = MemoryVectorStore()

        stored = self.create_vector(
            (1.0, 0.0)
        )

        store.add(stored)

        request = SearchRequest(
            vector=EmbeddingVector(
                values=(1.0, 0.0),
                model_name="dummy",
                dimensions=2,
            )
        )

        results = store.search(request)

        assert len(results) == 1

        assert (
            results[0].document_id
            == stored.document_id
        )

        assert results[0].similarity == pytest.approx(
            1.0
        )

    def test_search_threshold(self):

        store = MemoryVectorStore()

        store.add(
            self.create_vector((1.0, 0.0))
        )

        request = SearchRequest(
            vector=EmbeddingVector(
                values=(0.0, 1.0),
                model_name="dummy",
                dimensions=2,
            ),
            threshold=0.5,
        )

        assert store.search(request) == []

    def test_search_top_k(self):

        store = MemoryVectorStore()

        store.add_many(
            [
                self.create_vector((1.0, 0.0)),
                self.create_vector((0.9, 0.1)),
                self.create_vector((0.8, 0.2)),
            ]
        )

        request = SearchRequest(
            vector=EmbeddingVector(
                values=(1.0, 0.0),
                model_name="dummy",
                dimensions=2,
            ),
            top_k=2,
        )

        results = store.search(request)

        assert len(results) == 2

    #
    # ------------------------------------------------------------------
    # Cosine similarity
    # ------------------------------------------------------------------
    #

    def test_compute_similarity_identical(self):

        similarity = (
            MemoryVectorStore
            ._compute_similarity(
                (1.0, 0.0),
                (1.0, 0.0),
            )
        )

        assert similarity == pytest.approx(1.0)

    def test_compute_similarity_orthogonal(self):

        similarity = (
            MemoryVectorStore
            ._compute_similarity(
                (1.0, 0.0),
                (0.0, 1.0),
            )
        )

        assert similarity == pytest.approx(0.0)

    def test_compute_similarity_dimension_mismatch(self):

        with pytest.raises(ValueError):

            MemoryVectorStore._compute_similarity(
                (1.0,),
                (1.0, 2.0),
            )

    def test_compute_similarity_zero_vector(self):

        similarity = (
            MemoryVectorStore
            ._compute_similarity(
                (0.0, 0.0),
                (1.0, 0.0),
            )
        )

        assert similarity == 0.0
