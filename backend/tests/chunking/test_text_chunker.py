"""
Tests for TextChunker.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.chunking.base import Chunk
from app.chunking.text import TextChunker
from app.processors import DocumentContent


class TestTextChunker:
    """Tests for TextChunker."""

    @staticmethod
    def create_document(text: str) -> DocumentContent:
        """Create a test document."""

        return DocumentContent(
            document_id=uuid4(),
            title="Test Document",
            text=text,
            page_count=1,
            metadata={},
        )

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------

    def test_default_configuration(self) -> None:
        """Verify default configuration."""

        chunker = TextChunker()

        assert chunker.name == "text"
        assert chunker.chunk_size == 1000
        assert chunker.overlap == 200

    @pytest.mark.parametrize(
        ("chunk_size", "overlap"),
        [
            (0, 0),
            (-1, 0),
        ],
    )
    def test_invalid_chunk_size(
        self,
        chunk_size: int,
        overlap: int,
    ) -> None:
        """Invalid chunk size raises."""

        with pytest.raises(ValueError):
            TextChunker(
                chunk_size=chunk_size,
                overlap=overlap,
            )

    @pytest.mark.parametrize(
        ("chunk_size", "overlap"),
        [
            (100, -1),
            (100, 100),
            (100, 150),
        ],
    )
    def test_invalid_overlap(
        self,
        chunk_size: int,
        overlap: int,
    ) -> None:
        """Invalid overlap raises."""

        with pytest.raises(ValueError):
            TextChunker(
                chunk_size=chunk_size,
                overlap=overlap,
            )

    # -------------------------------------------------------------------------
    # Chunking
    # -------------------------------------------------------------------------

    def test_empty_document(self) -> None:
        """Empty document produces no chunks."""

        chunker = TextChunker()

        chunks = chunker.chunk(
            self.create_document("")
        )

        assert chunks == []

    def test_single_chunk(self) -> None:
        """Short document produces one chunk."""

        chunker = TextChunker(
            chunk_size=100,
            overlap=20,
        )

        document = self.create_document(
            "Investment OS"
        )

        chunks = chunker.chunk(document)

        assert len(chunks) == 1

        chunk = chunks[0]

        assert isinstance(chunk, Chunk)
        assert chunk.index == 0
        assert chunk.text == "Investment OS"
        assert chunk.start_offset == 0
        assert chunk.end_offset == len("Investment OS")
        assert chunk.length == len("Investment OS")

    def test_multiple_chunks(self) -> None:
        """Large document is split."""

        chunker = TextChunker(
            chunk_size=10,
            overlap=2,
        )

        document = self.create_document(
            "abcdefghijklmnopqrstuvwxyz"
        )

        chunks = chunker.chunk(document)

        assert len(chunks) == 3

        assert chunks[0].text == "abcdefghij"
        assert chunks[1].text == "ijklmnopqr"
        assert chunks[2].text == "qrstuvwxyz"

    def test_overlap(self) -> None:
        """Verify overlap is preserved."""

        chunker = TextChunker(
            chunk_size=10,
            overlap=2,
        )

        document = self.create_document(
            "abcdefghijklmnopqrstuvwxyz"
        )

        chunks = chunker.chunk(document)

        assert chunks[0].end_offset - chunks[1].start_offset == 2
        assert chunks[1].end_offset - chunks[2].start_offset == 2

    def test_offsets(self) -> None:
        """Verify offsets."""

        chunker = TextChunker(
            chunk_size=10,
            overlap=2,
        )

        document = self.create_document(
            "abcdefghijklmnopqrstuvwxyz"
        )

        chunks = chunker.chunk(document)

        assert chunks[0].start_offset == 0
        assert chunks[0].end_offset == 10

        assert chunks[1].start_offset == 8
        assert chunks[1].end_offset == 18

        assert chunks[2].start_offset == 16
        assert chunks[2].end_offset == 26

    def test_chunk_metadata(self) -> None:
        """Metadata is propagated."""

        document = self.create_document(
            "Investment OS"
        )

        chunker = TextChunker()

        chunk = chunker.chunk(document)[0]

        assert chunk.metadata["document_id"] == str(
            document.document_id
        )

        assert chunk.metadata["title"] == document.title

    def test_chunk_indices(self) -> None:
        """Chunk indices are sequential."""

        chunker = TextChunker(
            chunk_size=5,
            overlap=1,
        )

        document = self.create_document(
            "abcdefghijklmnop"
        )

        chunks = chunker.chunk(document)

        assert [c.index for c in chunks] == list(
            range(len(chunks))
        )

    def test_supports(self) -> None:
        """Default implementation supports all documents."""

        chunker = TextChunker()

        document = self.create_document("Hello")

        assert chunker.supports(document)
