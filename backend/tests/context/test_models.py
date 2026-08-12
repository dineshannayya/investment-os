"""
Tests for context domain models.
"""

from __future__ import annotations

from types import MappingProxyType
from uuid import uuid4

import pytest

from app.context.models import (
    ContextBlock,
    ContextDocument,
    PromptContext,
)


class TestContextBlock:
    """Tests for ContextBlock."""

    def test_create(self):

        document_id = uuid4()
        chunk_id = uuid4()

        block = ContextBlock(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Healthcare startup information",
            relevance=0.92,
        )

        assert block.document_id == document_id
        assert block.chunk_id == chunk_id
        assert block.text == "Healthcare startup information"
        assert block.relevance == pytest.approx(0.92)

    def test_chunk_id_can_be_none(self):

        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=None,
            text="Document-level information",
            relevance=0.85,
        )

        assert block.chunk_id is None

    def test_default_metadata(self):

        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            relevance=0.8,
        )

        assert block.metadata == {}
        assert isinstance(
            block.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Financial information",
            relevance=0.9,
            metadata={
                "page": 7,
                "section": "Financials",
            },
        )

        assert block.metadata["page"] == 7
        assert block.metadata["section"] == "Financials"

    def test_frozen(self):

        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            relevance=0.8,
        )

        with pytest.raises(AttributeError):
            block.text = "Changed"

    def test_metadata_is_read_only(self):

        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            relevance=0.8,
            metadata={"page": 1},
        )

        with pytest.raises(TypeError):
            block.metadata["page"] = 2


class TestContextDocument:
    """Tests for ContextDocument."""

    def test_create(self):

        document_id = uuid4()

        block = ContextBlock(
            document_id=document_id,
            chunk_id=uuid4(),
            text="Relevant information",
            relevance=0.9,
        )

        document = ContextDocument(
            document_id=document_id,
            blocks=(block,),
            score=0.9,
        )

        assert document.document_id == document_id
        assert document.blocks == (block,)
        assert document.score == pytest.approx(0.9)

    def test_default_blocks(self):

        document = ContextDocument(
            document_id=uuid4(),
        )

        assert document.blocks == ()
        assert document.score == 0.0

    def test_default_metadata(self):

        document = ContextDocument(
            document_id=uuid4(),
        )

        assert document.metadata == {}
        assert isinstance(
            document.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        document = ContextDocument(
            document_id=uuid4(),
            metadata={
                "document_type": "pitch_deck",
                "page_count": 25,
            },
        )

        assert (
            document.metadata["document_type"]
            == "pitch_deck"
        )
        assert document.metadata["page_count"] == 25

    def test_frozen(self):

        document = ContextDocument(
            document_id=uuid4(),
        )

        with pytest.raises(AttributeError):
            document.score = 1.0

    def test_metadata_is_read_only(self):

        document = ContextDocument(
            document_id=uuid4(),
            metadata={"page_count": 10},
        )

        with pytest.raises(TypeError):
            document.metadata["page_count"] = 20


class TestPromptContext:
    """Tests for PromptContext."""

    def test_create(self):

        document_id = uuid4()

        block = ContextBlock(
            document_id=document_id,
            chunk_id=uuid4(),
            text="Relevant information",
            relevance=0.95,
        )

        document = ContextDocument(
            document_id=document_id,
            blocks=(block,),
            score=0.95,
        )

        context = PromptContext(
            query="What are the financial risks?",
            blocks=(block,),
            documents=(document,),
        )

        assert context.query == "What are the financial risks?"
        assert context.blocks == (block,)
        assert context.documents == (document,)

    def test_defaults(self):

        context = PromptContext()

        assert context.query == ""
        assert context.blocks == ()
        assert context.documents == ()
        assert context.metadata == {}

    def test_default_metadata(self):

        context = PromptContext()

        assert isinstance(
            context.metadata,
            MappingProxyType,
        )

    def test_metadata(self):

        context = PromptContext(
            query="What are the risks?",
            metadata={
                "retrieval_strategy": "semantic",
                "top_k": 10,
            },
        )

        assert (
            context.metadata["retrieval_strategy"]
            == "semantic"
        )
        assert context.metadata["top_k"] == 10

    def test_block_count(self):

        document_id = uuid4()

        blocks = (
            ContextBlock(
                document_id=document_id,
                chunk_id=uuid4(),
                text="Block 1",
                relevance=0.9,
            ),
            ContextBlock(
                document_id=document_id,
                chunk_id=uuid4(),
                text="Block 2",
                relevance=0.8,
            ),
        )

        context = PromptContext(
            blocks=blocks,
        )

        assert context.block_count == 2

    def test_document_count(self):

        context = PromptContext(
            documents=(
                ContextDocument(
                    document_id=uuid4(),
                ),
                ContextDocument(
                    document_id=uuid4(),
                ),
            ),
        )

        assert context.document_count == 2

    def test_text(self):

        context = PromptContext(
            blocks=(
                ContextBlock(
                    document_id=uuid4(),
                    chunk_id=uuid4(),
                    text="First relevant block",
                    relevance=0.9,
                ),
                ContextBlock(
                    document_id=uuid4(),
                    chunk_id=uuid4(),
                    text="Second relevant block",
                    relevance=0.8,
                ),
            ),
        )

        assert context.text == (
            "First relevant block\n\n"
            "Second relevant block"
        )

    def test_empty_text(self):

        context = PromptContext()

        assert context.text == ""

    def test_frozen(self):

        context = PromptContext(
            query="Example",
        )

        with pytest.raises(AttributeError):
            context.query = "Changed"

    def test_metadata_is_read_only(self):

        context = PromptContext(
            metadata={"source": "retrieval"},
        )

        with pytest.raises(TypeError):
            context.metadata["source"] = "other"

    def test_metadata_is_detached_from_source_dict(self):
    
        metadata = {"page": 1}
    
        block = ContextBlock(
            document_id=uuid4(),
            chunk_id=uuid4(),
            text="Example",
            relevance=0.8,
            metadata=metadata,
        )
    
        metadata["page"] = 99
    
        assert block.metadata["page"] == 1
    
