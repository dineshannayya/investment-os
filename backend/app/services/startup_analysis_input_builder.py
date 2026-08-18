"""Build normalized startup-analysis input from persisted startup data."""

from __future__ import annotations

from enum import Enum

from app.models.founder import Founder
from app.models.opportunity import Opportunity
from app.models.startup import Startup
from app.schemas.analysis import (
    CompanyAnalysis,
    FounderAnalysis,
    FundraisingAnalysis,
    StartupAnalysisInput,
)


class StartupAnalysisInputBuilder:
    """Build :class:`StartupAnalysisInput` from the startup aggregate.

    The builder is intentionally limited to normalization. It does not:

    * calculate financial metrics,
    * extract facts from documents,
    * call an LLM, or
    * persist analysis results.

    Fields that are not represented by the current persistence model remain
    ``None`` rather than being inferred or fabricated.

    Opportunity handling:
    * only OPEN opportunities are considered current fundraising rounds;
    * zero OPEN opportunities results in ``fundraising=None``;
    * exactly one OPEN opportunity is normalized;
    * multiple OPEN opportunities are treated as an explicit ambiguity.
    """

    def build(self, startup: Startup) -> StartupAnalysisInput:
        """Build normalized analysis input for ``startup``."""
        return StartupAnalysisInput(
            startup_id=startup.id,
            company=self._build_company(startup),
            founders=[
                self._build_founder(founder)
                for founder in (startup.founders or [])
            ],
            fundraising=self._build_fundraising(
                startup.opportunities or []
            ),
            # Product, market, traction, financial, business model,
            # and evidence require dedicated source data. They are
            # intentionally left unset until those sources are integrated.
        )

    @staticmethod
    def _build_company(startup: Startup) -> CompanyAnalysis:
        """Map persisted company fields to the analysis contract."""
        return CompanyAnalysis(
            name=startup.name,
            description=startup.description,
            industry=startup.industry,
            sector=startup.sector,
            stage=StartupAnalysisInputBuilder._enum_value(startup.stage),
            founded_year=startup.founded_year,
            headquarters=startup.headquarters,
        )

    @staticmethod
    def _build_founder(founder: Founder) -> FounderAnalysis:
        """Map persisted founder fields to the analysis contract.

        ``FounderAnalysis`` intentionally does not expose private contact
        information such as email, phone, or LinkedIn URL. Those fields are
        therefore not copied into the analysis input.
        """
        relevant_experience = StartupAnalysisInputBuilder._build_experience(
            founder
        )

        return FounderAnalysis(
            founder_id=founder.id,
            name=founder.full_name,
            role=StartupAnalysisInputBuilder._enum_value(founder.designation),
            background=founder.education,
            relevant_experience=relevant_experience,
            # The current Founder model has no explicit counts for these.
            previous_startups=None,
            previous_exits=None,
            analysis_notes=founder.notes,
        )

    @staticmethod
    def _build_fundraising(
        opportunities: list[Opportunity],
    ) -> FundraisingAnalysis | None:
        """Normalize the current OPEN fundraising opportunity.

        The Startup model may contain multiple historical opportunities,
        while ``StartupAnalysisInput`` currently accepts only one
        ``FundraisingAnalysis``.

        Selection policy:
        * no OPEN opportunity -> ``None``
        * one OPEN opportunity -> use it
        * multiple OPEN opportunities -> raise ``ValueError`` rather than
          silently selecting an arbitrary fundraising round.
        """
        open_opportunities = [
            opportunity
            for opportunity in opportunities
            if StartupAnalysisInputBuilder._enum_value(
                opportunity.status
            ) == "OPEN"
        ]

        if not open_opportunities:
            return None

        if len(open_opportunities) > 1:
            raise ValueError(
                "Startup has multiple OPEN fundraising opportunities; "
                "cannot determine the current fundraising round "
                "unambiguously."
            )

        opportunity = open_opportunities[0]

        return FundraisingAnalysis(
            current_round=opportunity.round_name,
            amount_raising=opportunity.target_raise,
            # committed_amount represents commitments, not necessarily
            # capital already raised. Therefore it must not be mapped to
            # amount_raised.
            amount_raised=None,
            pre_money_valuation=opportunity.pre_money_valuation,
            post_money_valuation=opportunity.post_money_valuation,
            valuation_cap=opportunity.valuation_cap,
            instrument=StartupAnalysisInputBuilder._enum_value(
                opportunity.instrument
            ),
            investor_commitments=opportunity.committed_amount,
        )

    @staticmethod
    def _build_experience(founder: Founder) -> str | None:
        """Normalize the available founder experience fields into text."""
        parts: list[str] = []

        if founder.experience_years is not None:
            parts.append(f"{founder.experience_years} years experience")

        if founder.previous_companies:
            parts.append(
                f"Previous companies: {founder.previous_companies}"
            )

        if not parts:
            return None

        return "; ".join(parts)

    @staticmethod
    def _enum_value(value: object) -> str | None:
        """Return an enum's value while accepting plain strings in tests."""
        if value is None:
            return None

        if isinstance(value, Enum):
            return str(value.value)

        return str(value)


__all__ = ["StartupAnalysisInputBuilder"]
