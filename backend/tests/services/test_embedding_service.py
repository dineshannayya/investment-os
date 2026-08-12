"""
Tests for EmbeddingService.
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
from app.services.embedding_service import EmbeddingService


class DummyEmbeddingProvider(EmbeddingProvider):
    """Dummy embedding provider used for testing."""

    def __init__(self):
        self.embed_document_called = False
        self.embed_text_called = False
        self.embed_chunks_called = False

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

    def embed_document(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> DocumentEmbedding:

        self.embed_document_called = True

        return super().embed_document(
            document=document,
            chunks=chunks,
        )

    def embed_text(
        self,
        text: str,
    ) -> EmbeddingVector:

        self.embed_text_called = True

        return super().embed_text(text)

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddingVector]:

        self.embed_chunks_called = True

        return super().embed_chunks(chunks)


class DummyEmbeddingFactory:
    """Dummy embedding factory."""

    def __init__(
        self,
        provider: EmbeddingProvider,
    ):
        self.provider = provider


class TestEmbeddingService:

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
    # Constructor
    # ------------------------------------------------------------------

    def test_factory_property(self):

        factory = DummyEmbeddingFactory(
            DummyEmbeddingProvider(),
        )

        service = EmbeddingService(
            factory=factory,
        )

        assert service.factory is factory

    def test_provider_property(self):

        provider = DummyEmbeddingProvider()

        service = EmbeddingService(
            factory=DummyEmbeddingFactory(
                provider,
            ),
        )

        assert service.provider is provider

    # ------------------------------------------------------------------
    # embed()
    # ------------------------------------------------------------------

    def test_embed_document(self):

        provider = DummyEmbeddingProvider()

        service = EmbeddingService(
            factory=DummyEmbeddingFactory(
                provider,
            ),
        )

        embedding = service.embed(
            self.create_document(),
            self.create_chunks(),
        )

        assert provider.embed_document_called

        assert isinstance(
            embedding,
            DocumentEmbedding,
        )

    # ------------------------------------------------------------------
    # embed_text()
    # ------------------------------------------------------------------

    def test_embed_text(self):

        provider = DummyEmbeddingProvider()

        service = EmbeddingService(
            factory=DummyEmbeddingFactory(
                provider,
            ),
        )

        vector = service.embed_text(
            "hello"
        )

        assert provider.embed_text_called

        assert isinstance(
            vector,
            EmbeddingVector,
        )

    # ------------------------------------------------------------------
    # embed_chunks()
    # ------------------------------------------------------------------

    def test_embed_chunks(self):

        provider = DummyEmbeddingProvider()

        service = EmbeddingService(
            factory=DummyEmbeddingFactory(
                provider,
            ),
        )

        vectors = service.embed_chunks(
            self.create_chunks(),
        )

        assert provider.embed_chunks_called

        assert len(vectors) == 2

        assert all(
            isinstance(
                vector,
                EmbeddingVector,
            )
            for vector in vectors
        )

    def test_embed_query(self):
    
        provider = DummyEmbeddingProvider()
    
        service = EmbeddingService(
            factory=DummyEmbeddingFactory(provider),
        )
    
        vector = service.embed_query("AI healthcare")
    
        assert provider.embed_text_called
        assert isinstance(vector, EmbeddingVector)
    
