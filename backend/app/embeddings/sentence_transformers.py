"""
Sentence Transformers embedding provider.
"""

from __future__ import annotations

from typing import Any
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer: Any = None

from app.embeddings.base import EmbeddingProvider
from app.embeddings.models import EmbeddingVector


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Embedding provider backed by sentence-transformers.

    The model is loaded lazily on first use to avoid unnecessary startup
    overhead and to simplify unit testing.
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str | None = None,
    ) -> None:
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model: Any | None = None
        self._dimensions: int | None = None

    @property
    def name(self) -> str:
        """
        Name of the embedding model.
        """
        return self._model_name

    @property
    def dimensions(self) -> int:
        """
        Embedding vector dimension.
        """
        if self._dimensions is None:
            self._dimensions = (
                self._get_model()
                .get_sentence_embedding_dimension()
            )

        return self._dimensions

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[EmbeddingVector]:
        """
        Generate embeddings for multiple texts.
        """

        if not texts:
            return []

        model = self._get_model()

        dimensions = self.dimensions

        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return [
            EmbeddingVector(
                values=tuple(float(v) for v in vector),
                model_name=self.name,
                dimensions=dimensions,
            )
            for vector in vectors
        ]

    #
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    #

    def _get_model(self) -> Any:
        """
        Lazily load the SentenceTransformer model.
        """
        if self._model is None:

            if SentenceTransformer is None:
                raise RuntimeError(
                    "sentence-transformers is not installed."
                )

            self._model = SentenceTransformer(
                self._model_name,
            )

        return self._model

