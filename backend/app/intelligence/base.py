"""
Base interfaces for Investment Intelligence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.chunking.base import Chunk
from app.processors import DocumentContent

# Generic result type returned by an extractor.
T = TypeVar("T")


class IntelligenceExtractor(ABC, Generic[T]):
    """
    Base class for all intelligence extractors.

    An extractor analyzes a processed document and its chunks,
    producing a structured intelligence model.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable extractor name.
        """

    @abstractmethod
    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> T:
        """
        Extract structured information from a document.
        """

    def supports(
        self,
        document: DocumentContent,
    ) -> bool:
        """
        Return whether this extractor supports the document.

        The default implementation accepts all documents.
        """
        return True
