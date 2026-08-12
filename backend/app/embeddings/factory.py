"""
Embedding provider factory.
"""

from __future__ import annotations

from app.embeddings.base import EmbeddingProvider
from app.embeddings.sentence_transformers import (
    SentenceTransformerProvider,
)


class EmbeddingFactory:
    """
    Factory for embedding providers.

    The factory manages a single active embedding provider,
    allowing different implementations (Sentence Transformers,
    OpenAI, Gemini, Ollama, etc.) to be plugged in without
    changing application code.
    """

    DEFAULT_PROVIDER = SentenceTransformerProvider

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self._provider = (
            provider
            if provider is not None
            else self.DEFAULT_PROVIDER()
        )

    @property
    def provider(self) -> EmbeddingProvider:
        """
        Return the active embedding provider.
        """
        return self._provider

    @property
    def provider_name(self) -> str:
        """
        Return the active provider name.
        """
        return self._provider.name

    @property
    def dimensions(self) -> int:
        """
        Return embedding vector dimensions.
        """
        return self._provider.dimensions

    def set_provider(
        self,
        provider: EmbeddingProvider,
    ) -> None:
        """
        Replace the active embedding provider.
        """
        self._provider = provider
