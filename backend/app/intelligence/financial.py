"""
Financial intelligence extractor.

Money syntax and normalization are delegated to MoneyParser.
FinancialExtractor is responsible only for semantic classification.
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    FinancialMetrics,
    IntelligenceEvidence,
)
from app.intelligence.parsers import (
    DurationParser,
    MoneyOccurrence,
    MoneyParser,
)
from app.processors import DocumentContent


class ValuationType(str, Enum):
    """Classification of a document-derived valuation."""

    PRE_MONEY = "pre_money"
    POST_MONEY = "post_money"
    VALUATION_CAP = "valuation_cap"
    UNSPECIFIED = "unspecified"


class FinancialExtractor(
    IntelligenceExtractor[FinancialMetrics]
):
    """
    Extract structured financial metrics from investment documents.

    MoneyParser owns monetary syntax, normalization, currency handling, and
    source offsets. This extractor owns only semantic classification.
    """

    CONTEXT_WINDOW = 40

    # These patterns classify an already-parsed MoneyOccurrence.
    # They intentionally do not contain monetary syntax.
    RAISE_CONTEXT_PATTERNS = (
        r"\bamount\s+(?:being\s+)?raised\b",
        r"\braise\s+amount\b",
        r"\btarget\s+raise\b",
        r"\bfundraising\s+(?:target|amount)\b",
        r"\bamount\s+raising\b",
        r"\bcurrently\s+raising\b",
        r"\braising\b",
        r"\braised\b",
        r"\b(?:funding|financing|investment)\s+round\b",
        r"\bround\s+size\b",
    )

    VALUATION_CONTEXT_PATTERNS = (
        (
            ValuationType.PRE_MONEY,
            r"\bpre[-\s]?money\s+valuation\b",
        ),
        (
            ValuationType.POST_MONEY,
            r"\bpost[-\s]?money\s+valuation\b",
        ),
        (
            ValuationType.VALUATION_CAP,
            r"\bvaluation\s+cap\b",
        ),
        (
            ValuationType.UNSPECIFIED,
            (
                r"\b(?:numeric|company|current|estimated|"
                r"indicative)?\s*valuation\b"
            ),
        ),
        (
            ValuationType.UNSPECIFIED,
            r"\bvalued\s+at\b",
        ),
    )

    #
    # field_name, semantic keywords
    #
    METRIC_MAPPING = (
        (
            "revenue",
            (
                "revenue",
                "sales",
                "income",
            ),
        ),
        (
            "ebitda",
            (
                "ebitda",
            ),
        ),
        (
            "arr",
            (
                "arr",
                "annual recurring revenue",
            ),
        ),
        (
            "burn_rate",
            (
                "burn",
                "burn rate",
            ),
        ),
    )

    @property
    def name(self) -> str:
        return "financials"

    def _occurrence_context(
        self,
        text: str,
        occurrence: MoneyOccurrence,
    ) -> str:
        """
        Return bounded semantic context for a monetary occurrence.
    
        Context does not cross a source-line boundary. This prevents a
        financial value on one line from inheriting semantic meaning from
        another financial statement on the next line.
        """
    
        line_start = text.rfind("\n", 0, occurrence.start) + 1
    
        line_end = text.find("\n", occurrence.end)
    
        if line_end == -1:
            line_end = len(text)
    
        start = max(
            line_start,
            occurrence.start - self.CONTEXT_WINDOW,
        )
    
        end = min(
            line_end,
            occurrence.end + self.CONTEXT_WINDOW,
        )
    
        return text[start:end]

    def _semantic_distance(
        self,
        text: str,
        occurrence: MoneyOccurrence,
        patterns: tuple[str, ...],
    ) -> int | None:
        """
        Return distance from the money occurrence to the nearest semantic phrase.
    
        Semantic matching is restricted to the source line containing the
        monetary occurrence. This prevents adjacent financial statements
        from contaminating each other's classification.
        """
    
        line_start = text.rfind(
            "\n",
            0,
            occurrence.start,
        ) + 1
    
        line_end = text.find(
            "\n",
            occurrence.end,
        )
    
        if line_end == -1:
            line_end = len(text)
    
        context_start = max(
            line_start,
            occurrence.start - self.CONTEXT_WINDOW,
        )
    
        context_end = min(
            line_end,
            occurrence.end + self.CONTEXT_WINDOW,
        )
    
        context = text[context_start:context_end]
    
        best_distance: int | None = None
    
        for pattern in patterns:
            for match in re.finditer(
                pattern,
                context,
                flags=re.IGNORECASE,
            ):
                match_start = context_start + match.start()
                match_end = context_start + match.end()
    
                if match_end <= occurrence.start:
                    distance = occurrence.start - match_end
                elif match_start >= occurrence.end:
                    distance = match_start - occurrence.end
                else:
                    distance = 0
    
                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_distance = distance
    
        return best_distance


    def _money_occurrences(
        self,
        text: str,
    ) -> list[MoneyOccurrence]:
        """Return canonical normalized money occurrences."""
        return MoneyParser.find_all(text)

    def _matches_context(
        self,
        context: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(
                pattern,
                context,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        )


    def _extract_raise_occurrence(
        self,
        text: str,
        occurrences: list[MoneyOccurrence] | None = None,
    ) -> MoneyOccurrence | None:
        """Find the money occurrence most strongly associated with fundraising."""
    
        occurrences = (
            occurrences
            if occurrences is not None
            else self._money_occurrences(text)
        )
    
        candidates: list[tuple[int, int, MoneyOccurrence]] = []
    
        explicit_patterns = (
            r"\bamount\s+(?:being\s+)?raised\b",
            r"\braise\s+amount\b",
            r"\btarget\s+raise\b",
            r"\bfundraising\s+(?:target|amount)\b",
            r"\bamount\s+raising\b",
            r"\bcurrently\s+raising\b",
            r"\braising\b",
            r"\braised\b",
        )
    
        round_patterns = (
            r"\b(?:funding|financing|investment)\s+round\b",
            r"\bround\s+size\b",
        )
    
        for occurrence in occurrences:
            lowered_context = self._occurrence_context(
                text,
                occurrence,
            ).lower()
    
            # Explicit investor-ticket language must never be classified
            # as the company's fundraising amount.
            if (
                "minimum investment" in lowered_context
                or "minimum ticket" in lowered_context
                or "investment size" in lowered_context
            ):
                continue
    
            explicit_distance = self._semantic_distance(
                text,
                occurrence,
                explicit_patterns,
            )
    
            round_distance = self._semantic_distance(
                text,
                occurrence,
                round_patterns,
            )
    
            if explicit_distance is not None:
                # Strongest category.
                candidates.append(
                    (
                        100,
                        explicit_distance,
                        occurrence,
                    )
                )
    
            elif round_distance is not None:
                candidates.append(
                    (
                        50,
                        round_distance,
                        occurrence,
                    )
                )
    
        if not candidates:
            return None
    
        # Higher semantic priority first.
        # For equal priority, nearest semantic phrase wins.
        # For equal distance, source order wins.
        candidates.sort(
            key=lambda item: (
                -item[0],
                item[1],
                item[2].start,
            )
        )
    
        return candidates[0][2]



    def _extract_valuation_occurrence(
        self,
        text: str,
        occurrences: list[MoneyOccurrence] | None = None,
    ) -> tuple[MoneyOccurrence, ValuationType] | None:
        """Find the first money occurrence with valuation context."""

        occurrences = (
            occurrences
            if occurrences is not None
            else self._money_occurrences(text)
        )

        # Prefer explicitly classified valuation forms.
        for valuation_type, pattern in self.VALUATION_CONTEXT_PATTERNS:
            for occurrence in occurrences:
                context = self._line_context(
                    text,
                    occurrence.start,
                    occurrence.end,
                )

                if re.search(
                    pattern,
                    context,
                    flags=re.IGNORECASE,
                ):
                    return occurrence, valuation_type

        return None

    def _extract_ebitda_margin(
        self,
        text: str,
    ) -> tuple[Decimal, int, int] | None:
        """
        Extract an EBITDA margin only when the percentage is explicitly
        associated with EBITDA margin terminology.
        """

        percentage = r"(?P<value>\d+(?:\.\d+)?)\s*%"

        patterns = (
            (
                rf"\bebitda\s+margin\b"
                rf"(?:\s+(?:is|was|of|at|reached|increased\s+to|"
                rf"decreased\s+to))?"
                rf"\s*[:=]?\s*{percentage}"
            ),
            (
                rf"{percentage}"
                rf"\s+\bebitda\s+margin\b"
            ),
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match is None:
                continue

            value = Decimal(match.group("value"))
            value_start = match.start("value")
            value_end = match.end("value")

            if value_end < len(text) and text[value_end] == "%":
                value_end += 1

            return (
                value,
                value_start,
                value_end,
            )

        return None

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> FinancialMetrics:
        text = document.text
        occurrences = self._money_occurrences(text)
        raise_occurrence = self._extract_raise_occurrence(
            text,
            occurrences,
        )
        
        currency: str | None = None
        
        if (
            raise_occurrence is not None
            and raise_occurrence.money.currency
        ):
            currency = raise_occurrence.money.currency


        values: dict[str, Decimal | None] = {
            "revenue": None,
            "ebitda": None,
            "arr": None,
            "burn_rate": None,
        }

        # Generic financial metrics are classified from canonical
        # MoneyOccurrence objects.
        for occurrence in occurrences:
            context = self._line_context(
                text,
                occurrence.start,
                occurrence.end,
            ).lower()
        
            for field_name, keywords in self.METRIC_MAPPING:
                if values[field_name] is not None:
                    continue
        
                if not self._contains(context, keywords):
                    continue
        
                values[field_name] = occurrence.money.amount
        
                if currency is None and occurrence.money.currency:
                    currency = occurrence.money.currency
        
                break

        if (
            currency is None
            and raise_occurrence is not None
            and raise_occurrence.money.currency
        ):
            currency = raise_occurrence.money.currency

        valuation_result = self._extract_valuation_occurrence(
            text,
            occurrences,
        )

        if (
            currency is None
            and valuation_result is not None
            and valuation_result[0].money.currency
        ):
            currency = valuation_result[0].money.currency

        margin_result = self._extract_ebitda_margin(text)
        runway_months = DurationParser.parse_months(text)

        metrics = FinancialMetrics(
            currency=currency,
            raise_amount=(
                raise_occurrence.money.amount
                if raise_occurrence is not None
                else None
            ),
            valuation=(
                valuation_result[0].money.amount
                if valuation_result is not None
                else None
            ),
            valuation_type=(
                valuation_result[1]
                if valuation_result is not None
                else ValuationType.UNSPECIFIED
            ),
            revenue=values["revenue"],
            ebitda=values["ebitda"],
            arr=values["arr"],
            margin=(
                margin_result[0]
                if margin_result is not None
                else None
            ),
            burn_rate=values["burn_rate"],
            runway_months=runway_months,
            confidence=0.0,
        )

        confidence = self._calculate_confidence(metrics)

        return FinancialMetrics(
            currency=metrics.currency,
            raise_amount=metrics.raise_amount,
            valuation=metrics.valuation,
            valuation_type=metrics.valuation_type,
            revenue=metrics.revenue,
            ebitda=metrics.ebitda,
            arr=metrics.arr,
            margin=metrics.margin,
            burn_rate=metrics.burn_rate,
            runway_months=metrics.runway_months,
            confidence=confidence,
        )

    def extract_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        result: FinancialMetrics,
    ) -> tuple[IntelligenceEvidence, ...]:
        """Return source evidence supporting extracted financial metrics."""

        text = document.text
        occurrences = self._money_occurrences(text)
        evidence: list[IntelligenceEvidence] = []

        remaining_fields = {
            field_name
            for field_name, _ in self.METRIC_MAPPING
            if getattr(result, field_name) is not None
        }

        for occurrence in occurrences:
            if not remaining_fields:
                break

            context = self._line_context(
                text,
                occurrence.start,
                occurrence.end,
            ).lower()

            for field_name, keywords in self.METRIC_MAPPING:
                if field_name not in remaining_fields:
                    continue

                if not self._contains(context, keywords):
                    continue

                if getattr(result, field_name) != occurrence.money.amount:
                    continue

                evidence.append(
                    self._money_evidence(
                        document,
                        chunks,
                        occurrence,
                        field_name,
                    )
                )

                remaining_fields.remove(field_name)
                break

        raise_occurrence = self._extract_raise_occurrence(
            text,
            occurrences,
        )

        if (
            result.raise_amount is not None
            and raise_occurrence is not None
            and raise_occurrence.money.amount == result.raise_amount
        ):
            evidence.append(
                self._money_evidence(
                    document,
                    chunks,
                    raise_occurrence,
                    "raise_amount",
                )
            )

        valuation_result = self._extract_valuation_occurrence(
            text,
            occurrences,
        )

        if (
            result.valuation is not None
            and valuation_result is not None
            and valuation_result[0].money.amount == result.valuation
        ):
            occurrence, valuation_type = valuation_result

            evidence.append(
                self._money_evidence(
                    document,
                    chunks,
                    occurrence,
                    "valuation",
                    metadata={
                        "valuation_type": valuation_type.value,
                    },
                )
            )

        if result.margin is not None:
            margin_result = self._extract_ebitda_margin(text)

            if margin_result is not None:
                margin, start, end = margin_result

                if margin == result.margin:
                    chunk = self._find_chunk(
                        chunks,
                        start,
                        end,
                    )

                    evidence.append(
                        IntelligenceEvidence(
                            extractor=self.name,
                            field_name="margin",
                            chunk_index=(
                                chunk.index
                                if chunk is not None
                                else None
                            ),
                            start_offset=start,
                            end_offset=end,
                            text=self._line_context(
                                text,
                                start,
                                end,
                            ),
                        )
                    )

        evidence.sort(
            key=lambda item: item.start_offset or 0
        )

        return tuple(evidence)

    def _money_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        occurrence: MoneyOccurrence,
        field_name: str,
        *,
        metadata: dict | None = None,
    ) -> IntelligenceEvidence:
        """Build evidence directly from a canonical MoneyOccurrence."""

        chunk = self._find_chunk(
            chunks,
            occurrence.start,
            occurrence.end,
        )

        return IntelligenceEvidence(
            extractor=self.name,
            field_name=field_name,
            chunk_index=(
                chunk.index if chunk is not None else None
            ),
            start_offset=occurrence.start,
            end_offset=occurrence.end,
            text=self._line_context(
                document.text,
                occurrence.start,
                occurrence.end,
            ),
            metadata=metadata or {},
        )

    def _find_chunk(
        self,
        chunks: list[Chunk],
        start: int,
        end: int,
    ) -> Chunk | None:
        """Return the chunk containing the source occurrence."""

        for chunk in chunks:
            if (
                chunk.start_offset <= start
                and end <= chunk.end_offset
            ):
                return chunk

        return None

    def _line_context(
        self,
        text: str,
        start: int,
        end: int,
    ) -> str:
        """Return only the source line containing the occurrence."""

        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)

        if line_end == -1:
            line_end = len(text)

        return text[line_start:line_end]

    def _contains(
        self,
        context: str,
        keywords: tuple[str, ...],
    ) -> bool:
        return any(
            keyword in context
            for keyword in keywords
        )

    def _calculate_confidence(
        self,
        metrics: FinancialMetrics,
    ) -> float:
        detected = sum(
            getattr(metrics, field) is not None
            for field, _ in self.METRIC_MAPPING
        )

        if metrics.raise_amount is not None:
            detected += 1

        if metrics.margin is not None:
            detected += 1

        if metrics.runway_months is not None:
            detected += 1

        return min(
            1.0,
            0.25 + detected * 0.10,
        )
