"""
Document classification extractor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import DocumentClassification
from app.processors import DocumentContent


@dataclass(frozen=True, slots=True)
class ClassificationRule:
    """
    Rule used to identify a document type.
    """

    document_type: str
    keywords: tuple[str, ...]


class ClassificationExtractor(
    IntelligenceExtractor[DocumentClassification]
):
    """
    Classify investment-related documents.
    """

    RULES = (
        ClassificationRule(
            "pitch_deck",
            (
                "problem",
                "solution",
                "market",
                "traction",
                "business model",
                "go-to-market",
                "competition",
                "team",
                "ask",
            ),
        ),
        ClassificationRule(
            "business_plan",
            (
                "executive summary",
                "marketing strategy",
                "operations",
                "financial projections",
            ),
        ),
        ClassificationRule(
            "financial_model",
            (
                "revenue forecast",
                "cash flow",
                "income statement",
                "balance sheet",
                "ebitda",
            ),
        ),
        ClassificationRule(
            "term_sheet",
            (
                "term sheet",
                "liquidation preference",
                "drag along",
                "tag along",
                "anti dilution",
            ),
        ),
        ClassificationRule(
            "shareholders_agreement",
            (
                "shareholders agreement",
                "sha",
                "board composition",
                "reserved matters",
            ),
        ),
        ClassificationRule(
            "cap_table",
            (
                "cap table",
                "shareholding",
                "equity",
                "ownership",
                "fully diluted",
            ),
        ),
        ClassificationRule(
            "investor_update",
            (
                "monthly update",
                "quarterly update",
                "highlights",
                "key metrics",
            ),
        ),
    )

    @property
    def name(self) -> str:
        return "classification"

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> DocumentClassification:

        text = document.text.lower()

        scores: list[tuple[str, int]] = []

        for rule in self.RULES:

            score = sum(
                keyword in text
                for keyword in rule.keywords
            )

            if score:
                scores.append(
                    (
                        rule.document_type,
                        score,
                    )
                )

        if not scores:
            return DocumentClassification()

        scores.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        primary = scores[0][0]

        secondary = tuple(
            name
            for name, _ in scores[1:]
        )

        confidence = min(
            1.0,
            scores[0][1] / 5.0,
        )

        return DocumentClassification(
            primary_type=primary,
            secondary_types=secondary,
            confidence=confidence,
        )
