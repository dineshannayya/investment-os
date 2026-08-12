"""
Financial intelligence extractor.
"""

from __future__ import annotations

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import FinancialMetrics
from app.intelligence.parsers import (
    DurationParser,
    MoneyParser,
    PercentageParser,
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
            "arr": None,
            "burn_rate": None,
        }
    
        #
        # Money metrics
        #
        for occurrence in MoneyParser.find_all(text):
    
            context = self._context(
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
        margin = PercentageParser.parse(text)
    
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
            arr=metrics.arr,
            burn_rate=metrics.burn_rate,
            margin=metrics.margin,
            runway_months=metrics.runway_months,
            confidence=confidence,
        )    

    # ==============================================================
    # Helpers
    # ==============================================================

    def _context(
        self,
        text: str,
        start: int,
        end: int,
    ) -> str:

        begin = max(
            0,
            start - self.CONTEXT_WINDOW,
        )

        finish = min(
            len(text),
            end + self.CONTEXT_WINDOW,
        )

        return text[begin:finish]

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
