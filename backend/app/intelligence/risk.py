"""
Investment risk extractor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import (
    IntelligenceEvidence,
    RiskAssessment,
)
from app.processors import DocumentContent
import re



@dataclass(slots=True, frozen=True)
class RiskRule:
    """
    Rule used to identify an investment risk.
    """

    field: str
    value: str
    severity: str
    keywords: tuple[str, ...]


#
# --------------------------------------------------------------------
# Founder Risks
# --------------------------------------------------------------------
#

FOUNDER_RULES = (
    RiskRule(
        field="founder_risks",
        value="solo_founder",
        severity="high",
        keywords=(
            "solo founder",
            "single founder",
            "founder dependency",
            "founder concentration",
            "key person dependency",
            "key-person dependency",
        ),
    ),
    RiskRule(
        field="founder_risks",
        value="first_time_founder",
        severity="high",
        keywords=(
            "first time founder",
            "first-time founder",
        ),
    ),
)

#
# --------------------------------------------------------------------
# Financial Risks
# --------------------------------------------------------------------
#

FINANCIAL_RULES = (
    RiskRule(
        field="financial_risks",
        value="high_burn",
        severity="high",
        keywords=(
            "high burn rate",
            "burn rate is high",
            "elevated burn",
            "high burn",
            "burn rate",
        ),
    ),
    RiskRule(
        field="financial_risks",
        value="low_runway",
        severity="high",
        keywords=(
            "runway 6 months",
            "less than 6 months runway",
            "less than six months runway",
            "runway is less than 6 months",
            "limited runway",
            "low runway",
        ),
    ),
    RiskRule(
        field="financial_risks",
        value="pre_revenue",
        severity="medium",
        keywords=(
            "pre revenue",
            "pre-revenue",
            "no revenue",
        ),
    ),
)

#
# --------------------------------------------------------------------
# Execution Risks
# --------------------------------------------------------------------
#

EXECUTION_RULES = (
    RiskRule(
        field="execution_risks",
        value="prototype_stage",
        severity="high",
        keywords=(
            "prototype",
            "proof of concept",
            "poc",
        ),
    ),
    RiskRule(
        field="execution_risks",
        value="hiring_dependency",
        severity="medium",
        keywords=(
            "key hires",
            "hiring plan",
            "critical hires",
            "hiring dependency",
            "dependent on hiring",
        ),
    ),
)

#
# --------------------------------------------------------------------
# Market Risks
# --------------------------------------------------------------------
#

MARKET_RULES = (
    RiskRule(
        field="market_risks",
        value="high_competition",
        severity="high",
        keywords=(
            "competitive market",
            "strong competition",
            "highly competitive market",
            "intense competition",
            "significant competition",
        ),
    ),
    RiskRule(
        field="market_risks",
        value="customer_concentration",
        severity="high",
        keywords=(
            "single customer",
            "single-customer dependency",
            "customer concentration",
            "high customer concentration",
            "revenue depends on a single customer",
            "revenue concentrated in one customer",
            "revenue is highly concentrated in one customer",
            "revenue is concentrated in one major customer",
        ),
    ),
)

#
# --------------------------------------------------------------------
# Technology Risks
# --------------------------------------------------------------------
#

TECHNOLOGY_RULES = (
    RiskRule(
        field="technology_risks",
        value="unproven_technology",
        severity="high",
        keywords=(
            "experimental",
            "experimental technology",
            "unproven",
            "unproven technology",
            "technology not yet validated",
            "not yet validated",
            "still validating its technology",
        ),
    ),
    RiskRule(
        field="technology_risks",
        value="manufacturing_dependency",
        severity="high",
        keywords=(
            "single foundry",
            "single-source foundry",
            "single foundry dependency",
            "manufacturing dependency",
            "manufacturing partner",
            "depends on a single foundry",
            "dependent on a single foundry",
            "depends on a manufacturing partner",
            "dependent on a manufacturing partner",
        ),
    ),
)

#
# --------------------------------------------------------------------
# Legal Risks
# --------------------------------------------------------------------
#

LEGAL_RULES = (
    RiskRule(
        field="legal_risks",
        value="patent_pending",
        severity="high",
        keywords=(
            "patent pending",
            "patents pending",
        ),
    ),
    RiskRule(
        field="legal_risks",
        value="regulatory_approval",
        severity="high",
        keywords=(
            "fda",
            "cdsco",
            "regulatory approval",
            "regulatory approval required",
            "regulatory clearance",
            "regulatory approval pending",
        ),
    ),
)


class RiskExtractor(
    IntelligenceExtractor[RiskAssessment],
):
    """
    Extract investment risks from documents.
    """

    RULES = (
        *FOUNDER_RULES,
        *FINANCIAL_RULES,
        *EXECUTION_RULES,
        *MARKET_RULES,
        *TECHNOLOGY_RULES,
        *LEGAL_RULES,
    )

    @staticmethod
    def _find_keyword(
        text: str,
        keyword: str,
    ) -> re.Match[str] | None:
        """Return the first source occurrence of a risk keyword."""
    
        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
        return re.search(pattern, text)

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        return (
            RiskExtractor._find_keyword(
                text,
                keyword,
            )
            is not None
        )


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
    
    def extract_evidence(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
        result: RiskAssessment,
    ) -> tuple[IntelligenceEvidence, ...]:
        """Return source evidence supporting extracted investment risks."""
    
        text = document.text.lower()
        evidence: list[IntelligenceEvidence] = []
    
        for rule in self.RULES:
            values = getattr(result, rule.field)
    
            if rule.value not in values:
                continue
    
            match = None
    
            for keyword in rule.keywords:
                match = self._find_keyword(
                    text,
                    keyword,
                )
    
                if match is not None:
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
    
    
    @property
    def name(self) -> str:
        return "risks"

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> RiskAssessment:

        text = document.text.lower()

        values = {
            "founder_risks": set(),
            "financial_risks": set(),
            "execution_risks": set(),
            "market_risks": set(),
            "technology_risks": set(),
            "legal_risks": set(),
        }

        for rule in self.RULES:

            if any(
                self._contains_keyword(text, keyword)
                for keyword in rule.keywords
            ):
                values[rule.field].add(rule.value)


        risks = RiskAssessment(
            founder_risks=tuple(
                sorted(values["founder_risks"])
            ),
            financial_risks=tuple(
                sorted(values["financial_risks"])
            ),
            execution_risks=tuple(
                sorted(values["execution_risks"])
            ),
            market_risks=tuple(
                sorted(values["market_risks"])
            ),
            technology_risks=tuple(
                sorted(values["technology_risks"])
            ),
            legal_risks=tuple(
                sorted(values["legal_risks"])
            ),
            confidence=0.0,
        )

        return RiskAssessment(
            founder_risks=risks.founder_risks,
            financial_risks=risks.financial_risks,
            execution_risks=risks.execution_risks,
            market_risks=risks.market_risks,
            technology_risks=risks.technology_risks,
            legal_risks=risks.legal_risks,
            confidence=self._confidence(risks),
        )

    def _confidence(
        self,
        risks: RiskAssessment,
    ) -> float:

        score = (
            len(risks.founder_risks)
            + len(risks.financial_risks)
            + len(risks.execution_risks)
            + len(risks.market_risks)
            + len(risks.technology_risks)
            + len(risks.legal_risks)
        )

        return min(
            1.0,
            0.25 + score * 0.08,
        )
