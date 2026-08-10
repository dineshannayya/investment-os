"""
Investment entity extractor.
"""

from __future__ import annotations

import re

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import InvestmentEntities
from app.processors import DocumentContent


class EntityExtractor(IntelligenceExtractor[InvestmentEntities]):
    """
    Extract investment-related named entities from a processed document.

    This implementation is intentionally deterministic and relies on
    simple rules and regular expressions rather than NLP libraries.
    """

    COMPANY_PATTERNS = (
        re.compile(r"(?im)^company\s*:\s*(.+)$"),
        re.compile(r"(?im)^startup\s*:\s*(.+)$"),
        re.compile(r"(?im)^organization\s*:\s*(.+)$"),
    )

    FOUNDER_PATTERN = re.compile(
        r"(?im)^founders?\s*:\s*(.+)$"
    )

    INVESTOR_PATTERN = re.compile(
        r"(?im)^investors?\s*:\s*(.+)$"
    )

    ACCELERATOR_PATTERN = re.compile(
        r"(?im)^accelerators?\s*:\s*(.+)$"
    )

    LOCATION_PATTERN = re.compile(
        r"(?im)^location\s*:\s*(.+)$"
    )

    SECTOR_PATTERN = re.compile(
        r"(?im)^sector\s*:\s*(.+)$"
    )

    PRODUCT_PATTERN = re.compile(
        r"(?im)^products?\s*:\s*(.+)$"
    )

    TECHNOLOGY_PATTERN = re.compile(
        r"(?im)^technolog(?:y|ies)\s*:\s*(.+)$"
    )

    SPLIT_PATTERN = re.compile(r"\s*,\s*|\s*;\s*")

    @property
    def name(self) -> str:
        return "entities"

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentEntities:
        """
        Extract entities from the document.
        """

        text = document.text

        return InvestmentEntities(
            company_name=self._extract_company(text),
            founders=self._extract_list(
                self.FOUNDER_PATTERN,
                text,
            ),
            investors=self._extract_list(
                self.INVESTOR_PATTERN,
                text,
            ),
            accelerators=self._extract_list(
                self.ACCELERATOR_PATTERN,
                text,
            ),
            locations=self._extract_list(
                self.LOCATION_PATTERN,
                text,
            ),
            sectors=self._extract_list(
                self.SECTOR_PATTERN,
                text,
            ),
            products=self._extract_list(
                self.PRODUCT_PATTERN,
                text,
            ),
            technologies=self._extract_list(
                self.TECHNOLOGY_PATTERN,
                text,
            ),
            confidence=self._calculate_confidence(text),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_company(
        self,
        text: str,
    ) -> str | None:
        """
        Extract the primary company/startup name.
        """

        for pattern in self.COMPANY_PATTERNS:
            match = pattern.search(text)

            if match:
                return match.group(1).strip()

        return None

    def _extract_list(
        self,
        pattern: re.Pattern[str],
        text: str,
    ) -> tuple[str, ...]:
        """
        Extract a comma/semicolon separated list.
        """

        match = pattern.search(text)

        if match is None:
            return ()

        values = []

        for value in self.SPLIT_PATTERN.split(match.group(1)):
            value = value.strip()

            if value and value not in values:
                values.append(value)

        return tuple(values)

    def _calculate_confidence(
        self,
        text: str,
    ) -> float:
        """
        Calculate a simple confidence score.

        Confidence increases with the number of recognised
        investment entity fields.
        """

        patterns = (
            self.COMPANY_PATTERNS
            + (
                self.FOUNDER_PATTERN,
                self.INVESTOR_PATTERN,
                self.ACCELERATOR_PATTERN,
                self.LOCATION_PATTERN,
                self.SECTOR_PATTERN,
                self.PRODUCT_PATTERN,
                self.TECHNOLOGY_PATTERN,
            )
        )

        matches = 0

        for pattern in patterns:
            if isinstance(pattern, tuple):
                if any(p.search(text) for p in pattern):
                    matches += 1
            elif pattern.search(text):
                matches += 1

        return min(1.0, 0.25 + (matches * 0.1))
