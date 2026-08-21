"""
Investment signal extractor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    IntelligenceEvidence,
    InvestmentSignals,
)
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
    def _find_keyword(
        text: str,
        keyword: str,
    ) -> re.Match[str] | None:
        """Return the first source match for a signal keyword."""
    
        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
        return re.search(pattern, text)

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        return (
            SignalExtractor._find_keyword(
                text,
                keyword,
            )
            is not None
        )

    @staticmethod
    def _contains_negated_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        """Return True when a keyword occurrence is explicitly negated."""
        match = SignalExtractor._find_keyword(text, keyword)

        if match is None:
            return False

        before = text[
            max(0, match.start() - 80):match.start()
        ].lower()

        patterns = (
            r"\bnot\s+(?:a\s+|an\s+)?$",
            r"\bnot\s+(?:primarily\s+)?$",
            r"\brather\s+than\s+(?:a\s+|an\s+)?$",
            r"\binstead\s+of\s+(?:a\s+|an\s+)?$",
            r"\bversus\s+(?:a\s+|an\s+)?$",
            r"\bvs\.?\s+(?:a\s+|an\s+)?$",
            r"\bnot\s+the\s+$",
        )

        return any(
            re.search(pattern, before)
            for pattern in patterns
        )

    @classmethod
    def _rule_matches(
        cls,
        text: str,
        rule: SignalRule,
    ) -> bool:
        """Match a rule with contextual protection for B2C/consumer."""
        for keyword in rule.keywords:
            if not cls._contains_keyword(text, keyword):
                continue

            if (
                rule.value in {"b2c", "consumer"}
                and cls._contains_negated_keyword(
                    text,
                    keyword,
                )
            ):
                continue

            return True

        return False


    @staticmethod
    def _find_chunk(
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

            if not self._rule_matches(text, rule):
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

    def extract_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        result: InvestmentSignals,
    ) -> tuple[IntelligenceEvidence, ...]:
        """Return source evidence supporting extracted investment signals."""
    
        text = document.text.lower()
        evidence: list[IntelligenceEvidence] = []
    
        for rule in self.RULES:
            # Only produce evidence for signals that actually
            # exist in the extracted result.
            if rule.field == "stage":
                if result.stage != rule.value:
                    continue
    
            else:
                values = getattr(result, rule.field)
    
                if rule.value not in values:
                    continue
    
            match = None
   
            for keyword in rule.keywords:
                match = self._find_keyword(
                    text,
                    keyword,
                )

                if match is None:
                    continue

                if (
                    rule.value in {"b2c", "consumer"}
                    and self._contains_negated_keyword(
                        text,
                        keyword,
                    )
                ):
                    match = None
                    continue

                break 
    
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
                    field_name=rule.field,
                    chunk_index=(
                        chunk.index
                        if chunk is not None
                        else None
                    ),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    text=self._line_context(
                        document.text,
                        match.start(),
                        match.end(),
                    ),
                )
            )
    
        return tuple(evidence)


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
