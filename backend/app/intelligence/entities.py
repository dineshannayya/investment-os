"""
Investment entity extractor.
"""

from __future__ import annotations

import re

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    IntelligenceEvidence,
    InvestmentEntities,
)
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

        match = cls._find_first_match(
            cls.COMPANY_PATTERNS,
            text,
        )
        
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

    def extract_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        result: InvestmentEntities,
    ) -> tuple[IntelligenceEvidence, ...]:
        """
        Return source evidence supporting extracted entity fields.
        """
    
        text = document.text
        evidence: list[IntelligenceEvidence] = []
    
        field_patterns = (
            ("company_name", self.COMPANY_PATTERNS),
            ("founders", (self.FOUNDER_PATTERN,)),
            ("investors", (self.INVESTOR_PATTERN,)),
            ("accelerators", (self.ACCELERATOR_PATTERN,)),
            ("locations", (self.LOCATION_PATTERN,)),
            ("sectors", (self.SECTOR_PATTERN,)),
            ("products", (self.PRODUCT_PATTERN,)),
            ("technologies", (self.TECHNOLOGY_PATTERN,)),
        )
    
        for field_name, patterns in field_patterns:
            value = getattr(result, field_name)
    
            if not value:
                continue
    
            match = self._find_first_match(
                patterns,
                text,
            )
    
            if match is None:
                continue
    
            chunk = self._find_chunk(
                chunks,
                match.start(),
                match.end(),
            )
    
            evidence.append(
                IntelligenceEvidence(
                    extractor=self.name,
                    field_name=field_name,
                    chunk_index=(
                        chunk.index if chunk is not None else None
                    ),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    text=self._line_context(
                        text,
                        match.start(),
                        match.end(),
                    ),
                )
            )
    
        return tuple(evidence)

    @staticmethod
    def _find_first_match(
        patterns: tuple[re.Pattern[str], ...],
        text: str,
    ) -> re.Match[str] | None:
        """Return the first matching entity label."""
    
        for pattern in patterns:
            match = pattern.search(text)
    
            if match is not None:
                return match
    
        return None

    @staticmethod
    def _line_context(
        text: str,
        start: int,
        end: int,
    ) -> str:
        """Return the complete source line containing a match."""
    
        line_start = text.rfind("\n", 0, start) + 1
    
        line_end = text.find("\n", end)
    
        if line_end == -1:
            line_end = len(text)
    
        return text[line_start:line_end].strip()


    @staticmethod
    def _find_chunk(
        chunks: list[Chunk],
        start: int,
        end: int,
    ) -> Chunk | None:
        """Return the chunk containing the source match."""
    
        for chunk in chunks:
            if (
                chunk.start_offset <= start
                and end <= chunk.end_offset
            ):
                return chunk
    
        return None


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
