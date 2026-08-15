"""
Base interfaces for document chunking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.processors import DocumentContent

# ============================================================================
# Chunk Model
# ============================================================================


@dataclass(slots=True, frozen=True)
class Chunk:
    """
    Represents a chunk of extracted document text.
    """

    index: int

    text: str

    start_offset: int

    end_offset: int

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        """
        Number of characters in the chunk.
        """
        return len(self.text)


# ============================================================================
# Chunker Interface
# ============================================================================


class Chunker(ABC):
    """
    Base class for document chunkers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable chunker name.
        """

    @abstractmethod
    def chunk(
        self,
        document: DocumentContent,
    ) -> list[Chunk]:
        """
        Split a document into chunks.
        """

    def supports(
        self,
        document: DocumentContent,
    ) -> bool:
        """
        Return whether this chunker can process the document.

        The default implementation accepts all documents.
        """
        return True
