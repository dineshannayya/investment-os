"""
Investment Intelligence service.
"""

from __future__ import annotations

from typing import Any

from app.chunking.base import Chunk
from app.intelligence.factory import IntelligenceFactory
from app.intelligence.models import (
    DocumentMetadata,
    FinancialMetrics,
    IntelligenceEvidence,
    InvestmentEntities,
    InvestmentProfile,
    InvestmentSignals,
    RiskAssessment,
)

from app.processors import DocumentContent


RESULT_MAPPING: dict[type, str] = {
    DocumentMetadata: "metadata",
    InvestmentEntities: "entities",
    FinancialMetrics: "financials",
    InvestmentSignals: "signals",
    RiskAssessment: "risks",
}

EXPECTED_COMPONENTS: tuple[str, ...] = (
    "metadata",
    "entities",
    "financials",
    "signals",
    "risks",
)


class InvestmentIntelligenceService:
    """
    Build a structured InvestmentProfile from a processed document.

    The service coordinates the registered intelligence extractors and
    consolidates their results into a single InvestmentProfile.
    """

    def __init__(
        self,
        factory: IntelligenceFactory,
    ) -> None:
        self._factory = factory

    def _calculate_confidence(
        self,
        profile_data: dict[str, Any],
    ) -> float:
        """
        Calculate the overall intelligence confidence.

        The current confidence model remains the arithmetic mean of the
        confidence values produced by the five core intelligence
        components.
        """

        confidences = tuple(
            profile_data[field].confidence
            for field in EXPECTED_COMPONENTS
        )

        return sum(confidences) / len(confidences)

    def _build_quality_metadata(
        self,
        profile_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build deterministic quality/completeness metadata.

        This metadata describes which core intelligence components were
        actually supplied by registered extractors. It does not reinterpret
        or modify the confidence values produced by individual extractors.
        """

        component_confidence = {
            field: profile_data[field].confidence
            for field in EXPECTED_COMPONENTS
        }

        available_components = tuple(
            field
            for field in EXPECTED_COMPONENTS
            if profile_data.get(
                f"_{field}_available",
                False,
            )
        )

        missing_components = tuple(
            field
            for field in EXPECTED_COMPONENTS
            if field not in available_components
        )

        return {
            "components_expected": len(EXPECTED_COMPONENTS),
            "components_available": len(available_components),
            "components_missing": len(missing_components),
            "available_components": available_components,
            "missing_components": missing_components,
            "component_confidence": component_confidence,
        }

    def analyze(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentProfile:
        """
        Run all registered intelligence extractors.
        """

        profile_data: dict[str, Any] = {
            "metadata": DocumentMetadata(
                title=document.title,
                page_count=document.page_count,
            ),
            "entities": InvestmentEntities(),
            "financials": FinancialMetrics(),
            "signals": InvestmentSignals(),
            "risks": RiskAssessment(),
            "evidence": [],
            "extras": {},

        }

        # Track which core components were actually produced by an
        # extractor. Defaults above remain valid fallback objects.
        for field_name in EXPECTED_COMPONENTS:
            profile_data[f"_{field_name}_available"] = False

        for extractor in self._factory.extractors:
            if not extractor.supports(document):
                continue
        
            result = extractor.extract(
                document,
                chunks,
            )
        
            evidence = extractor.extract_evidence(
                document,
                chunks,
                result,
            )
        
            if evidence:
                profile_data["evidence"].extend(evidence)
        
            for model_type, field_name in RESULT_MAPPING.items():
                if isinstance(result, model_type):
                    profile_data[field_name] = result
                    profile_data[f"_{field_name}_available"] = True
                    break
            else:
                profile_data["extras"][extractor.name] = result
        

        confidence = self._calculate_confidence(profile_data)

        quality = self._build_quality_metadata(profile_data)

        profile_data["extras"]["intelligence_quality"] = quality

        # Internal bookkeeping fields must not become InvestmentProfile
        # constructor arguments.
        for field_name in EXPECTED_COMPONENTS:
            profile_data.pop(f"_{field_name}_available", None)

        profile_data["evidence"] = tuple(
            profile_data["evidence"]
        )

        return InvestmentProfile(
            document_id=document.document_id,
            confidence=confidence,
            **profile_data,
        )
