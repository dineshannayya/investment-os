"""
Context builder.

Transforms retrieved chunks into a structured, bounded PromptContext.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.context.models import (
    ContextBlock,
    ContextDocument,
    PromptContext,
)
from app.retrieval.models import RetrievedChunk


class ContextBuilder:
    """
    Build bounded prompt context from retrieved chunks.

    The builder is deterministic and does not depend on any LLM,
    tokenizer, or prompt provider.
    """

    DEFAULT_MAX_CHARS = 12000

    def __init__(
        self,
        *,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        if max_chars <= 0:
            raise ValueError(
                "max_chars must be greater than zero."
            )

        self._max_chars = max_chars

    @property
    def max_chars(self) -> int:
        """
        Return the maximum context size in characters.
        """
        return self._max_chars

    def build(
        self,
        chunks: tuple[RetrievedChunk, ...] | list[RetrievedChunk],
        *,
        query: str = "",
    ) -> PromptContext:
        """
        Build prompt context from retrieved chunks.
        """

        unique_chunks = self._deduplicate(chunks)

        ordered_chunks = self._sort(unique_chunks)

        selected_chunks = self._apply_budget(
            ordered_chunks,
        )

        blocks = tuple(
            self._to_context_block(chunk)
            for chunk in selected_chunks
        )

        documents = self._group_documents(
            blocks,
        )

        return PromptContext(
            query=query,
            blocks=blocks,
            documents=documents,
        )

    def _deduplicate(
        self,
        chunks: tuple[RetrievedChunk, ...] | list[RetrievedChunk],
    ) -> tuple[RetrievedChunk, ...]:
        """
        Remove duplicate chunks while preserving the first occurrence.
        """

        seen: set[tuple[UUID, UUID | None, str]] = set()
        unique: list[RetrievedChunk] = []

        for chunk in chunks:
            key = (
                chunk.document_id,
                chunk.chunk_id,
                chunk.text,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(chunk)

        return tuple(unique)

    @staticmethod
    def _sort(
        chunks: tuple[RetrievedChunk, ...],
    ) -> tuple[RetrievedChunk, ...]:
        """
        Sort chunks by descending similarity.

        Python's sort is stable, so chunks with equal similarity
        retain their original retrieval order.
        """

        return tuple(
            sorted(
                chunks,
                key=lambda chunk: chunk.similarity,
                reverse=True,
            )
        )

    def _apply_budget(
        self,
        chunks: tuple[RetrievedChunk, ...],
    ) -> tuple[RetrievedChunk, ...]:
        """
        Select chunks without exceeding the configured character budget.
        """

        selected: list[RetrievedChunk] = []
        total_chars = 0

        for chunk in chunks:
            chunk_size = len(chunk.text)

            if not chunk.text:
                continue

            if (
                selected
                and total_chars + chunk_size
                > self._max_chars
            ):
                break

            if (
                not selected
                and chunk_size > self._max_chars
            ):
                # Do not silently truncate source content at this layer.
                # A future tokenizer/chunking layer can handle truncation.
                break

            selected.append(chunk)
            total_chars += chunk_size

        return tuple(selected)

    @staticmethod
    def _to_context_block(
        chunk: RetrievedChunk,
    ) -> ContextBlock:
        """
        Convert a retrieved chunk into a context block.
        """

        return ContextBlock(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            relevance=chunk.similarity,
            metadata=chunk.metadata,
        )

    @staticmethod
    def _group_documents(
        blocks: tuple[ContextBlock, ...],
    ) -> tuple[ContextDocument, ...]:
        """
        Group context blocks by document while preserving document order.
        """

        grouped: dict[UUID, list[ContextBlock]] = defaultdict(list)

        for block in blocks:
            grouped[block.document_id].append(block)

        documents: list[ContextDocument] = []

        for document_id, document_blocks in grouped.items():
            block_tuple = tuple(document_blocks)

            score = max(
                block.relevance
                for block in block_tuple
            )

            metadata = (
                block_tuple[0].metadata
                if block_tuple
                else {}
            )

            documents.append(
                ContextDocument(
                    document_id=document_id,
                    blocks=block_tuple,
                    score=score,
                    metadata=metadata,
                )
            )

        return tuple(documents)
