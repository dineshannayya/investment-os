"""
Context domain models.

These models represent structured context assembled from retrieved
document chunks for downstream AI processing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ContextBlock:
    """
    A single piece of retrieved content included in the context.
    """

    document_id: UUID

    chunk_id: UUID | None

    text: str

    relevance: float

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(slots=True, frozen=True)
class ContextDocument:
    """
    Context assembled from one document.

    A document may contribute multiple context blocks.
    """

    document_id: UUID

    blocks: tuple[ContextBlock, ...] = ()

    score: float = 0.0

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(slots=True, frozen=True)
class PromptContext:
    """
    Complete context prepared for downstream prompt construction.
    """

    blocks: tuple[ContextBlock, ...] = ()

    documents: tuple[ContextDocument, ...] = ()

    query: str = ""

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


    @property
    def block_count(self) -> int:
        """
        Return the number of context blocks.
        """

        return len(self.blocks)

    @property
    def document_count(self) -> int:
        """
        Return the number of documents represented in the context.
        """

        return len(self.documents)

    @property
    def text(self) -> str:
        """
        Return context blocks as a single text representation.
        """

        return "\n\n".join(
            block.text
            for block in self.blocks
        )
