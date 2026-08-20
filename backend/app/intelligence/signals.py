"""
Investment signal extractor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import InvestmentSignals
from app.processors import DocumentContent
import re


@dataclass(slots=True, frozen=True)
class SignalRule:
    """
    Rule used to identify an investment signal.
    """

    field: str

    value: str

    keywords: tuple[str, ...]


class SignalExtractor(
    IntelligenceExtractor[InvestmentSignals],
):
    """
    Extract investment signals from documents.
    """

    RULES = (
        #
        # Stage
        #
        SignalRule(
            field="stage",
            value="idea",
            keywords=(
                "idea stage",
                "concept stage",
                "prototype",
            ),
        ),
        SignalRule(
            field="stage",
            value="pre_seed",
            keywords=(
                "pre-seed",
                "pre seed",
            ),
        ),
        SignalRule(
            field="stage",
            value="seed",
            keywords=(
                "seed round",
                "seed funding",
            ),
        ),
        SignalRule(
            field="stage",
            value="series_a",
            keywords=(
                "series a",
            ),
        ),

        #
        # Industry
        #
        SignalRule(
            field="industry",
            value="healthcare",
            keywords=(
                "healthcare",
                "hospital",
                "clinic",
                "patient",
                "medical",
                "diagnostic",
            ),
        ),
        SignalRule(
            field="industry",
            value="semiconductor",
            keywords=(
                "semiconductor",
                "soc",
                "asic",
                "chip",
                "risc-v",
                "silicon",
                "fabless",
                "integrated circuit",
                "microcontroller",
                "microprocessor",
            ),
        ),
        SignalRule(
            field="industry",
            value="fintech",
            keywords=(
                "fintech",
                "payment",
                "bank",
                "upi",
            ),
        ),

        #
        # Business model
        #
        SignalRule(
            field="business_models",
            value="saas",
            keywords=(
                "subscription",
                "saas",
                "annual recurring revenue",
            ),
        ),
        SignalRule(
            field="business_models",
            value="marketplace",
            keywords=(
                "marketplace",
                "buyer",
                "seller",
            ),
        ),
        SignalRule(
            field="business_models",
            value="hardware",
            keywords=(
                "hardware",
                "hardware product",
                "hardware platform",
                "embedded hardware",
                "embedded system",
                "semiconductor product",
            )
        ),
        SignalRule(
            field="business_models",
            value="b2b",
            keywords=(
                "enterprise",
                "business customers",
                "b2b",
            ),
        ),
        SignalRule(
            field="business_models",
            value="b2c",
            keywords=(
                "consumer",
                "end users",
                "b2c",
            ),
        ),

        #
        # Technology
        #
        SignalRule(
            field="technologies",
            value="ai",
            keywords=(
                "artificial intelligence",
                "machine learning",
                "generative ai",
                "llm",
                "ai",
                "edge ai",
                "ai inference",
                "edge inference",
                "neural network",
                "deep learning",
            ),
        ),
        SignalRule(
            field="technologies",
            value="computer_vision",
            keywords=(
                "computer vision",
                "vision model",
                "vision ai",
                "ai vision",
                "video analytics",
                "image processing",
                "visual inference",
                "video intelligence",
            ),
        ),
        SignalRule(
            field="technologies",
            value="iot",
            keywords=(
                "iot",
                "internet of things",
            ),
        ),

        #
        # Geography
        #
        SignalRule(
            field="geographies",
            value="india",
            keywords=(
                "india",
                "bangalore",
                "bengaluru",
            ),
        ),
        SignalRule(
            field="geographies",
            value="usa",
            keywords=(
                "usa",
                "united states",
                "california",
            ),
        ),

        #
        # Market
        #
        SignalRule(
            field="markets",
            value="enterprise",
            keywords=(
                "enterprise",
            ),
        ),
        SignalRule(
            field="markets",
            value="consumer",
            keywords=(
                "consumer",
            ),
        ),
        SignalRule(
            field="markets",
            value="surveillance",
            keywords=(
                "surveillance",
                "video surveillance",
                "security camera",
                "security cameras",
                "cctv",
            ),
        ),

        #
        # Themes
        #
        SignalRule(
            field="themes",
            value="deeptech",
            keywords=(
                "deep tech",
                "deeptech",
            ),
        ),
        SignalRule(
            field="themes",
            value="ai",
            keywords=(
                "artificial intelligence",
                "generative ai",
                "llm",
            ),
        ),
        SignalRule(
            field="themes",
            value="edge_ai",
            keywords=(
                "edge ai",
                "edge inference",
                "on-device ai",
                "on device ai",
            ),
        ),
        SignalRule(
            field="themes",
            value="surveillance",
            keywords=(
                "surveillance",
                "video surveillance",
                "security camera",
                "cctv",
            ),
        ),
    )

    @property
    def name(self) -> str:
        return "signals"

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
        return re.search(pattern, text) is not None


    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> InvestmentSignals:

        text = document.text.lower()

        values = {
            "stage": None,
            "industry": set(),
            "business_models": set(),
            "technologies": set(),
            "markets": set(),
            "geographies": set(),
            "themes": set(),
        }

        for rule in self.RULES:

            if not any(
                self._contains_keyword(text, keyword)
                for keyword in rule.keywords
            ):
                continue

            if rule.field == "stage":

                if values["stage"] is None:
                    values["stage"] = rule.value

            else:

                values[rule.field].add(
                    rule.value
                )

        signals = InvestmentSignals(
            stage=values["stage"],
            industry=tuple(
                sorted(values["industry"])
            ),
            business_models=tuple(
                sorted(values["business_models"])
            ),
            technologies=tuple(
                sorted(values["technologies"])
            ),
            markets=tuple(
                sorted(values["markets"])
            ),
            geographies=tuple(
                sorted(values["geographies"])
            ),
            themes=tuple(
                sorted(values["themes"])
            ),
            confidence=0.0,
        )

        return InvestmentSignals(
            stage=signals.stage,
            industry=signals.industry,
            business_models=signals.business_models,
            technologies=signals.technologies,
            markets=signals.markets,
            geographies=signals.geographies,
            themes=signals.themes,
            confidence=self._confidence(
                signals,
            ),
        )

    def _confidence(
        self,
        signals: InvestmentSignals,
    ) -> float:

        score = 0

        if signals.stage:
            score += 1

        score += len(signals.industry)
        score += len(signals.business_models)
        score += len(signals.technologies)
        score += len(signals.markets)
        score += len(signals.geographies)
        score += len(signals.themes)

        return min(
            1.0,
            0.25 + score * 0.08,
        )
