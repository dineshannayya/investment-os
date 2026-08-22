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
    AnalysisEvidence,
    BusinessModelAnalysis,
    FinancialAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    SourceAuthority,
    SourceStatus,
    SourceValue,
    StartupAnalysisInput,
    TractionAnalysis,
)

from app.services.document_processing import DocumentProcessingService
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)

from app.services.source_intelligence_reconciliation import (
    SourceIntelligenceReconciliationService,
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
        reconciliation: SourceIntelligenceReconciliationService,
        profile_observer: Callable[[InvestmentProfile], None] | None = None,
        source_facts_observer: (
            Callable[[list[SourceValue]], None] | None
        ) = None,
    ) -> None:
        self._document_processing = document_processing
        self._intelligence = intelligence
        self._reconciliation = reconciliation
        self._profile_observer = profile_observer
        self._source_facts_observer = source_facts_observer


    @staticmethod
    def _apply_reconciled_traction(
        analysis_input: StartupAnalysisInput,
    ) -> StartupAnalysisInput:
        if analysis_input.traction is not None:
            return analysis_input
    
        revenue = (
            analysis_input.financials.revenue
            if analysis_input.financials is not None
            else None
        )
    
        if revenue is None:
            return analysis_input
    
        return analysis_input.model_copy(
            update={
                "traction": TractionAnalysis(
                    revenue=revenue,
                )
            }
        )


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

        enriched = self._merge_profiles(
            analysis_input,
            profiles,
        )
        
        source_facts = self._build_source_facts(
            profiles,
        )

        if self._source_facts_observer is not None:
            self._source_facts_observer(source_facts)

        
        reconciled = self._reconciliation.reconcile(
            enriched,
            source_facts,
        )
        
        return self._apply_reconciled_traction(
            reconciled,
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
        """Merge non-conflicting document intelligence."""
    
        product = cls._build_product(profiles)
        market = cls._build_market(profiles)
        traction = cls._build_traction(profiles)
        business_model = cls._build_business_model(profiles)
        evidence = cls._build_evidence(profiles)
    
        return analysis_input.model_copy(
            update={
                "product": product or analysis_input.product,
                "market": market or analysis_input.market,
                "traction": traction or analysis_input.traction,
                "business_model": (
                    business_model
                    or analysis_input.business_model
                ),
                "evidence": [
                    *analysis_input.evidence,
                    *evidence,
                ],
            }
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
        return None

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
    def _build_signal_source_facts(
        profile: InvestmentProfile,
    ) -> list[SourceValue]:
        facts: list[SourceValue] = []
    
        authority = (
            StartupAnalysisDocumentIntelligenceService
            ._source_authority(profile)
        )
    
        common = {
            "status": SourceStatus.FACT,
            "source_document_id": profile.document_id,
            "source_name": profile.metadata.title,
            "source_authority": authority,
            "confidence": Decimal(str(profile.confidence)),
        }
    
        for market in profile.signals.markets:
            facts.append(
                SourceValue(
                    field="market_description",
                    value=market,
                    **common,
                )
            )
    
        for geography in profile.signals.geographies:
            facts.append(
                SourceValue(
                    field="geographic_market",
                    value=geography,
                    **common,
                )
            )
    
        for business_model in profile.signals.business_models:
            facts.append(
                SourceValue(
                    field="business_model",
                    value=business_model,
                    **common,
                )
            )
    
        return facts


    @staticmethod
    def _build_source_facts(
        profiles: Iterable[InvestmentProfile],
    ) -> list[SourceValue]:
        facts: list[SourceValue] = []
    
        for profile in profiles:
            facts.extend(
                StartupAnalysisDocumentIntelligenceService
                ._build_financial_source_facts(profile)
            )
    
            facts.extend(
                StartupAnalysisDocumentIntelligenceService
                ._build_signal_source_facts(profile)
            )
    
        return facts

    @staticmethod
    def _build_financial_source_facts(
        profile: InvestmentProfile,
    ) -> list[SourceValue]:
        financials = profile.financials
    
        facts: list[SourceValue] = []
    
        values = (
            ("revenue", financials.revenue),
            ("ebitda", financials.ebitda),
            ("ebitda_margin", financials.margin),
            ("burn_rate", financials.burn_rate),
            ("runway_months", financials.runway_months),
            ("raise_amount", financials.raise_amount),
            ("valuation", financials.valuation),
        )

    
        for field, value in values:
            if value is None:
                continue
    
            facts.append(
                SourceValue(
                    field=field,
                    value=value,
                    status=SourceStatus.FACT,
                    source_document_id=profile.document_id,
                    source_name=profile.metadata.title,
                    source_authority=(
                        StartupAnalysisDocumentIntelligenceService
                        ._source_authority(profile)
                    ),
                    confidence=Decimal(
                        str(profile.confidence)
                    ),
                )
            )
    
        return facts


    @staticmethod
    def _source_authority(
        profile: InvestmentProfile,
    ) -> SourceAuthority:
        document_type = (
            profile.metadata.document_type or ""
        ).lower()
    
        title = profile.metadata.title.lower()
    
        if (
            "mis" in document_type
            or "mis" in title
            or "financial" in document_type
            and "model" not in document_type
        ):
            return SourceAuthority.MIS
    
        if any(
            token in document_type
            for token in (
                "transaction",
                "term_sheet",
                "investment_note",
            )
        ):
            return SourceAuthority.TRANSACTION_DOCUMENT
    
        if (
            "projection" in document_type
            or "financial_model" in document_type
            or "model" in document_type
        ):
            return SourceAuthority.FINANCIAL_MODEL
    
        if "investor" in title:
            return SourceAuthority.INVESTOR_SUMMARY
    
        return SourceAuthority.COMPANY_DOCUMENT


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
