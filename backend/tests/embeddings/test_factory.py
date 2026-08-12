"""
Tests for EmbeddingFactory.
"""

from __future__ import annotations

from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import EmbeddingFactory
from app.embeddings.models import EmbeddingVector
from app.embeddings.sentence_transformers import (
    SentenceTransformerProvider,
)


class DummyEmbeddingProvider(EmbeddingProvider):
    """Dummy embedding provider."""

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


class TestEmbeddingFactory:
    """Tests for EmbeddingFactory."""

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_default_provider(self):

        factory = EmbeddingFactory()

        assert isinstance(
            factory.provider,
            SentenceTransformerProvider,
        )

    def test_custom_provider(self):

        provider = DummyEmbeddingProvider()

        factory = EmbeddingFactory(
            provider=provider,
        )

        assert factory.provider is provider

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_provider_name(self):

        provider = DummyEmbeddingProvider()

        factory = EmbeddingFactory(
            provider=provider,
        )

        assert factory.provider_name == "dummy"

    def test_dimensions(self):

        provider = DummyEmbeddingProvider()

        factory = EmbeddingFactory(
            provider=provider,
        )

        assert factory.dimensions == 3

    # ------------------------------------------------------------------
    # Provider replacement
    # ------------------------------------------------------------------

    def test_set_provider(self):

        factory = EmbeddingFactory(
            provider=DummyEmbeddingProvider(),
        )

        new_provider = DummyEmbeddingProvider()

        factory.set_provider(
            new_provider,
        )

        assert factory.provider is new_provider

    def test_provider_name_updates(self):

        class AnotherProvider(DummyEmbeddingProvider):

            @property
            def name(self):
                return "another"

        factory = EmbeddingFactory(
            provider=DummyEmbeddingProvider(),
        )

        factory.set_provider(
            AnotherProvider(),
        )

        assert factory.provider_name == "another"

    def test_dimensions_update(self):

        class LargeProvider(DummyEmbeddingProvider):

            @property
            def dimensions(self):
                return 1024

        factory = EmbeddingFactory(
            provider=DummyEmbeddingProvider(),
        )

        factory.set_provider(
            LargeProvider(),
        )

        assert factory.dimensions == 1024

    def test_provider_identity(self):
    
        provider = DummyEmbeddingProvider()
    
        factory = EmbeddingFactory(
            provider=provider,
        )
    
        assert factory.provider is provider

    def test_default_provider_type(self):
    
        factory = EmbeddingFactory()
    
        assert type(factory.provider) is factory.DEFAULT_PROVIDER
