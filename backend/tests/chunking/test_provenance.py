"""Tests for chunk-to-document provenance resolution."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.chunking.base import Chunk
from app.chunking.provenance import ChunkProvenanceResolver
from app.processors import DocumentContent, DocumentSegment


class TestChunkProvenanceResolver:
    """Tests for ChunkProvenanceResolver."""

    @staticmethod
    def create_document(
        text: str,
        segments: tuple[DocumentSegment, ...],
    ) -> DocumentContent:
        """Create a test document."""
        return DocumentContent(
            document_id=uuid4(),
            title="Test Document",
            text=text,
            page_count=1,
            metadata={},
            segments=segments,
        )

    @staticmethod
    def create_segment(
        index: int,
        text: str,
        start_offset: int,
        end_offset: int,
        *,
        segment_type: str = "page",
        page: int | None = None,
    ) -> DocumentSegment:
        """Create a test document segment."""
        metadata = {
            "type": segment_type,
        }

        if page is not None:
            metadata["page"] = page

        return DocumentSegment(
            index=index,
            text=text,
            start_offset=start_offset,
            end_offset=end_offset,
            metadata=metadata,
        )

    @staticmethod
    def create_chunk(
        text: str,
        start_offset: int,
        end_offset: int,
        index: int = 0,
    ) -> Chunk:
        """Create a test chunk."""
        return Chunk(
            index=index,
            text=text,
            start_offset=start_offset,
            end_offset=end_offset,
            metadata={},
        )

    def test_no_segments_returns_empty_tuple(self):
        """A document without segments has no provenance."""
        document = self.create_document(
            text="Investment OS",
            segments=(),
        )

        chunk = self.create_chunk(
            text="Investment",
            start_offset=0,
            end_offset=10,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == ()

    def test_chunk_inside_single_segment(self):
        """A chunk completely inside one segment resolves to that segment."""
        segment = self.create_segment(
            index=0,
            text="Investment OS",
            start_offset=0,
            end_offset=13,
            page=1,
        )

        document = self.create_document(
            text="Investment OS",
            segments=(segment,),
        )

        chunk = self.create_chunk(
            text="Investment",
            start_offset=0,
            end_offset=10,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (segment,)

    def test_chunk_starts_at_segment_boundary(self):
        """A chunk starting at a segment boundary overlaps that segment."""
        segment = self.create_segment(
            index=0,
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
            page=1,
        )

        document = self.create_document(
            text="abcdefghij",
            segments=(segment,),
        )

        chunk = self.create_chunk(
            text="abcde",
            start_offset=0,
            end_offset=5,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (segment,)

    def test_chunk_ending_at_segment_boundary(self):
        """A chunk ending at a segment boundary overlaps that segment."""
        segment = self.create_segment(
            index=0,
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
            page=1,
        )

        document = self.create_document(
            text="abcdefghij",
            segments=(segment,),
        )

        chunk = self.create_chunk(
            text="fghij",
            start_offset=5,
            end_offset=10,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (segment,)

    def test_chunk_crosses_two_segments(self):
        """A chunk crossing a boundary resolves to both segments."""
        segment_one = self.create_segment(
            index=0,
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
            page=1,
        )

        segment_two = self.create_segment(
            index=1,
            text="klmnopqrst",
            start_offset=10,
            end_offset=20,
            page=2,
        )

        document = self.create_document(
            text="abcdefghijklmnopqrst",
            segments=(segment_one, segment_two),
        )

        chunk = self.create_chunk(
            text="ijkl",
            start_offset=8,
            end_offset=12,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (
            segment_one,
            segment_two,
        )

    def test_chunk_does_not_overlap_segment(self):
        """A non-overlapping segment is excluded."""
        segment = self.create_segment(
            index=1,
            text="klmnopqrst",
            start_offset=10,
            end_offset=20,
            page=2,
        )

        document = self.create_document(
            text="abcdefghijklmnopqrst",
            segments=(segment,),
        )

        chunk = self.create_chunk(
            text="abcde",
            start_offset=0,
            end_offset=5,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == ()

    def test_chunk_exactly_matches_one_segment(self):
        """An exact range match resolves to one segment."""
        segment = self.create_segment(
            index=0,
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
            page=1,
        )

        document = self.create_document(
            text="abcdefghij",
            segments=(segment,),
        )

        chunk = self.create_chunk(
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (segment,)

    def test_chunk_crosses_multiple_segments(self):
        """A chunk can overlap multiple document segments."""
        segments = (
            self.create_segment(
                index=0,
                text="abcdefghij",
                start_offset=0,
                end_offset=10,
                page=1,
            ),
            self.create_segment(
                index=1,
                text="klmnopqrst",
                start_offset=10,
                end_offset=20,
                page=2,
            ),
            self.create_segment(
                index=2,
                text="uvwxyzabcd",
                start_offset=20,
                end_offset=30,
                page=3,
            ),
        )

        document = self.create_document(
            text="abcdefghijklmnopqrstuvwxyzabcd",
            segments=segments,
        )

        chunk = self.create_chunk(
            text="ijklmnopqrstuv",
            start_offset=8,
            end_offset=22,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (
            segments[0],
            segments[1],
            segments[2],
        )

    def test_boundary_touching_segments_do_not_overlap(self):
        """Adjacent half-open ranges do not overlap accidentally."""
        segments = (
            self.create_segment(
                index=0,
                text="abcdefghij",
                start_offset=0,
                end_offset=10,
                page=1,
            ),
            self.create_segment(
                index=1,
                text="klmnopqrst",
                start_offset=10,
                end_offset=20,
                page=2,
            ),
        )

        document = self.create_document(
            text="abcdefghijklmnopqrst",
            segments=segments,
        )

        chunk = self.create_chunk(
            text="kl",
            start_offset=10,
            end_offset=12,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert result == (segments[1],)

    def test_result_preserves_document_segment_order(self):
        """Resolved segments preserve document order."""
        segments = (
            self.create_segment(
                index=0,
                text="abcdefghij",
                start_offset=0,
                end_offset=10,
                page=1,
            ),
            self.create_segment(
                index=1,
                text="klmnopqrst",
                start_offset=10,
                end_offset=20,
                page=2,
            ),
            self.create_segment(
                index=2,
                text="uvwxyzabcd",
                start_offset=20,
                end_offset=30,
                page=3,
            ),
        )

        document = self.create_document(
            text="abcdefghijklmnopqrstuvwxyzabcd",
            segments=segments,
        )

        chunk = self.create_chunk(
            text="fghijklmnopq",
            start_offset=5,
            end_offset=17,
        )

        result = ChunkProvenanceResolver.resolve(
            document,
            chunk,
        )

        assert [segment.index for segment in result] == [0, 1]

    @pytest.mark.parametrize(
        "start_offset,end_offset",
        [
            (-1, 5),
            (-10, 0),
        ],
    )
    def test_negative_chunk_start_raises(
        self,
        start_offset: int,
        end_offset: int,
    ):
        """Negative chunk offsets are rejected."""
        document = self.create_document(
            text="Investment OS",
            segments=(),
        )

        chunk = self.create_chunk(
            text="",
            start_offset=start_offset,
            end_offset=end_offset,
        )

        with pytest.raises(
            ValueError,
            match="start_offset cannot be negative",
        ):
            ChunkProvenanceResolver.resolve(
                document,
                chunk,
            )

    def test_chunk_end_before_start_raises(self):
        """Invalid chunk ranges are rejected."""
        document = self.create_document(
            text="Investment OS",
            segments=(),
        )

        chunk = self.create_chunk(
            text="",
            start_offset=10,
            end_offset=5,
        )

        with pytest.raises(
            ValueError,
            match="end_offset cannot be smaller",
        ):
            ChunkProvenanceResolver.resolve(
                document,
                chunk,
            )

    # Empty chunks
    def test_resolve_range_no_chunks_returns_empty_tuple(self):
        result = ChunkProvenanceResolver.resolve_range(
            chunks=[],
            start_offset=0,
            end_offset=10,
        )
    
        assert result == ()
    
    # Range inside one chunk
    def test_resolve_range_inside_single_chunk(self):
        chunk = self.create_chunk(
            text="Investment OS",
            start_offset=0,
            end_offset=13,
        )
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=[chunk],
            start_offset=2,
            end_offset=10,
        )
    
        assert result == (chunk,)
    
    # Range crossing two chunks
    def test_resolve_range_crosses_two_chunks(self):
        chunks = [
            self.create_chunk(
                text="abcdefghij",
                start_offset=0,
                end_offset=10,
                index=0,
            ),
            self.create_chunk(
                text="klmnopqrst",
                start_offset=10,
                end_offset=20,
                index=1,
            ),
        ]
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=chunks,
            start_offset=8,
            end_offset=12,
        )
    
        assert result == (
            chunks[0],
            chunks[1],
        )
    
    # Exact chunk range
    def test_resolve_range_exact_chunk_match(self):
        chunk = self.create_chunk(
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
        )
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=[chunk],
            start_offset=0,
            end_offset=10,
        )
    
        assert result == (chunk,)
    
    # Range doesn't overlap
    def test_resolve_range_no_overlap(self):
        chunk = self.create_chunk(
            text="klmnopqrst",
            start_offset=10,
            end_offset=20,
        )
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=[chunk],
            start_offset=0,
            end_offset=5,
        )
    
        assert result == ()
    
    # Boundary semantics need explicit tests
    def test_resolve_range_at_chunk_boundary(self):
        chunks = [
            self.create_chunk(
                text="abcdefghij",
                start_offset=0,
                end_offset=10,
                index=0,
            ),
            self.create_chunk(
                text="klmnopqrst",
                start_offset=10,
                end_offset=20,
                index=1,
            ),
        ]
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=chunks,
            start_offset=10,
            end_offset=12,
        )
    
        assert result == (chunks[1],)
    
    
    # Invalid range tests
    @pytest.mark.parametrize(
        "start_offset,end_offset",
        [
            (-1, 5),
            (-10, 0),
        ],
    )
    def test_resolve_range_negative_start_raises(
        self,
        start_offset: int,
        end_offset: int,
    ):
        with pytest.raises(
            ValueError,
            match="start_offset cannot be negative",
        ):
            ChunkProvenanceResolver.resolve_range(
                chunks=[],
                start_offset=start_offset,
                end_offset=end_offset,
            )
    
    # zero-length ranges
    def test_resolve_range_zero_length_returns_empty(self):
        chunk = self.create_chunk(
            text="abcdefghij",
            start_offset=0,
            end_offset=10,
        )
    
        result = ChunkProvenanceResolver.resolve_range(
            chunks=[chunk],
            start_offset=5,
            end_offset=5,
        )
    
        assert result == ()
    
