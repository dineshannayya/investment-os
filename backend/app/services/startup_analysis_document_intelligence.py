"""Document intelligence enrichment for Startup Analysis."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal

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
    AnalysisEvidence,
)

from app.services.document_processing import DocumentProcessingService
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)


class StartupAnalysisDocumentIntelligenceService:
    """
    Enrich StartupAnalysisInput with document-derived intelligence.

    ``profile_observer`` is an optional diagnostic hook. It is intentionally
    disabled by default and does not alter production behaviour. It exists so
    the real E2E path can inspect the exact InvestmentProfile produced by the
    intelligence layer before profile-to-analysis-input mapping occurs.
    """

    def __init__(
        self,
        *,
        document_processing: DocumentProcessingService,
        intelligence: InvestmentIntelligenceService,
        profile_observer: Callable[[InvestmentProfile], None] | None = None,
    ) -> None:
        self._document_processing = document_processing
        self._intelligence = intelligence
        self._profile_observer = profile_observer

    def enrich(
        self,
        startup: Startup,
        analysis_input: StartupAnalysisInput,
    ) -> StartupAnalysisInput:
        """Enrich analysis input from all startup documents."""
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

    @staticmethod
    def _build_evidence(
        profiles: Iterable[InvestmentProfile],
    ) -> list[AnalysisEvidence]:
        evidence: list[AnalysisEvidence] = []
    
        for profile in profiles:
            for item in profile.evidence:
                evidence.append(
                    AnalysisEvidence(
                        document_id=profile.document_id,
                        page=item.metadata.get("page"),
                        section=(
                            item.metadata.get("section")
                            or item.field_name
                        ),
                        source_text=item.text,
                        confidence=Decimal(str(profile.confidence)),
                    )
                )
    
        return evidence


    def _analyze_document(self, document_id):
        """Process, chunk, and analyze one stored document."""
        content, chunks = (
            self._document_processing.process_and_chunk(
                document_id,
            )
        )

        profile = self._intelligence.analyze(
            content,
            chunks,
        )

        if self._profile_observer is not None:
            self._profile_observer(profile)

        return profile

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
        evidence = cls._build_evidence(profiles)

        return StartupAnalysisInput(
            startup_id=analysis_input.startup_id,
            company=analysis_input.company,
            founders=analysis_input.founders,
            product=product or analysis_input.product,
            market=market or analysis_input.market,
            traction=traction or analysis_input.traction,
            financials=financials or analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=business_model or analysis_input.business_model,
            evidence=[
                *analysis_input.evidence,
                *evidence,
            ],

        )

    @classmethod
    def _build_product(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> ProductAnalysis | None:
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
            product_description=(", ".join(products) if products else None),
            technology=(", ".join(technologies) if technologies else None),
        )

    @classmethod
    def _build_market(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> MarketAnalysis | None:
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
            market_description=(", ".join(markets) if markets else None),
            geographic_market=(
                ", ".join(geographies) if geographies else None
            ),
        )

    @classmethod
    def _build_traction(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> TractionAnalysis | None:
        revenue = cls._first_non_none(
            profile.financials.revenue
            for profile in profiles
        )

        if revenue is None:
            return None

        return TractionAnalysis(revenue=revenue)

    @classmethod
    def _build_financials(
        cls,
        profiles: Iterable[InvestmentProfile],
    ) -> FinancialAnalysis | None:
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
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _unique_strings(values) -> tuple[str, ...]:
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
