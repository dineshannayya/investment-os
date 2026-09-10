"""Build dimension-scoped evidence from canonical startup evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from app.models.investment_scorecard import InvestmentScorecard
from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceItem,
    DimensionEvidenceSet,
)
from app.schemas.analysis import AnalysisEvidence


# ---------------------------------------------------------------------------
# Routing policy
# ---------------------------------------------------------------------------

FIELD_DIMENSION_ROUTING: Final[Mapping[str, frozenset[str]]] = {
    # Founder / team
    "founder": frozenset({"founder_team"}),
    "founders": frozenset({"founder_team"}),
    "founder_background": frozenset({"founder_team"}),
    "founder_experience": frozenset({"founder_team"}),
    "founder_commitment": frozenset({"founder_team"}),
    "employment": frozenset({"founder_team"}),
    "vesting": frozenset({"founder_team"}),
    "shareholding": frozenset({
        "founder_team",
        "governance_cap_table",
    }),

    # Market
    "market": frozenset({"market_tam"}),
    "market_description": frozenset({"market_tam"}),
    "tam": frozenset({"market_tam"}),
    "sam": frozenset({"market_tam"}),
    "som": frozenset({"market_tam"}),
    "market_growth_rate": frozenset({"market_tam"}),
    "geographic_market": frozenset({"market_tam"}),
    "geography": frozenset({"market_tam"}),
    "geographies": frozenset({"market_tam"}),
    "competitors": frozenset({
        "market_tam",
        "risk_exit_potential",
    }),
    "markets": frozenset({"market_tam"}),

    # Product / PMF
    "product": frozenset({"product_pmf"}),
    "product_description": frozenset({"product_pmf"}),
    "customer_problem": frozenset({"product_pmf"}),
    "solution": frozenset({"product_pmf"}),
    "customer_need": frozenset({"product_pmf"}),

    # Technology / IP
    "technology": frozenset({"technology_ip_moat"}),
    "technologies": frozenset({"technology_ip_moat"}),
    "intellectual_property": frozenset({"technology_ip_moat"}),
    "ip": frozenset({"technology_ip_moat"}),
    "patent": frozenset({"technology_ip_moat"}),
    "architecture": frozenset({"technology_ip_moat"}),
    "proprietary": frozenset({"technology_ip_moat"}),
    "themes": frozenset({"technology_ip_moat"}),

    # Commercial traction
    "revenue": frozenset({
        "commercial_traction",
        "financial_health",
    }),
    "arr": frozenset({
        "commercial_traction",
        "financial_health",
    }),
    "revenue_growth_yoy": frozenset({"commercial_traction"}),
    "customers": frozenset({"commercial_traction"}),
    "paying_customers": frozenset({"commercial_traction"}),
    "active_users": frozenset({"commercial_traction"}),
    "orders": frozenset({"commercial_traction"}),
    "repeat_customer_rate": frozenset({"commercial_traction"}),
    "churn_rate": frozenset({"commercial_traction"}),
    "business_models": frozenset({"commercial_traction"}),

    # Unit economics
    "customer_acquisition_cost": frozenset({
        "commercial_traction",
        "unit_economics_margins",
    }),
    "average_order_value": frozenset({
        "commercial_traction",
        "unit_economics_margins",
    }),
    "ltv": frozenset({"unit_economics_margins"}),
    "ltv_to_cac": frozenset({"unit_economics_margins"}),
    "gross_margin": frozenset({
        "unit_economics_margins",
        "financial_health",
    }),
    "contribution_profit_per_order": frozenset({
        "unit_economics_margins",
    }),

    # Financial health
    "ebitda": frozenset({"financial_health"}),
    "ebitda_margin": frozenset({"financial_health"}),
    "net_profit": frozenset({"financial_health"}),
    "cash": frozenset({"financial_health"}),
    "debt": frozenset({"financial_health"}),
    "burn_rate": frozenset({"financial_health"}),
    "runway_months": frozenset({"financial_health"}),

    # Governance
    "cap_table": frozenset({"governance_cap_table"}),
    "board": frozenset({"governance_cap_table"}),
    "reserved_matters": frozenset({"governance_cap_table"}),
    "investor_rights": frozenset({"governance_cap_table"}),
    "information_rights": frozenset({"governance_cap_table"}),
    "inspection_rights": frozenset({"governance_cap_table"}),
    "esop": frozenset({"governance_cap_table"}),

    # Valuation / deal
    "stage": frozenset({"valuation_deal_terms"}),
    "amount_raising": frozenset({"valuation_deal_terms"}),
    "raise_amount": frozenset({"valuation_deal_terms"}),
    "amount_raised": frozenset({"valuation_deal_terms"}),
    "pre_money_valuation": frozenset({"valuation_deal_terms"}),
    "post_money_valuation": frozenset({"valuation_deal_terms"}),
    "valuation_cap": frozenset({"valuation_deal_terms"}),
    "instrument": frozenset({
        "valuation_deal_terms",
        "governance_cap_table",
    }),
    "ccps": frozenset({
        "valuation_deal_terms",
        "governance_cap_table",
    }),
    "anti_dilution": frozenset({
        "valuation_deal_terms",
        "governance_cap_table",
    }),

    # Risk / exit
    "exit": frozenset({"risk_exit_potential"}),
    "exit_pathway": frozenset({"risk_exit_potential"}),
    "liquidity": frozenset({"risk_exit_potential"}),
    "tag": frozenset({"risk_exit_potential"}),
    "drag": frozenset({"risk_exit_potential"}),
    "competition": frozenset({
        "market_tam",
        "risk_exit_potential",
    }),
}


SECTION_DIMENSION_ROUTING: Final[Mapping[str, frozenset[str]]] = {
    "founder_profile": frozenset({"founder_team"}),
    "founder_background": frozenset({"founder_team"}),
    "management": frozenset({"founder_team"}),

    "market": frozenset({"market_tam"}),
    "market_size": frozenset({"market_tam"}),
    "market_analysis": frozenset({"market_tam"}),
    "geographies": frozenset({"market_tam"}),

    "product": frozenset({"product_pmf"}),
    "product_overview": frozenset({"product_pmf"}),
    "customer_problem": frozenset({"product_pmf"}),

    "technology": frozenset({"technology_ip_moat"}),
    "technology_ip": frozenset({"technology_ip_moat"}),
    "themes": frozenset({"technology_ip_moat"}),

    "traction": frozenset({"commercial_traction"}),
    "sales": frozenset({"commercial_traction"}),
    "customers": frozenset({"commercial_traction"}),
    "business_models": frozenset({"commercial_traction"}),
    "arr": frozenset({
        "commercial_traction",
        "financial_health",
    }),

    "unit_economics": frozenset({"unit_economics_margins"}),
    "margins": frozenset({"unit_economics_margins"}),

    "financials": frozenset({"financial_health"}),
    "financial": frozenset({"financial_health"}),

    "cap_table": frozenset({"governance_cap_table"}),
    "governance": frozenset({"governance_cap_table"}),

    "valuation": frozenset({"valuation_deal_terms"}),
    "deal_terms": frozenset({"valuation_deal_terms"}),
    "fundraising": frozenset({"valuation_deal_terms"}),
    "stage": frozenset({"valuation_deal_terms"}),

    "exit": frozenset({"risk_exit_potential"}),
    "risks": frozenset({"risk_exit_potential"}),
}


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DimensionEvidenceBuildDiagnostics:
    """Diagnostics produced while constructing dimension evidence."""

    total_evidence: int
    routed_evidence: int
    unrouted_evidence: int
    duplicate_evidence: int
    dimension_counts: dict[str, int]
    unrouted_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DimensionEvidenceBuildResult:
    """Builder result including optional diagnostics."""

    evidence_set: DimensionEvidenceSet
    diagnostics: DimensionEvidenceBuildDiagnostics


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class DimensionEvidenceBuilder:
    """
    Deterministically project canonical AnalysisEvidence into scorecard
    dimensions.

    This service:

    - does not call an LLM
    - does not calculate scores
    - does not calculate confidence
    - does not resolve source conflicts
    - does not modify canonical evidence
    - does not invent observations
    """

    DEFAULT_SCHEMA_VERSION: Final[str] = "1.0"

    def __init__(
        self,
        *,
        field_routing: Mapping[str, frozenset[str]] | None = None,
        section_routing: Mapping[str, frozenset[str]] | None = None,
        strict: bool = False,
    ) -> None:
        self._field_routing = (
            field_routing
            if field_routing is not None
            else FIELD_DIMENSION_ROUTING
        )
        self._section_routing = (
            section_routing
            if section_routing is not None
            else SECTION_DIMENSION_ROUTING
        )
        self._strict = strict

    def build(
        self,
        *,
        startup_name: str,
        scorecard: InvestmentScorecard,
        analysis_input: StartupAnalysisInput,
        schema_version: str = DEFAULT_SCHEMA_VERSION,
    ) -> DimensionEvidenceBuildResult:
        """
        Build dimension-scoped evidence from canonical evidence.

        Evidence may be routed to more than one dimension.

        In strict mode, evidence that cannot be routed is rejected.
        """

        evidence = analysis_input.evidence

        if not startup_name.strip():
            raise ValueError("startup_name must not be blank")

        dimension_ids = tuple(
            dimension.id
            for dimension in scorecard.dimensions
        )

        dimension_id_set = set(dimension_ids)

        buckets: dict[
            str,
            list[DimensionEvidenceItem],
        ] = defaultdict(list)

        seen_refs: dict[str, set[str]] = {
            dimension_id: set()
            for dimension_id in dimension_ids
        }

        evidence_list = tuple(evidence)

        total_evidence = len(evidence_list)
        routed_refs: set[str] = set()
        unrouted_refs: list[str] = []
        seen_input_refs: set[str] = set()
        duplicate_count = 0

        for item in evidence_list:
            if item.evidence_ref in seen_input_refs:
                duplicate_count += 1
            else:
                seen_input_refs.add(item.evidence_ref)
        
            routes = self._routes_for(item)

            unknown_routes = routes - dimension_id_set

            if unknown_routes:
                raise ValueError(
                    "Evidence routing references unknown scorecard "
                    f"dimensions: {sorted(unknown_routes)}"
                )

            if not routes:
                unrouted_refs.append(item.evidence_ref)

                if self._strict:
                    print()
                    print("=" * 80)
                    print("UNROUTED EVIDENCE")
                    print("=" * 80)
                    print(f"evidence_ref : {item.evidence_ref}")
                    print(f"field        : {item.field}")
                    print(f"section      : {item.section}")
                    print(f"source_type  : {item.source_type}")
                    print(f"source_name  : {item.source_name}")
                    print(f"document_id  : {item.document_id}")
                    print(f"page         : {item.page}")
                    print(f"source_text  : {item.source_text}")
                    print("=" * 80)
                
                    raise ValueError(
                        "Unable to route evidence_ref "
                        f"{item.evidence_ref!r}"
                    )

                continue

            routed_refs.add(item.evidence_ref)

            observation = self._build_observation(item)

            dimension_item = DimensionEvidenceItem(
                evidence_ref=item.evidence_ref,
                observation=observation,
                source_type=(
                    item.source_type
                    or "unknown"
                ),
            )

            for dimension_id in sorted(routes):
                if item.evidence_ref in seen_refs[dimension_id]:
                    continue

                seen_refs[dimension_id].add(item.evidence_ref)
                buckets[dimension_id].append(dimension_item)

        dimensions = {
            dimension_id: DimensionEvidence(
                evidence=buckets[dimension_id]
            )
            for dimension_id in dimension_ids
        }

        evidence_set = DimensionEvidenceSet(
            schema_version=schema_version,
            startup=startup_name,
            dimensions=dimensions,
        )

        diagnostics = DimensionEvidenceBuildDiagnostics(
            total_evidence=total_evidence,
            routed_evidence=len(routed_refs),
            unrouted_evidence=len(unrouted_refs),
            duplicate_evidence=duplicate_count,
            dimension_counts={
                dimension_id: len(
                    evidence_set.dimensions[dimension_id].evidence
                )
                for dimension_id in dimension_ids
            },
            unrouted_refs=tuple(unrouted_refs),
        )

        return DimensionEvidenceBuildResult(
            evidence_set=evidence_set,
            diagnostics=diagnostics,
        )

    def _routes_for(
        self,
        item: AnalysisEvidence,
    ) -> frozenset[str]:
        """Return dimensions supported by the evidence metadata."""

        routes: set[str] = set()

        field = self._normalize(item.field)
        section = self._normalize(item.section)

        if field:
            routes.update(
                self._field_routing.get(
                    field,
                    frozenset(),
                )
            )

        if section:
            routes.update(
                self._section_routing.get(
                    section,
                    frozenset(),
                )
            )

        return frozenset(routes)

    @staticmethod
    def _build_observation(
        item: AnalysisEvidence,
    ) -> str:
        """
        Construct the Qwen-facing observation without interpretation.

        Prefer canonical source text. The builder must not turn evidence
        into an investment conclusion.
        """

        text = (item.source_text or "").strip()

        if text:
            return text

        field = (item.field or "").strip()

        if field:
            return f"Source evidence for {field}."

        return "Source evidence."

    @staticmethod
    def _normalize(value: str | None) -> str:
        if value is None:
            return ""

        return value.strip().lower().replace(" ", "_")
