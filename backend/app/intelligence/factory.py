"""
Investment Intelligence factory.
"""

from __future__ import annotations

from typing import Any

from app.intelligence.base import IntelligenceExtractor
from app.intelligence.entities import EntityExtractor
from app.intelligence.financial import FinancialExtractor
from app.intelligence.metadata import MetadataExtractor
from app.intelligence.risk import RiskExtractor
from app.intelligence.signals import SignalExtractor


class IntelligenceFactory:
    """
    Registry for intelligence extractors.
    """

    def __init__(self) -> None:
        self._extractors: list[IntelligenceExtractor[Any]] = []

    @property
    def extractors(self) -> tuple[IntelligenceExtractor[Any], ...]:
        """
        Registered extractors.
        """
        return tuple(self._extractors)

    def register(
        self,
        extractor: IntelligenceExtractor[Any],
    ) -> None:
        """
        Register an extractor.

        Duplicate registrations are ignored.
        """

        if extractor in self._extractors:
            return

        self._extractors.append(extractor)

    def clear(self) -> None:
        """
        Remove all registered extractors.
        """

        self._extractors.clear()

    def run(
        self,
        document,
        chunks,
    ) -> dict[str, Any]:
        """
        Run all compatible extractors.

        Returns a dictionary keyed by extractor name.
        """

        results: dict[str, Any] = {}

        for extractor in self._extractors:
            if extractor.supports(document):
                results[extractor.name] = extractor.extract(
                    document,
                    chunks,
                )

        return results


def create_intelligence_factory() -> IntelligenceFactory:
    """
    Create the default intelligence factory.
    """

    factory = IntelligenceFactory()

    for extractor in (
        MetadataExtractor(),
        EntityExtractor(),
        FinancialExtractor(),
        SignalExtractor(),
        RiskExtractor(),
    ):
        factory.register(extractor)

    return factory
