"""
Financial intelligence extractor.
"""

from __future__ import annotations

import re
from decimal import Decimal
from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    FinancialMetrics,
    IntelligenceEvidence,
)
from app.intelligence.parsers import (
    DurationParser,
    MoneyParser
)
from app.processors import DocumentContent


class FinancialExtractor(
    IntelligenceExtractor[FinancialMetrics]
):
    """
    Extract structured financial metrics from investment documents.
    """

    CONTEXT_WINDOW = 40

    #
    # field_name, keywords
    #
    METRIC_MAPPING = (
        (
            "raise_amount",
            (
                "raise",
                "raised",
                "funding",
                "fundraise",
                "investment",
                "round",
            ),
        ),
        (
            "valuation",
            (
                "valuation",
                "valued",
                "post-money",
                "pre-money",
            ),
        ),
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


    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> FinancialMetrics:
    
        text = document.text
    
        #
        # Temporary values
        #
        values = {
            "currency": None,
            "raise_amount": None,
            "valuation": None,
            "revenue": None,
            "ebitda": None,
            "arr": None,
            "burn_rate": None,
        }
    
        #
        # Money metrics
        #
        for occurrence in MoneyParser.find_all(text):
    
            context = self._line_context(
                text,
                occurrence.start,
                occurrence.end,
            ).lower()
    
            for field_name, keywords in self.METRIC_MAPPING:
    
                #
                # already populated
                #
                if values[field_name] is not None:
                    continue
    
                if not self._contains(
                    context,
                    keywords,
                ):
                    continue
    
                values[field_name] = (
                    occurrence.money.amount
                )
    
                if (
                    values["currency"] is None
                    and occurrence.money.currency
                ):
                    values["currency"] = (
                        occurrence.money.currency
                    )
    
                break
    
        #
        # Other metrics
        #
        margin_result = self._extract_ebitda_margin(text)

        margin = (
            margin_result[0]
            if margin_result is not None
            else None
        )
    
        runway_months = (
            DurationParser.parse_months(text)
        )
        #
        # Build immutable model
        #
        metrics = FinancialMetrics(
            currency=values["currency"],
            raise_amount=values["raise_amount"],
            valuation=values["valuation"],
            revenue=values["revenue"],
            ebitda=values["ebitda"],
            arr=values["arr"],
            burn_rate=values["burn_rate"],
            margin=margin,
            runway_months=runway_months,
            confidence=0.0,
        )

        confidence = self._calculate_confidence(
            metrics
        )

        #
        # Return final immutable object
        #
        return FinancialMetrics(
            currency=metrics.currency,
            raise_amount=metrics.raise_amount,
            valuation=metrics.valuation,
            revenue=metrics.revenue,
            ebitda=metrics.ebitda,
            arr=metrics.arr,
            burn_rate=metrics.burn_rate,
            margin=metrics.margin,
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
        evidence: list[IntelligenceEvidence] = []
    
        # Map populated metrics to the corresponding source occurrence.
        remaining_fields = {
            field_name
            for field_name, _ in self.METRIC_MAPPING
            if getattr(result, field_name) is not None
        }
    
        for occurrence in MoneyParser.find_all(text):
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
    
                chunk = self._find_chunk(
                    chunks,
                    occurrence.start,
                    occurrence.end,
                )
    
                evidence.append(
                    IntelligenceEvidence(
                        extractor=self.name,
                        field_name=field_name,
                        chunk_index=(
                            chunk.index if chunk is not None else None
                        ),
                        start_offset=occurrence.start,
                        end_offset=occurrence.end,
                        text=self._line_context(
                            text,
                            occurrence.start,
                            occurrence.end,
                        ),
                    )
                )
    
                remaining_fields.remove(field_name)
                break

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
    
        return tuple(evidence)


    # ==============================================================
    # Helpers
    # ==============================================================

    def _extract_ebitda_margin(
        self,
        text: str,
    ) -> tuple[Decimal, int, int] | None:
        """
        Extract an EBITDA margin only when the percentage is explicitly
        associated with EBITDA margin terminology.

        Returns:
            (margin, start_offset, end_offset)
            or None when no supported EBITDA-margin expression exists.
        """

        percentage = r"(?P<value>\d+(?:\.\d+)?)\s*%"

        patterns = (
            # EBITDA margin: 32.5%
            rf"\bebitda\s+margin\b"
            rf"(?:\s+(?:is|was|of|at|reached|increased\s+to|"
            rf"decreased\s+to))?"
            rf"\s*[:=]?\s*{percentage}",

            # 32.5% EBITDA margin
            rf"{percentage}"
            rf"\s+\bebitda\s+margin\b",
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

            # Include the % sign in the evidence span.
            if value_end < len(text) and text[value_end] == "%":
                value_end += 1

            return (
                value,
                value_start,
                value_end,
            )

        return None

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
        """Return only the source line containing the monetary occurrence."""
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

        if metrics.margin is not None:
            detected += 1

        if metrics.runway_months is not None:
            detected += 1

        return min(
            1.0,
            0.25 + detected * 0.10,
        )
