"""
Tests for SentenceTransformerProvider.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.embeddings.models import EmbeddingVector
from app.embeddings.sentence_transformers import (
    SentenceTransformerProvider,
)


class TestSentenceTransformerProvider:
    """Tests for SentenceTransformerProvider."""

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_default_model(self):

        provider = SentenceTransformerProvider()

        assert (
            provider.name
            == SentenceTransformerProvider.DEFAULT_MODEL
        )

    def test_custom_model(self):

        provider = SentenceTransformerProvider(
            model_name="custom-model",
        )

        assert provider.name == "custom-model"

    # ------------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------------

    def test_embed_empty_texts(self):

        provider = SentenceTransformerProvider()

        vectors = provider.embed_texts([])

        assert vectors == []

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    @patch(
        "app.embeddings.sentence_transformers.SentenceTransformer"
    )
    def test_lazy_model_loading(
        self,
        mock_transformer,
    ):

        mock_model = MagicMock()

        mock_model.get_sentence_embedding_dimension.return_value = 384

        mock_model.encode.return_value = [
            [1.0, 2.0, 3.0],
        ]

        mock_transformer.return_value = mock_model

        provider = SentenceTransformerProvider()

        assert provider._model is None

        provider.embed_texts(["hello"])

        assert provider._model is mock_model

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------

    @patch(
        "app.embeddings.sentence_transformers.SentenceTransformer"
    )
    def test_dimensions(
        self,
        mock_transformer,
    ):

        mock_model = MagicMock()

        mock_model.get_sentence_embedding_dimension.return_value = 384

        mock_transformer.return_value = mock_model

        provider = SentenceTransformerProvider()

        assert provider.dimensions == 384

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    @patch(
        "app.embeddings.sentence_transformers.SentenceTransformer"
    )
    def test_embed_texts(
        self,
        mock_transformer,
    ):

        mock_model = MagicMock()

        mock_model.get_sentence_embedding_dimension.return_value = 3

        mock_model.encode.return_value = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ]

        mock_transformer.return_value = mock_model

        provider = SentenceTransformerProvider()

        vectors = provider.embed_texts(
            [
                "one",
                "two",
            ]
        )

        assert len(vectors) == 2

        assert all(
            isinstance(
                vector,
                EmbeddingVector,
            )
            for vector in vectors
        )

        assert vectors[0].values == (
            1.0,
            2.0,
            3.0,
        )

        assert vectors[1].values == (
            4.0,
            5.0,
            6.0,
        )

        assert vectors[0].dimensions == 3

    # ------------------------------------------------------------------
    # Model caching
    # ------------------------------------------------------------------

    @patch(
        "app.embeddings.sentence_transformers.SentenceTransformer"
    )
    def test_model_loaded_once(
        self,
        mock_transformer,
    ):

        mock_model = MagicMock()

        mock_model.get_sentence_embedding_dimension.return_value = 3

        mock_model.encode.return_value = [
            [1.0, 2.0, 3.0],
        ]

        mock_transformer.return_value = mock_model

        provider = SentenceTransformerProvider()

        provider.embed_texts(["hello"])

        provider.embed_texts(["world"])

        mock_transformer.assert_called_once()
