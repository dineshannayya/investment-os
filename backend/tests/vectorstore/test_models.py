"""
Tests for vector store models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from uuid import uuid4

import pytest

from app.embeddings.models import EmbeddingVector
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class TestStoredVector:
    """Tests for StoredVector."""

    @staticmethod
    def create_vector() -> EmbeddingVector:
        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

    def test_defaults(self):

        stored = StoredVector(
            document_id=uuid4(),
            vector=self.create_vector(),
        )

        assert isinstance(
            stored.document_id,
            type(uuid4()),
        )

        assert stored.vector.dimensions == 3

        assert isinstance(
            stored.metadata,
            MappingProxyType,
        )

        assert len(stored.metadata) == 0

    def test_metadata(self):

        metadata = MappingProxyType(
            {
                "type": "document",
                "title": "Pitch Deck",
            }
        )

        stored = StoredVector(
            document_id=uuid4(),
            vector=self.create_vector(),
            metadata=metadata,
        )

        assert stored.metadata["type"] == "document"

        assert stored.metadata["title"] == "Pitch Deck"

    def test_frozen(self):

        stored = StoredVector(
            document_id=uuid4(),
            vector=self.create_vector(),
        )

        with pytest.raises(
            FrozenInstanceError,
        ):
            stored.document_id = uuid4()


class TestSearchRequest:
    """Tests for SearchRequest."""

    @staticmethod
    def create_vector() -> EmbeddingVector:
        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

    def test_defaults(self):

        request = SearchRequest(
            vector=self.create_vector(),
        )

        assert request.top_k == 5

        assert request.threshold == 0.0

    def test_custom_values(self):

        request = SearchRequest(
            vector=self.create_vector(),
            top_k=10,
            threshold=0.8,
        )

        assert request.top_k == 10

        assert request.threshold == pytest.approx(
            0.8
        )

    def test_frozen(self):

        request = SearchRequest(
            vector=self.create_vector(),
        )

        with pytest.raises(
            FrozenInstanceError,
        ):
            request.top_k = 20


class TestSearchResult:
    """Tests for SearchResult."""

    @staticmethod
    def create_vector() -> EmbeddingVector:
        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

    def test_defaults(self):

        result = SearchResult(
            document_id=uuid4(),
            similarity=0.95,
            vector=self.create_vector(),
        )

        assert result.similarity == pytest.approx(
            0.95
        )

        assert result.vector.dimensions == 3

        assert isinstance(
            result.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        metadata = MappingProxyType(
            {
                "page": 2,
                "chunk": 5,
            }
        )

        result = SearchResult(
            document_id=uuid4(),
            similarity=0.90,
            vector=self.create_vector(),
            metadata=metadata,
        )

        assert result.metadata["page"] == 2

        assert result.metadata["chunk"] == 5

    def test_frozen(self):

        result = SearchResult(
            document_id=uuid4(),
            similarity=0.5,
            vector=self.create_vector(),
        )

        with pytest.raises(
            FrozenInstanceError,
        ):
            result.similarity = 0.7

    def test_score_alias(self):

        result = SearchResult(
            document_id=uuid4(),
            similarity=0.83,
            vector=self.create_vector(),
        )

        assert result.score == pytest.approx(
            0.83
        )

    def test_stored_vector_equality(self):
    
        vector = self.create_vector()
    
        document_id = uuid4()
    
        a = StoredVector(
            document_id=document_id,
            vector=vector,
        )
    
        b = StoredVector(
            document_id=document_id,
            vector=vector,
        )
    
        assert a == b

    def test_metadata_is_read_only(self):
    
        stored = StoredVector(
            document_id=uuid4(),
            vector=self.create_vector(),
        )
    
        with pytest.raises(TypeError):
            stored.metadata["page"] = 1
        
