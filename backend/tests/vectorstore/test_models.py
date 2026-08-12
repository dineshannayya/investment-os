"""
Tests for vector store domain models.
"""

from __future__ import annotations

from types import MappingProxyType
from uuid import uuid4

from app.embeddings.models import EmbeddingVector
from app.vectorstore.models import (
    SearchRequest,
    SearchResult,
    StoredVector,
)


class TestStoredVector:

    @staticmethod
    def create_embedding() -> EmbeddingVector:
        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

    def test_create(self):

        document_id = uuid4()
        chunk_id = uuid4()

        vector = StoredVector(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Healthcare startup information",
            vector=self.create_embedding(),
        )

        assert vector.document_id == document_id
        assert vector.chunk_id == chunk_id
        assert (
            vector.text
            == "Healthcare startup information"
        )
        assert vector.vector.values == (
            1.0,
            2.0,
            3.0,
        )

    def test_default_metadata(self):

        vector = StoredVector(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            vector=self.create_embedding(),
        )

        assert vector.metadata == {}
        assert isinstance(
            vector.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        metadata = {
            "page": 4,
            "section": "Financials",
        }

        vector = StoredVector(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Financial information",
            vector=self.create_embedding(),
            metadata=metadata,
        )

        assert vector.metadata["page"] == 4
        assert (
            vector.metadata["section"]
            == "Financials"
        )

    def test_frozen(self):

        vector = StoredVector(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            vector=self.create_embedding(),
        )

        try:
            vector.text = "Changed"
            assert False, "Expected FrozenInstanceError"
        except AttributeError:
            pass


class TestSearchRequest:

    @staticmethod
    def create_embedding() -> EmbeddingVector:
        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

    def test_defaults(self):

        request = SearchRequest(
            vector=self.create_embedding(),
        )

        assert request.top_k == 5
        assert request.threshold == 0.0

    def test_custom_values(self):

        request = SearchRequest(
            vector=self.create_embedding(),
            top_k=10,
            threshold=0.75,
        )

        assert request.top_k == 10
        assert request.threshold == 0.75


class TestSearchResult:

    def test_create(self):

        document_id = uuid4()
        chunk_id = uuid4()

        result = SearchResult(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Relevant investment information",
            similarity=0.92,
        )

        assert result.document_id == document_id
        assert result.chunk_id == chunk_id
        assert (
            result.text
            == "Relevant investment information"
        )
        assert result.similarity == 0.92

    def test_default_metadata(self):

        result = SearchResult(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            similarity=0.8,
        )

        assert result.metadata == {}
        assert isinstance(
            result.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        result = SearchResult(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            similarity=0.85,
            metadata={
                "page": 7,
                "section": "Risk",
            },
        )

        assert result.metadata["page"] == 7
        assert (
            result.metadata["section"]
            == "Risk"
        )

    def test_frozen(self):

        result = SearchResult(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            similarity=0.8,
        )

        try:
            result.text = "Changed"
            assert False, "Expected FrozenInstanceError"
        except AttributeError:
            pass
