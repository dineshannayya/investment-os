"""Utilities for resolving document provenance for text chunks."""

from __future__ import annotations

from app.chunking.base import Chunk
from app.processors import DocumentContent, DocumentSegment


class ChunkProvenanceResolver:
    """Resolve document segments overlapping a text chunk."""

    @staticmethod
    def resolve(
        document: DocumentContent,
        chunk: Chunk,
    ) -> tuple[DocumentSegment, ...]:
        """Return document segments overlapping the chunk range.

        Ranges are half-open: [start_offset, end_offset).
        """

        if chunk.start_offset < 0:
            raise ValueError("chunk.start_offset cannot be negative")

        if chunk.end_offset < chunk.start_offset:
            raise ValueError(
                "chunk.end_offset cannot be smaller than "
                "chunk.start_offset"
            )

        if not document.segments:
            return ()

        return tuple(
            segment
            for segment in document.segments
            if (
                chunk.start_offset < segment.end_offset
                and chunk.end_offset > segment.start_offset
            )
        )

    @staticmethod
    def resolve_range(
        chunks: list[Chunk],
        start_offset: int,
        end_offset: int,
    ) -> tuple[Chunk, ...]:
        """Return chunks overlapping a source text range.
    
        Ranges are half-open: [start_offset, end_offset).
        """
    
        if start_offset < 0:
            raise ValueError(
                "start_offset cannot be negative"
            )
    
        if end_offset < start_offset:
            raise ValueError(
                "end_offset cannot be smaller than start_offset"
            )

        if start_offset == end_offset:
            return ()
    
        if not chunks:
            return ()
    
        return tuple(
            chunk
            for chunk in chunks
            if (
                start_offset < chunk.end_offset
                and end_offset > chunk.start_offset
            )
        )



__all__ = ["ChunkProvenanceResolver"]
