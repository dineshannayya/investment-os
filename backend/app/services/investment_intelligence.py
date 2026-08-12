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
    InvestmentSignals,
    RiskAssessment,
)
from app.processors import DocumentContent

RESULT_MAPPING :  dict[type, str] = {
    DocumentMetadata: "metadata",
    InvestmentEntities: "entities",
    FinancialMetrics: "financials",
    InvestmentSignals: "signals",
    RiskAssessment: "risks",
}

class InvestmentIntelligenceService:
    """
    Build a structured InvestmentProfile from a processed document.
    """

    def __init__(
        self,
        factory: IntelligenceFactory,
    ) -> None:
        self._factory = factory

    def _calculate_confidence(
        self,
        profile_data: dict[str, any],
    ) -> float:
    
        confidences = (
            profile_data["metadata"].confidence,
            profile_data["entities"].confidence,
            profile_data["financials"].confidence,
            profile_data["signals"].confidence,
            profile_data["risks"].confidence,
        )
    
        return sum(confidences) / len(confidences)


    def analyze(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentProfile:
        """
        Run all registered intelligence extractors.
        """

        #
        # Execute every registered extractor.
        #
        profile_data: dict[str, object] = {
            "metadata": DocumentMetadata(
                title=document.title,
                page_count=document.page_count,
            ),
            "entities": InvestmentEntities(),
            "financials": FinancialMetrics(),
            "signals": InvestmentSignals(),
            "risks": RiskAssessment(),
            "extras": {},
        }
        
        for extractor in self._factory.extractors:
            result = extractor.extract(document, chunks)
        
            for model_type, field_name in RESULT_MAPPING.items():
                if isinstance(result, model_type):
                    profile_data[field_name] = result
                    break
            else:
                profile_data["extras"][extractor.name] = result


        confidence = self._calculate_confidence(profile_data)

        return InvestmentProfile(
            document_id=document.document_id,
            confidence=confidence,
            **profile_data,
        )
