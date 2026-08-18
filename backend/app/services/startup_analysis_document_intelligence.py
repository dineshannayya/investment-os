"""
Document intelligence enrichment for Startup Analysis.

This service bridges the document-processing/intelligence pipeline
into StartupAnalysisInput.

Responsibilities
----------------
- Process startup documents.
- Chunk processed documents.
- Run InvestmentIntelligenceService.
- Aggregate document intelligence.
- Map supported intelligence fields into StartupAnalysisInput.

Non-responsibilities
--------------------
- Startup normalization.
- Financial metric calculation.
- LLM invocation.
- Evidence provenance resolution.
- Persistence.

Evidence remains untouched in 3.7.6.3.C.4.
Evidence population is handled by the dedicated provenance milestone.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.intelligence.models import (
    FinancialMetrics as IntelligenceFinancialMetrics,
    InvestmentEntities,
    InvestmentProfile,
    InvestmentSignals,
)
from app.models.startup import Startup
from app.schemas.analysis import (
    BusinessModelAnalysis,
    FinancialAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupAnalysisInput,
    TractionAnalysis,
)
from app.services.document_processing import DocumentProcessingService
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)


class StartupAnalysisDocumentIntelligenceService:
    """
    Enrich StartupAnalysisInput with document-derived intelligence.
    """

    def __init__(
        self,
        *,
        document_processing: DocumentProcessingService,
        intelligence: InvestmentIntelligenceService,
    ) -> None:
        self._document_processing = document_processing
        self._intelligence = intelligence

    def enrich(
        self,
        startup: Startup,
        analysis_input: StartupAnalysisInput,
    ) -> StartupAnalysisInput:
        """
        Enrich analysis input from all startup documents.

        If the startup has no documents, the original input is returned
        unchanged.
        """

        documents = tuple(startup.documents or [])

        if not documents:
            return analysis_input

        profiles = tuple(
            self._analyze_document(document.id)
            for document in documents
        )

        return self._merge_profiles(
            analysis_input,
            profiles,
        )

    def _analyze_document(self, document_id):
        """Process, chunk, and analyze one stored document."""

        content, chunks = (
            self._document_processing.process_and_chunk(
                document_id,
            )
        )

        return self._intelligence.analyze(
            content,
            chunks,
        )

    @classmethod
    def _merge_profiles(
        cls,
        analysis_input: StartupAnalysisInput,
        profiles: tuple[InvestmentProfile, ...],
    ) -> StartupAnalysisInput:
        """Merge document profiles into the analysis input."""

        product = cls._build_product(profiles)
        market = cls._build_market(profiles)
        traction = cls._build_traction(profiles)
        financials = cls._build_financials(profiles)
        business_model = cls._build_business_model(profiles)

        return StartupAnalysisInput(
            startup_id=analysis_input.startup_id,
            company=analysis_input.company,
            founders=analysis_input.founders,
            product=product or analysis_input.product,
            market=market or analysis_input.market,
            traction=traction or analysis_input.traction,
            financials=financials or analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=(
                business_model
                or analysis_input.business_model
            ),
            # Evidence is intentionally preserved.
            # 3.7.6.3.C.4 does not create evidence.
            evidence=list(analysis_input.evidence),
        )

    @classmethod
    def _build_product(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> ProductAnalysis | None:
        """Build product information from extracted entities."""

        products = cls._unique_strings(
            value
            for profile in profiles
            for value in profile.entities.products
        )

        technologies = cls._unique_strings(
            value
            for profile in profiles
            for value in profile.entities.technologies
        )

        if not products and not technologies:
            return None

        return ProductAnalysis(
            product_description=(
                ", ".join(products)
                if products
                else None
            ),
            technology=(
                ", ".join(technologies)
                if technologies
                else None
            ),
        )

    @classmethod
    def _build_market(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> MarketAnalysis | None:
        """Build market information from extracted signals."""

        markets = cls._unique_strings(
            value
            for profile in profiles
            for value in profile.signals.markets
        )

        geographies = cls._unique_strings(
            value
            for profile in profiles
            for value in profile.signals.geographies
        )

        if not markets and not geographies:
            return None

        return MarketAnalysis(
            market_description=(
                ", ".join(markets)
                if markets
                else None
            ),
            geographic_market=(
                ", ".join(geographies)
                if geographies
                else None
            ),
        )

    @classmethod
    def _build_traction(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> TractionAnalysis | None:
        """
        Build traction information from directly extracted revenue.

        No customer/user figures are fabricated because the current
        intelligence model does not provide them.
        """

        revenue = cls._first_non_none(
            profile.financials.revenue
            for profile in profiles
        )

        if revenue is None:
            return None

        return TractionAnalysis(
            revenue=revenue,
        )

    @classmethod
    def _build_financials(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> FinancialAnalysis | None:
        """Build financial analysis from extracted financial facts."""

        revenue = cls._first_non_none(
            profile.financials.revenue
            for profile in profiles
        )

        ebitda = cls._first_non_none(
            profile.financials.ebitda
            for profile in profiles
        )

        margin = cls._first_non_none(
            profile.financials.margin
            for profile in profiles
        )

        burn_rate = cls._first_non_none(
            profile.financials.burn_rate
            for profile in profiles
        )

        runway_months = cls._first_non_none(
            profile.financials.runway_months
            for profile in profiles
        )

        if all(
            value is None
            for value in (
                revenue,
                ebitda,
                margin,
                burn_rate,
                runway_months,
            )
        ):
            return None

        return FinancialAnalysis(
            revenue=revenue,
            ebitda=ebitda,
            ebitda_margin=margin,
            burn_rate=burn_rate,
            runway_months=runway_months,
        )

    @classmethod
    def _build_business_model(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> BusinessModelAnalysis | None:
        """Build business-model information from extracted signals."""

        business_models = cls._unique_strings(
            value
            for profile in profiles
            for value in profile.signals.business_models
        )

        if not business_models:
            return None

        return BusinessModelAnalysis(
            business_model=", ".join(business_models),
        )

    @staticmethod
    def _first_non_none(values):
        """Return the first non-None value."""
        for value in values:
            if value is not None:
                return value

        return None

    @staticmethod
    def _unique_strings(values) -> tuple[str, ...]:
        """Return non-empty strings while preserving order."""

        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            if not value:
                continue

            normalized = str(value).strip()

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

        return tuple(result)


__all__ = [
    "StartupAnalysisDocumentIntelligenceService",
]
