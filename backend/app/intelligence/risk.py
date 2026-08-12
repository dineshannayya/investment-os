"""
Investment risk extractor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import RiskAssessment
from app.processors import DocumentContent


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
        ),
    ),
    RiskRule(
        field="market_risks",
        value="customer_concentration",
        severity="high",
        keywords=(
            "single customer",
            "major customer",
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
            "unproven",
        ),
    ),
    RiskRule(
        field="technology_risks",
        value="manufacturing_dependency",
        severity="high",
        keywords=(
            "foundry",
            "fabrication",
            "manufacturing partner",
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
        ),
    ),
    RiskRule(
        field="legal_risks",
        value="regulatory_approval",
        severity="high",
        keywords=(
            "regulatory approval",
            "fda",
            "cdsco",
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
                keyword in text
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
