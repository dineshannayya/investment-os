"""
Tests for ContextBuilder.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.context.builder import ContextBuilder
from app.context.models import (
    ContextBlock,
    ContextDocument,
    PromptContext,
)
from app.retrieval.models import RetrievedChunk


class TestContextBuilder:
    """Tests for ContextBuilder."""

    @staticmethod
    def create_chunk(
        *,
        document_id=None,
        chunk_id=None,
        text: str = "Example chunk",
        similarity: float = 0.8,
        metadata=None,
    ) -> RetrievedChunk:
        """
        Create a test RetrievedChunk.
        """

        return RetrievedChunk(
            document_id=document_id or uuid4(),
            chunk_id=chunk_id or uuid4(),
            text=text,
            similarity=similarity,
            metadata=metadata or {},
        )

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_default_max_chars(self):

        builder = ContextBuilder()

        assert (
            builder.max_chars
            == ContextBuilder.DEFAULT_MAX_CHARS
        )

    def test_custom_max_chars(self):

        builder = ContextBuilder(
            max_chars=5000,
        )

        assert builder.max_chars == 5000

    def test_invalid_max_chars(self):

        with pytest.raises(ValueError):

            ContextBuilder(
                max_chars=0,
            )

        with pytest.raises(ValueError):

            ContextBuilder(
                max_chars=-1,
            )

    # ------------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------------

    def test_build_empty_context(self):

        builder = ContextBuilder()

        context = builder.build(
            [],
            query="What are the risks?",
        )

        assert isinstance(
            context,
            PromptContext,
        )

        assert context.query == "What are the risks?"
        assert context.blocks == ()
        assert context.documents == ()
        assert context.block_count == 0
        assert context.document_count == 0
        assert context.text == ""

    # ------------------------------------------------------------------
    # Query propagation
    # ------------------------------------------------------------------

    def test_query_is_preserved(self):

        builder = ContextBuilder()

        context = builder.build(
            [
                self.create_chunk(),
            ],
            query="What are the financial risks?",
        )

        assert (
            context.query
            == "What are the financial risks?"
        )

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def test_chunk_converted_to_context_block(self):

        document_id = uuid4()
        chunk_id = uuid4()

        chunk = self.create_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Financial risk information",
            similarity=0.91,
            metadata={
                "page": 7,
                "section": "Financials",
            },
        )

        builder = ContextBuilder()

        context = builder.build(
            [chunk],
        )

        assert len(context.blocks) == 1

        block = context.blocks[0]

        assert isinstance(
            block,
            ContextBlock,
        )

        assert block.document_id == document_id
        assert block.chunk_id == chunk_id
        assert block.text == "Financial risk information"
        assert block.relevance == pytest.approx(0.91)

        assert block.metadata["page"] == 7
        assert (
            block.metadata["section"]
            == "Financials"
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def test_duplicate_chunks_are_removed(self):

        document_id = uuid4()
        chunk_id = uuid4()

        first = self.create_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Same chunk",
            similarity=0.9,
        )

        duplicate = self.create_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Same chunk",
            similarity=0.9,
        )

        builder = ContextBuilder()

        context = builder.build(
            [
                first,
                duplicate,
            ],
        )

        assert len(context.blocks) == 1

    def test_same_chunk_id_with_different_text_is_not_deduplicated(
        self,
    ):

        document_id = uuid4()
        chunk_id = uuid4()

        first = self.create_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Original text",
        )

        second = self.create_chunk(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Updated text",
        )

        builder = ContextBuilder()

        context = builder.build(
            [
                first,
                second,
            ],
        )

        assert len(context.blocks) == 2

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def test_chunks_are_sorted_by_relevance(self):

        chunks = [
            self.create_chunk(
                text="Low relevance",
                similarity=0.4,
            ),
            self.create_chunk(
                text="High relevance",
                similarity=0.95,
            ),
            self.create_chunk(
                text="Medium relevance",
                similarity=0.7,
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        assert [
            block.text
            for block in context.blocks
        ] == [
            "High relevance",
            "Medium relevance",
            "Low relevance",
        ]

    def test_equal_relevance_preserves_input_order(self):

        chunks = [
            self.create_chunk(
                text="First",
                similarity=0.8,
            ),
            self.create_chunk(
                text="Second",
                similarity=0.8,
            ),
            self.create_chunk(
                text="Third",
                similarity=0.8,
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        assert [
            block.text
            for block in context.blocks
        ] == [
            "First",
            "Second",
            "Third",
        ]

    # ------------------------------------------------------------------
    # Character budget
    # ------------------------------------------------------------------

    def test_context_respects_max_chars(self):

        builder = ContextBuilder(
            max_chars=20,
        )

        chunks = [
            self.create_chunk(
                text="1234567890",
                similarity=0.9,
            ),
            self.create_chunk(
                text="abcdefghij",
                similarity=0.8,
            ),
            self.create_chunk(
                text="EXCLUDED",
                similarity=0.7,
            ),
        ]

        context = builder.build(chunks)

        assert len(context.blocks) == 2

        assert context.text == (
            "1234567890\n\n"
            "abcdefghij"
        )

    def test_oversized_first_chunk_is_excluded(self):

        builder = ContextBuilder(
            max_chars=10,
        )

        chunks = [
            self.create_chunk(
                text="This chunk is too long",
                similarity=0.9,
            ),
            self.create_chunk(
                text="Short",
                similarity=0.8,
            ),
        ]

        context = builder.build(chunks)

        assert len(context.blocks) == 0

    def test_empty_text_is_skipped(self):

        builder = ContextBuilder()

        chunks = [
            self.create_chunk(
                text="",
                similarity=0.9,
            ),
            self.create_chunk(
                text="Valid content",
                similarity=0.8,
            ),
        ]

        context = builder.build(chunks)

        assert len(context.blocks) == 1
        assert (
            context.blocks[0].text
            == "Valid content"
        )

    # ------------------------------------------------------------------
    # Document grouping
    # ------------------------------------------------------------------

    def test_chunks_are_grouped_by_document(self):

        document_a = uuid4()
        document_b = uuid4()

        chunks = [
            self.create_chunk(
                document_id=document_a,
                text="A1",
                similarity=0.95,
            ),
            self.create_chunk(
                document_id=document_b,
                text="B1",
                similarity=0.85,
            ),
            self.create_chunk(
                document_id=document_a,
                text="A2",
                similarity=0.75,
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        assert len(context.documents) == 2

        assert (
            context.document_count
            == 2
        )

        first_document = context.documents[0]
        second_document = context.documents[1]

        assert isinstance(
            first_document,
            ContextDocument,
        )

        assert first_document.document_id == document_a
        assert [
            block.text
            for block in first_document.blocks
        ] == [
            "A1",
            "A2",
        ]

        assert second_document.document_id == document_b
        assert [
            block.text
            for block in second_document.blocks
        ] == [
            "B1",
        ]

    # ------------------------------------------------------------------
    # Document score
    # ------------------------------------------------------------------

    def test_document_score_is_maximum_block_relevance(
        self,
    ):

        document_id = uuid4()

        chunks = [
            self.create_chunk(
                document_id=document_id,
                text="Lower relevance",
                similarity=0.6,
            ),
            self.create_chunk(
                document_id=document_id,
                text="Highest relevance",
                similarity=0.95,
            ),
            self.create_chunk(
                document_id=document_id,
                text="Medium relevance",
                similarity=0.8,
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        document = context.documents[0]

        assert document.score == pytest.approx(
            0.95,
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_document_metadata_comes_from_first_block(
        self,
    ):

        document_id = uuid4()

        chunks = [
            self.create_chunk(
                document_id=document_id,
                text="First",
                similarity=0.9,
                metadata={
                    "page": 1,
                },
            ),
            self.create_chunk(
                document_id=document_id,
                text="Second",
                similarity=0.8,
                metadata={
                    "page": 2,
                },
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        document = context.documents[0]

        assert document.metadata["page"] == 1

    # ------------------------------------------------------------------
    # Context text
    # ------------------------------------------------------------------

    def test_context_text_uses_block_separator(self):

        chunks = [
            self.create_chunk(
                text="First block",
                similarity=0.9,
            ),
            self.create_chunk(
                text="Second block",
                similarity=0.8,
            ),
        ]

        builder = ContextBuilder()

        context = builder.build(chunks)

        assert context.text == (
            "First block\n\n"
            "Second block"
        )
