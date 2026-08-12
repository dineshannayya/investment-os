"""
Tests for retrieval base classes.
"""

from __future__ import annotations

from uuid import uuid4

from app.embeddings.models import EmbeddingVector
from app.retrieval.base import Retriever
from app.retrieval.models import (
    Query,
    RetrievedChunk,
    RetrievedDocument,
    RetrievalResult,
)


class DummyRetriever(Retriever):
    """Dummy retriever used for testing."""

    def __init__(self):
        self.retrieve_called = False

    def retrieve(
        self,
        query: Query,
    ) -> RetrievalResult:

        self.retrieve_called = True

        chunk = RetrievedChunk(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example chunk",
            similarity=0.95,
        )

        document = RetrievedDocument(
            document_id=chunk.document_id,
            score=0.95,
            chunks=(chunk,),
        )

        return RetrievalResult(
            query=query,
            documents=(document,),
            retrieval_time_ms=12.5,
        )


class TestRetriever:

    @staticmethod
    def create_query() -> Query:

        return Query(
            text="healthcare startups",
            embedding=EmbeddingVector(
                values=(1.0, 2.0, 3.0),
                model_name="dummy",
                dimensions=3,
            ),
        )

    #
    # ------------------------------------------------------------------
    # retrieve()
    # ------------------------------------------------------------------
    #

    def test_retrieve(self):

        retriever = DummyRetriever()

        result = retriever.retrieve(
            self.create_query(),
        )

        assert retriever.retrieve_called

        assert result.query.text == "healthcare startups"

        assert len(result.documents) == 1

    #
    # ------------------------------------------------------------------
    # retrieve_documents()
    # ------------------------------------------------------------------
    #

    def test_retrieve_documents(self):

        retriever = DummyRetriever()

        documents = retriever.retrieve_documents(
            self.create_query(),
        )

        assert retriever.retrieve_called

        assert len(documents) == 1

        assert isinstance(
            documents[0],
            RetrievedDocument,
        )

    #
    # ------------------------------------------------------------------
    # retrieve_chunks()
    # ------------------------------------------------------------------
    #

    def test_retrieve_chunks(self):

        retriever = DummyRetriever()

        chunks = retriever.retrieve_chunks(
            self.create_query(),
        )

        assert retriever.retrieve_called

        assert len(chunks) == 1

        assert isinstance(
            chunks[0],
            RetrievedChunk,
        )

    #
    # ------------------------------------------------------------------
    # chunk flattening
    # ------------------------------------------------------------------
    #

    def test_retrieve_chunks_flattens_documents(self):

        class MultiRetriever(Retriever):

            def retrieve(
                self,
                query: Query,
            ) -> RetrievalResult:

                doc1 = RetrievedDocument(
                    document_id=uuid4(),
                    score=0.9,
                    chunks=(
                        RetrievedChunk(
                            document_id=uuid4(),
                            chunk_id=uuid4(),
                            text="Chunk 1",
                            similarity=0.9,
                        ),
                        RetrievedChunk(
                            document_id=uuid4(),
                            chunk_id=uuid4(),
                            text="Chunk 2",
                            similarity=0.8,
                        ),
                    ),
                )

                doc2 = RetrievedDocument(
                    document_id=uuid4(),
                    score=0.7,
                    chunks=(
                        RetrievedChunk(
                            document_id=uuid4(),
                            chunk_id=uuid4(),
                            text="Chunk 3",
                            similarity=0.7,
                        ),
                    ),
                )

                return RetrievalResult(
                    query=query,
                    documents=(
                        doc1,
                        doc2,
                    ),
                )

        retriever = MultiRetriever()

        chunks = retriever.retrieve_chunks(
            self.create_query(),
        )

        assert len(chunks) == 3

        assert chunks[0].text == "Chunk 1"

        assert chunks[1].text == "Chunk 2"

        assert chunks[2].text == "Chunk 3"
