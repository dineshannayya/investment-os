"""
Base interfaces for Investment Intelligence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.chunking.base import Chunk
from app.intelligence.models import IntelligenceEvidence
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

    def extract_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        result: T,
    ) -> tuple[IntelligenceEvidence, ...]:
        """
        Return source evidence supporting the extracted result.

        Extractors may override this method when they can provide
        precise provenance. The default implementation returns no
        evidence.
        """
        return ()
