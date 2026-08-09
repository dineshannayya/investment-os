"""
Text chunker implementation.
"""

from __future__ import annotations

from app.chunking.base import Chunk, Chunker
from app.processors import DocumentContent


class TextChunker(Chunker):
    """
    Character-based text chunker.

    Splits a document into fixed-size chunks with optional overlap.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if overlap < 0:
            raise ValueError("overlap cannot be negative.")

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self._chunk_size = chunk_size
        self._overlap = overlap

    @property
    def name(self) -> str:
        return "text"

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @property
    def overlap(self) -> int:
        return self._overlap

    @property
    def step(self) -> int:
        """Number of characters to advance for the next chunk."""
        return self._chunk_size - self._overlap


    def chunk(
        self,
        document: DocumentContent,
    ) -> list[Chunk]:
        """
        Split a document into overlapping chunks.
        """

        text = document.text

        if not text:
            return []

        chunks: list[Chunk] = []

        step = self._chunk_size - self._overlap

        start = 0
        index = 0

        while start < len(text):
            end = min(start + self._chunk_size, len(text))

            chunk_text = text[start:end]

            chunks.append(
                Chunk(
                    index=index,
                    text=chunk_text,
                    start_offset=start,
                    end_offset=end,
                    metadata={
                        "document_id": str(document.document_id),
                        "title": document.title,
                        "chunk_index": index,
                    },
                )
            )

            if end >= len(text):
                break

            start += self.step
            index += 1

        return chunks
