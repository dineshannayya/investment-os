"""
Tests for embedding models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.embeddings.models import (
    DocumentEmbedding,
    EmbeddingVector,
)

# ------------------------------------------
# TestEmbeddingVector
#     ✓ defaults
#     ✓ custom_confidence
#     ✓ frozen
#     ✓ tuple_values
#     ✓ empty_vector
#     ✓ equality
#------------------------------------------ 

class TestEmbeddingVector:
    """Tests for EmbeddingVector."""

    def test_defaults(self):
        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        assert vector.values == (1.0, 2.0, 3.0)
        assert vector.model_name == "dummy"
        assert vector.dimensions == 3
        assert vector.confidence == 1.0

    def test_custom_confidence(self):
        vector = EmbeddingVector(
            values=(0.1, 0.2),
            model_name="test-model",
            dimensions=2,
            confidence=0.85,
        )

        assert vector.confidence == pytest.approx(0.85)

    def test_is_frozen(self):
        vector = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )

        with pytest.raises(FrozenInstanceError):
            vector.model_name = "other"

    def test_tuple_values(self):
        vector = EmbeddingVector(
            values=(0.1, 0.2, 0.3),
            model_name="dummy",
            dimensions=3,
        )

        assert isinstance(vector.values, tuple)
        assert len(vector.values) == vector.dimensions

    def test_embedding_vector_equality(self):
        a = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        b = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        assert a == b

# ----------------------------------------------
# TestDocumentEmbedding
#    ✓ defaults
#    ✓ chunk_embeddings
#    ✓ frozen
#    ✓ dimension_matches_vector
#    ✓ chunk_embeddings_are_tuple
#    ✓ document_embedding_present
#    ✓ chunk_order_preserved
#    ✓ document_embedding_equality
# ----------------------------------------------
class TestDocumentEmbedding:
    """Tests for DocumentEmbedding."""

    def test_defaults(self):
        document_id = uuid4()

        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        embedding = DocumentEmbedding(
            document_id=document_id,
            model_name="dummy",
            dimensions=3,
            document_embedding=vector,
        )

        assert embedding.document_id == document_id
        assert embedding.model_name == "dummy"
        assert embedding.dimensions == 3
        assert embedding.document_embedding is vector
        assert embedding.chunk_embeddings == ()

    def test_chunk_embeddings(self):
        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=3,
            document_embedding=vector,
            chunk_embeddings=(vector, vector),
        )

        assert len(embedding.chunk_embeddings) == 2

    def test_is_frozen(self):
        vector = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )

        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=1,
            document_embedding=vector,
        )

        with pytest.raises(FrozenInstanceError):
            embedding.model_name = "other"

    def test_dimension_matches_vector(self):
        vector = EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )

        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=3,
            document_embedding=vector,
        )

        assert (
            embedding.dimensions
            == embedding.document_embedding.dimensions
        )

    def test_chunk_embeddings_are_tuple(self):
        vector = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )

        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=1,
            document_embedding=vector,
            chunk_embeddings=(vector,),
        )

        assert isinstance(
            embedding.chunk_embeddings,
            tuple,
        )


    def test_empty_vector(self):
        vector = EmbeddingVector(
            values=(),
            model_name="dummy",
            dimensions=0,
        )
    
        assert vector.values == ()
        assert vector.dimensions == 0

    def test_document_embedding_present(self):
    
        vector = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=1,
            document_embedding=vector,
        )
    
        assert embedding.document_embedding is vector

    def test_chunk_order_preserved(self):
    
        first = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        second = EmbeddingVector(
            values=(2.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        embedding = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=1,
            document_embedding=first,
            chunk_embeddings=(
                first,
                second,
            ),
        )
    
        assert embedding.chunk_embeddings[0] is first
        assert embedding.chunk_embeddings[1] is second

    def test_document_embedding_equality(self):
    
        vector = EmbeddingVector(
            values=(1.0,),
            model_name="dummy",
            dimensions=1,
        )
    
        a = DocumentEmbedding(
            document_id=uuid4(),
            model_name="dummy",
            dimensions=1,
            document_embedding=vector,
        )
    
        b = DocumentEmbedding(
            document_id=a.document_id,
            model_name="dummy",
            dimensions=1,
            document_embedding=vector,
        )
    
        assert a == b
                    
