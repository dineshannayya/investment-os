"""
Vector store factory.
"""

from __future__ import annotations

from app.vectorstore.base import VectorStore
from app.vectorstore.memory import MemoryVectorStore


class VectorStoreFactory:
    """
    Factory for vector store implementations.

    The factory manages a single active vector store implementation,
    allowing different backends (Memory, PGVector, Qdrant, Milvus,
    Weaviate, etc.) to be plugged in without changing application code.
    """

    DEFAULT_STORE = MemoryVectorStore

    def __init__(
        self,
        store: VectorStore | None = None,
    ) -> None:
        self._store = (
            store
            if store is not None
            else self.DEFAULT_STORE()
        )

    @property
    def store(self) -> VectorStore:
        """
        Return the active vector store.
        """
        return self._store

    @property
    def store_name(self) -> str:
        """
        Return the active vector store name.
        """
        return self._store.__class__.__name__

    @property
    def backend(self) -> str:
        """
        Return the configured backend identifier.
        """
        return self.store_name.lower().replace("vectorstore", "")


    def set_store(
        self,
        store: VectorStore,
    ) -> None:
        """
        Replace the active vector store.
        """
        self._store = store

