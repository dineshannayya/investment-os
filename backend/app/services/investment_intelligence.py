"""
Investment Intelligence service.
"""

from __future__ import annotations

from app.chunking.base import Chunk
from app.intelligence.factory import IntelligenceFactory
from app.intelligence.models import (
    DocumentMetadata,
    FinancialMetrics,
    InvestmentEntities,
    InvestmentProfile,
)
from app.processors import DocumentContent


class InvestmentIntelligenceService:
    """
    Service responsible for extracting structured investment
    intelligence from processed documents.
    """

    def __init__(
        self,
        *,
        factory: IntelligenceFactory,
    ) -> None:
        self._factory = factory

    @property
    def factory(self) -> IntelligenceFactory:
        """
        Intelligence factory.
        """
        return self._factory

    def analyze(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentProfile:
        """
        Analyze a processed document.

        Returns
        -------
        InvestmentProfile
            Consolidated investment intelligence.
        """

        results = self._factory.run(
            document=document,
            chunks=chunks,
        )

        metadata = results.get("metadata")

        if metadata is None:
            metadata = DocumentMetadata(
                title=document.title or "Untitled",
                page_count=document.page_count,
            )

        entities = results.get(
            "entities",
            InvestmentEntities(),
        )

        financials = results.get(
            "financials",
            FinancialMetrics(),
        )

        return InvestmentProfile(
            document_id=document.document_id,
            metadata=metadata,
            entities=entities,
            financials=financials,
            confidence=self._calculate_confidence(
                metadata,
                entities,
                financials,
            ),
        )

    def _calculate_confidence(
        self,
        metadata: DocumentMetadata,
        entities: InvestmentEntities,
        financials: FinancialMetrics,
    ) -> float:
        """
        Calculate an overall confidence score.

        Currently implemented as the arithmetic mean of the
        available extractor confidence values.
        """

        confidences = [
            metadata.confidence,
            entities.confidence,
            financials.confidence,
        ]

        return sum(confidences) / len(confidences)
