"""
Tests for embedding base classes.
"""

from __future__ import annotations

from uuid import uuid4

from app.chunking.base import Chunk
from app.embeddings.base import EmbeddingProvider
from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)
from app.processors import DocumentContent


class DummyEmbeddingProvider(EmbeddingProvider):
    """Simple embedding provider used for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def dimensions(self) -> int:
        return 3

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[EmbeddingVector]:

        return [
            EmbeddingVector(
                values=(1.0, 2.0, 3.0),
                model_name=self.name,
                dimensions=self.dimensions,
            )
            for _ in texts
        ]


class TestEmbeddingProvider:
    """Tests for EmbeddingProvider."""

    @staticmethod
    def create_document() -> DocumentContent:
        return DocumentContent(
            document_id=uuid4(),
            title="Test Document",
            text="Hello world",
            page_count=1,
            metadata={},
        )

    @staticmethod
    def create_chunks() -> list[Chunk]:
        return [
            Chunk(
                index=0,
                text="Hello",
                start_offset=0,
                end_offset=5,
                metadata={},
            ),
            Chunk(
                index=1,
                text="world",
                start_offset=6,
                end_offset=11,
                metadata={},
            ),
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_name(self):
        provider = DummyEmbeddingProvider()

        assert provider.name == "dummy"

    def test_dimensions(self):
        provider = DummyEmbeddingProvider()

        assert provider.dimensions == 3

    # ------------------------------------------------------------------
    # embed_texts
    # ------------------------------------------------------------------

    def test_embed_texts(self):
        provider = DummyEmbeddingProvider()

        vectors = provider.embed_texts(
            [
                "one",
                "two",
            ]
        )

        assert len(vectors) == 2

        assert all(
            isinstance(v, EmbeddingVector)
            for v in vectors
        )

    # ------------------------------------------------------------------
    # embed_text
    # ------------------------------------------------------------------

    def test_embed_text(self):
        provider = DummyEmbeddingProvider()

        vector = provider.embed_text(
            "hello"
        )

        assert isinstance(
            vector,
            EmbeddingVector,
        )

        assert vector.values == (
            1.0,
            2.0,
            3.0,
        )

    # ------------------------------------------------------------------
    # embed_chunks
    # ------------------------------------------------------------------

    def test_embed_chunks(self):
        provider = DummyEmbeddingProvider()

        chunks = self.create_chunks()

        vectors = provider.embed_chunks(
            chunks
        )

        assert len(vectors) == len(chunks)

        assert all(
            isinstance(v, EmbeddingVector)
            for v in vectors
        )

    # ------------------------------------------------------------------
    # embed_document
    # ------------------------------------------------------------------

    def test_embed_document(self):
        provider = DummyEmbeddingProvider()

        document = self.create_document()

        chunks = self.create_chunks()

        embedding = provider.embed_document(
            document=document,
            chunks=chunks,
        )

        assert isinstance(
            embedding,
            DocumentEmbedding,
        )

        assert (
            embedding.document_id
            == document.document_id
        )

        assert (
            embedding.model_name
            == provider.name
        )

        assert (
            embedding.document_embedding.model_name
            == provider.name
        )

        assert (
            len(
                embedding.chunk_embeddings
            )
            == len(chunks)
        )

    # ------------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------------

    def test_embed_empty_texts(self):
        provider = DummyEmbeddingProvider()

        vectors = provider.embed_texts([])

        assert vectors == []

    def test_embed_empty_chunks(self):
        provider = DummyEmbeddingProvider()

        vectors = provider.embed_chunks([])

        assert vectors == []

    class RecordingProvider(DummyEmbeddingProvider):
    
        def __init__(self):
            self.received = None
    
        def embed_texts(self, texts):
            self.received = texts
            return super().embed_texts(texts)
    
    
        def test_embed_text_delegates():
            provider = RecordingProvider()
        
            provider.embed_text("hello")
        
            assert provider.received == ["hello"]
        
