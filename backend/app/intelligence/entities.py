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
        re.compile(
            r"(?im)^[ \t]*company[ \t]*:[ \t]*([^\r\n]*)$"
        ),
        re.compile(
            r"(?im)^[ \t]*startup[ \t]*:[ \t]*([^\r\n]*)$"
        ),
        re.compile(
            r"(?im)^[ \t]*organization[ \t]*:[ \t]*([^\r\n]*)$"
        ),
    )
    
    FOUNDER_PATTERN = re.compile(
        r"(?im)^[ \t]*founders?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    INVESTOR_PATTERN = re.compile(
        r"(?im)^[ \t]*investors?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    ACCELERATOR_PATTERN = re.compile(
        r"(?im)^[ \t]*accelerators?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    LOCATION_PATTERN = re.compile(
        r"(?im)^[ \t]*locations?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    SECTOR_PATTERN = re.compile(
        r"(?im)^[ \t]*sectors?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    PRODUCT_PATTERN = re.compile(
        r"(?im)^[ \t]*products?[ \t]*:[ \t]*([^\r\n]*)$"
    )
    
    TECHNOLOGY_PATTERN = re.compile(
        r"(?im)^[ \t]*technolog(?:y|ies)[ \t]*:[ \t]*([^\r\n]*)$"
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

        Extraction remains deterministic and label-driven. ``chunks`` is
        accepted as part of the IntelligenceExtractor contract but is not
        used for inference in this iteration.
        """

        del chunks

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

    @staticmethod
    def _normalize_value(value: str) -> str:
        """
        Normalize whitespace without changing the entity's content.
        """

        return " ".join(value.strip().split())

    @classmethod
    def _extract_company(
        cls,
        text: str,
    ) -> str | None:
        """
        Extract the primary company/startup name.
        """

        for pattern in cls.COMPANY_PATTERNS:
            match = pattern.search(text)

            if match:
                value = cls._normalize_value(match.group(1))

                if value:
                    return value

        return None

    @classmethod
    def _extract_list(
        cls,
        pattern: re.Pattern[str],
        text: str,
    ) -> tuple[str, ...]:
        """
        Extract a comma/semicolon separated list.

        Values are normalized and duplicate values are removed while
        preserving their original order.
        """

        match = pattern.search(text)

        if match is None:
            return ()

        values: list[str] = []
        seen: set[str] = set()

        for raw_value in cls.SPLIT_PATTERN.split(match.group(1)):
            value = cls._normalize_value(raw_value)

            if not value:
                continue

            normalized_key = value.casefold()

            if normalized_key in seen:
                continue

            seen.add(normalized_key)
            values.append(value)

        return tuple(values)

    @classmethod
    def _calculate_confidence(
        cls,
        text: str,
    ) -> float:
        """
        Calculate a simple confidence score.

        Confidence increases with the number of recognized investment
        entity fields. The scoring model remains intentionally simple
        and deterministic.
        """

        patterns = (
            cls.COMPANY_PATTERNS
            + (
                cls.FOUNDER_PATTERN,
                cls.INVESTOR_PATTERN,
                cls.ACCELERATOR_PATTERN,
                cls.LOCATION_PATTERN,
                cls.SECTOR_PATTERN,
                cls.PRODUCT_PATTERN,
                cls.TECHNOLOGY_PATTERN,
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
