"""
Tests for SemanticRetriever.
"""

from __future__ import annotations

from uuid import uuid4

from app.embeddings.models import EmbeddingVector
from app.retrieval.models import Query
from app.retrieval.semantic import SemanticRetriever
from app.vectorstore.models import SearchResult


class DummyEmbeddingService:
    """Dummy embedding service."""

    def __init__(self):
        self.called = False

    def embed_text(
        self,
        text: str,
    ) -> EmbeddingVector:

        self.called = True

        return EmbeddingVector(
            values=(1.0, 2.0, 3.0),
            model_name="dummy",
            dimensions=3,
        )


class DummyVectorSearchService:
    """Dummy vector search service."""

    def __init__(self):
        self.called = False

        self.last_vector = None
        self.last_top_k = None
        self.last_threshold = None

    def search(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int,
        threshold: float,
    ):

        self.called = True
        self.last_vector = vector
        self.last_top_k = top_k
        self.last_threshold = threshold

        document_id = uuid4()
        chunk_id = uuid4()
        
        return [
            SearchResult(
                document_id=document_id,
                chunk_id=chunk_id,
                text="Healthcare startup information",
                similarity=0.91,
                metadata={
                    "page": 4,
                    "section": "Company Overview",
                },
            )
        ]
        

class TestSemanticRetriever:

    @staticmethod
    def create_query() -> Query:

        return Query(
            text="healthcare startup",
            top_k=10,
            threshold=0.5,
        )

    #
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    #

    def test_properties(self):

        embedding = DummyEmbeddingService()

        vector = DummyVectorSearchService()

        retriever = SemanticRetriever(
            embedding_service=embedding,
            vector_search_service=vector,
        )

        assert retriever.embedding_service is embedding

        assert retriever.vector_search_service is vector

    #
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    #

    def test_retrieve_generates_embedding(self):

        embedding = DummyEmbeddingService()

        vector = DummyVectorSearchService()

        retriever = SemanticRetriever(
            embedding_service=embedding,
            vector_search_service=vector,
        )

        result = retriever.retrieve(
            self.create_query(),
        )

        assert embedding.called
        assert vector.last_vector is result.query.embedding
        assert vector.called
        assert len(result.documents) == 1
        assert ( result.query.embedding is not None)

    def test_retrieve_uses_existing_embedding(self):

        embedding = DummyEmbeddingService()

        vector = DummyVectorSearchService()

        existing = EmbeddingVector(
            values=(9.0, 9.0, 9.0),
            model_name="dummy",
            dimensions=3,
        )

        retriever = SemanticRetriever(
            embedding_service=embedding,
            vector_search_service=vector,
        )

        query = Query(
            text="healthcare",
            embedding=existing,
        )

        result = retriever.retrieve(query)

        assert not embedding.called
        assert vector.called
        assert ( result.query.embedding is existing)
        assert vector.last_vector is existing


    def test_search_parameters_forwarded(self):

        embedding = DummyEmbeddingService()

        vector = DummyVectorSearchService()

        retriever = SemanticRetriever(
            embedding_service=embedding,
            vector_search_service=vector,
        )

        retriever.retrieve(
            Query(
                text="AI",
                top_k=7,
                threshold=0.75,
            )
        )

        assert vector.last_top_k == 7
        assert vector.last_threshold == 0.75
        assert vector.last_vector is not None

    def test_retrieval_result(self):

        retriever = SemanticRetriever(
            embedding_service=DummyEmbeddingService(),
            vector_search_service=DummyVectorSearchService(),
        )

        result = retriever.retrieve(
            self.create_query(),
        )

        assert len(result.documents) == 1

        document = result.documents[0]

        assert document.score == 0.91
        assert len(document.chunks) == 1
        assert ( document.chunks[0].similarity == 0.91)

        chunk = document.chunks[0]
        
        assert chunk.document_id == document.document_id
        assert chunk.chunk_id is not None
        assert chunk.text == "Healthcare startup information"
        assert chunk.similarity == 0.91
        
        assert document.metadata["page"] == 4
        assert document.metadata["section"] == "Company Overview"


    def test_retrieval_time_recorded(self):

        retriever = SemanticRetriever(
            embedding_service=DummyEmbeddingService(),
            vector_search_service=DummyVectorSearchService(),
        )

        result = retriever.retrieve(
            self.create_query(),
        )

        assert result.retrieval_time_ms >= 0.0

    def test_retrieved_chunk_data_is_preserved(self):
    
        retriever = SemanticRetriever(
            embedding_service=DummyEmbeddingService(),
            vector_search_service=DummyVectorSearchService(),
        )
    
        result = retriever.retrieve(
            self.create_query(),
        )
    
        document = result.documents[0]
        chunk = document.chunks[0]
    
        assert chunk.document_id == document.document_id
        assert chunk.text == "Healthcare startup information"
        assert chunk.similarity == 0.91
    
        assert chunk.metadata["page"] == 4
        assert (
            chunk.metadata["section"]
            == "Company Overview"
        )
    
