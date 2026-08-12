"""
Tests for RetrievalService.
"""

from __future__ import annotations

from uuid import uuid4

from app.context.models import PromptContext
from app.retrieval.models import (
    Query,
    RetrievalResult,
    RetrievedChunk,
    RetrievedDocument,
)
from app.services.retrieval import RetrievalService


class DummyRetriever:
    """Dummy retriever used to test service orchestration."""

    def __init__(
        self,
        result: RetrievalResult,
    ) -> None:
        self.result = result
        self.called = False
        self.last_query: Query | None = None

    def retrieve(
        self,
        query: Query,
    ) -> RetrievalResult:

        self.called = True
        self.last_query = query

        return self.result


class DummyContextBuilder:
    """Dummy context builder used to test service orchestration."""

    def __init__(
        self,
        context: PromptContext,
    ) -> None:
        self.context = context
        self.called = False
        self.last_chunks = None
        self.last_query = None

    def build(
        self,
        chunks,
        *,
        query: str = "",
    ) -> PromptContext:

        self.called = True
        self.last_chunks = tuple(chunks)
        self.last_query = query

        return self.context


class TestRetrievalService:
    """Tests for RetrievalService."""

    @staticmethod
    def create_chunk(
        *,
        document_id=None,
        chunk_id=None,
        text: str = "Example chunk",
        similarity: float = 0.9,
    ) -> RetrievedChunk:

        return RetrievedChunk(
            document_id=document_id or uuid4(),
            chunk_id=chunk_id or uuid4(),
            text=text,
            similarity=similarity,
            metadata={
                "page": 1,
            },
        )

    @staticmethod
    def create_document(
        chunks: tuple[RetrievedChunk, ...],
        *,
        document_id=None,
        score: float | None = None,
    ) -> RetrievedDocument:

        if document_id is None:
            if chunks:
                document_id = chunks[0].document_id
            else:
                document_id = uuid4()

        if score is None:
            score = max(
                (
                    chunk.similarity
                    for chunk in chunks
                ),
                default=0.0,
            )

        return RetrievedDocument(
            document_id=document_id,
            score=score,
            chunks=chunks,
        )

    @staticmethod
    def create_query(
        text: str = "What are the investment risks?",
    ) -> Query:

        return Query(
            text=text,
        )

    @staticmethod
    def create_result(
        documents: tuple[RetrievedDocument, ...],
        query: Query | None = None,
    ) -> RetrievalResult:

        return RetrievalResult(
            query=query or TestRetrievalService.create_query(),
            documents=documents,
        )

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    def test_dependencies_are_exposed(self):

        retriever = DummyRetriever(
            self.create_result(()),
        )

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        assert service.retriever is retriever
        assert (
            service.context_builder
            is context_builder
        )

    # ------------------------------------------------------------------
    # Retriever orchestration
    # ------------------------------------------------------------------

    def test_retrieve_calls_retriever(self):

        query = self.create_query()

        retriever = DummyRetriever(
            self.create_result(()),
        )

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        service.retrieve(query)

        assert retriever.called
        assert retriever.last_query is query

    # ------------------------------------------------------------------
    # Context builder orchestration
    # ------------------------------------------------------------------

    def test_retrieve_calls_context_builder(self):

        chunk = self.create_chunk()

        document = self.create_document(
            (chunk,),
        )

        result = self.create_result(
            (document,),
        )

        retriever = DummyRetriever(result)

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        service.retrieve(
            self.create_query(),
        )

        assert context_builder.called

    def test_query_text_is_passed_to_context_builder(
        self,
    ):

        query = self.create_query(
            "What are the financial risks?",
        )

        retriever = DummyRetriever(
            self.create_result(()),
        )

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        service.retrieve(query)

        assert (
            context_builder.last_query
            == "What are the financial risks?"
        )

    # ------------------------------------------------------------------
    # Flattening documents -> chunks
    # ------------------------------------------------------------------

    def test_all_document_chunks_are_passed_to_builder(
        self,
    ):

        document_a_id = uuid4()
        document_b_id = uuid4()

        chunks_a = (
            self.create_chunk(
                document_id=document_a_id,
                text="Document A - chunk 1",
                similarity=0.95,
            ),
            self.create_chunk(
                document_id=document_a_id,
                text="Document A - chunk 2",
                similarity=0.85,
            ),
        )

        chunks_b = (
            self.create_chunk(
                document_id=document_b_id,
                text="Document B - chunk 1",
                similarity=0.90,
            ),
        )

        documents = (
            self.create_document(
                chunks_a,
                document_id=document_a_id,
            ),
            self.create_document(
                chunks_b,
                document_id=document_b_id,
            ),
        )

        result = self.create_result(
            documents,
        )

        retriever = DummyRetriever(result)

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        service.retrieve(
            self.create_query(),
        )

        assert (
            context_builder.last_chunks
            == (
                chunks_a[0],
                chunks_a[1],
                chunks_b[0],
            )
        )

    def test_empty_documents_pass_empty_chunks(
        self,
    ):

        result = self.create_result(
            (
                self.create_document(()),
                self.create_document(()),
            ),
        )

        retriever = DummyRetriever(result)

        context_builder = DummyContextBuilder(
            PromptContext(),
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        service.retrieve(
            self.create_query(),
        )

        assert context_builder.last_chunks == ()

    # ------------------------------------------------------------------
    # Result propagation
    # ------------------------------------------------------------------

    def test_retrieve_returns_context_builder_result(
        self,
    ):

        chunk = self.create_chunk()

        document = self.create_document(
            (chunk,),
        )

        result = self.create_result(
            (document,),
        )

        expected_context = PromptContext(
            query="What are the investment risks?",
        )

        retriever = DummyRetriever(result)

        context_builder = DummyContextBuilder(
            expected_context,
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        actual_context = service.retrieve(
            self.create_query(),
        )

        assert actual_context is expected_context

    # ------------------------------------------------------------------
    # Empty retrieval
    # ------------------------------------------------------------------

    def test_empty_retrieval_builds_empty_context(
        self,
    ):

        query = self.create_query(
            "No matching information",
        )

        result = self.create_result(
            (),
            query=query,
        )

        expected_context = PromptContext(
            query=query.text,
        )

        retriever = DummyRetriever(result)

        context_builder = DummyContextBuilder(
            expected_context,
        )

        service = RetrievalService(
            retriever=retriever,
            context_builder=context_builder,
        )

        context = service.retrieve(query)

        assert context is expected_context
        assert context_builder.called
        assert context_builder.last_chunks == ()
