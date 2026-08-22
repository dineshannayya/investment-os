"""
Fundraising valuation normalization:

Source intelligence may emit:

    valuation
    valuation_cap

Both represent valuation-cap semantics when the source
evidence identifies the value as a valuation cap.

Canonical StartupAnalysis uses:

    FundraisingAnalysis.valuation_cap

The generic "valuation" alias must not be interpreted as
pre_money_valuation or post_money_valuation.

Transaction-document pre-money valuation remains authoritative
and suppresses valuation_cap according to the existing
transaction-authority rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from app.schemas.analysis import (
    AnalysisEvidence,
    BusinessModelAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
    MarketAnalysis,
    SourceAuthority,
    SourceConflict,
    SourceStatus,
    SourceValue,
    StartupAnalysisInput,
    TractionAnalysis,
)

# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------

_SOURCE_AUTHORITY_PRIORITY: dict[SourceAuthority, int] = {
    SourceAuthority.MIS: 100,
    SourceAuthority.TRANSACTION_DOCUMENT: 95,
    SourceAuthority.FINANCIAL_MODEL: 90,
    SourceAuthority.COMPANY_DOCUMENT: 80,
    SourceAuthority.INVESTOR_SUMMARY: 70,
    SourceAuthority.LLM: 10,
    SourceAuthority.UNKNOWN: 0,
}


# ---------------------------------------------------------------------------
# Qualitative multi-value fields
# ---------------------------------------------------------------------------

# These fields describe multiple potentially complementary characteristics.
# They must NOT be treated like scalar financial facts.
#
# Example:
#   market_description:
#       "B2B food supply"
#       "restaurant procurement"
#
# These are complementary descriptions, not competing claims.
_AGGREGATED_TEXT_FIELDS: frozenset[str] = frozenset(
    {
        "market_description",
        "business_model",
    }
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Candidate:
    """
    Internal representation of one candidate source value.

    This is deliberately kept private. Public callers work with
    SourceValue / SourceConflict.
    """

    value: Any
    source: SourceValue


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SourceIntelligenceReconciliationService:
    """
    Deterministically reconcile source intelligence.

    The service operates on an already normalized StartupAnalysisInput plus
    additional source facts.

    It does not:
      - call an LLM
      - perform investment scoring
      - calculate financial metrics
      - invent missing information
    """

    def _reconcile_business_model(
        self,
        current: BusinessModelAnalysis | None,
        facts: list[SourceValue],
    ) -> BusinessModelAnalysis | None:
        """
        Reconcile qualitative business-model descriptions.
    
        Multiple FACT values are complementary rather than conflicting.
    
        Example:
            B2B
            marketplace
    
        becomes:
            B2B, marketplace
        """
    
        if current is None:
            current = BusinessModelAnalysis()
    
        business_model = self._aggregate_text_values(
            facts,
            "business_model",
        )
    
        if business_model is not None:
            return current.model_copy(
                update={
                    "business_model": business_model,
                }
            )
    
        return current

    def reconcile(
        self,
        analysis_input: StartupAnalysisInput,
        source_facts: Iterable[SourceValue] | None = None,
    ) -> StartupAnalysisInput:
        """
        Reconcile source facts into StartupAnalysisInput.

        Existing source facts on analysis_input are retained and combined
        with source_facts supplied by the caller.
        """

        all_facts = [
            *analysis_input.source_facts,
            *(list(source_facts) if source_facts is not None else []),
        ]

        if not all_facts:
            return analysis_input

        # Deduplicate identical source facts first.
        all_facts = self._deduplicate_facts(all_facts)

        # Detect only material scalar/source conflicts.
        conflicts = self._detect_conflicts(all_facts)

        financials = self._reconcile_financials(
            analysis_input.financials,
            all_facts,
            conflicts,
        )

        fundraising = self._reconcile_fundraising(
            analysis_input.fundraising,
            all_facts,
            conflicts,
        )

        market = self._reconcile_market(
            analysis_input.market,
            all_facts,
        )

        traction = self._reconcile_traction(
            analysis_input.traction,
            all_facts,
            conflicts,
        )

        business_model = self._reconcile_business_model(
            analysis_input.business_model,
            all_facts,
        )

        return analysis_input.model_copy(
            update={
                "financials": financials,
                "fundraising": fundraising,
                "market": market,
                "traction": traction,
                "business_model": business_model,
                "source_facts": all_facts,
                "source_conflicts": conflicts,
            }
        )

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_facts(
        facts: list[SourceValue],
    ) -> list[SourceValue]:
        """
        Remove exact duplicate source facts.

        Two facts are considered duplicates when their source identity,
        field, period, status and value are identical.
        """

        result: list[SourceValue] = []
        seen: set[tuple[Any, ...]] = set()

        for fact in facts:
            key = (
                fact.field,
                fact.value,
                fact.status,
                fact.source_document_id,
                fact.source_name,
                fact.source_authority,
                fact.period,
                fact.section,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(fact)

        return result

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def _detect_conflicts(
        self,
        facts: list[SourceValue],
    ) -> list[SourceConflict]:
        """
        Detect material disagreement among source facts.

        Important:
        - FACT vs FACT with different scalar values => conflict.
        - FACT vs PROJECTION => not a conflict.
        - FACT vs ASSUMPTION => not a conflict.
        - DERIVED values are not reconciled here.
        - Qualitative multi-value fields are aggregated rather than
          treated as scalar conflicts.
        """

        grouped: dict[str, list[SourceValue]] = {}

        for fact in facts:
            if fact.status in {
                SourceStatus.PROJECTION,
                SourceStatus.ASSUMPTION,
                SourceStatus.DERIVED,
                SourceStatus.UNKNOWN,
            }:
                continue

            # Qualitative fields can legitimately contain multiple
            # complementary values.
            if fact.field in _AGGREGATED_TEXT_FIELDS:
                continue

            grouped.setdefault(fact.field, []).append(fact)

        conflicts: list[SourceConflict] = []

        for field, candidates in grouped.items():
            if len(candidates) < 2:
                continue

            material = self._material_candidates(candidates)

            if len(material) < 2:
                continue

            if not self._has_distinct_values(material):
                continue

            conflicts.append(
                SourceConflict(
                    field=field,
                    status=SourceStatus.CONFLICT,
                    values=material,
                    resolution=None,
                    requires_diligence=True,
                )
            )

        return conflicts

    @staticmethod
    def _material_candidates(
        candidates: list[SourceValue],
    ) -> list[SourceValue]:
        """
        Keep source facts that can legitimately compete with each other.

        Projection/assumption/derived values have already been excluded.
        """

        return [
            candidate
            for candidate in candidates
            if candidate.status == SourceStatus.FACT
        ]

    @staticmethod
    def _has_distinct_values(
        candidates: list[SourceValue],
    ) -> bool:
        values: list[Any] = []

        for candidate in candidates:
            if not any(
                SourceIntelligenceReconciliationService._values_equal(
                    candidate.value,
                    existing,
                )
                for existing in values
            ):
                values.append(candidate.value)

        return len(values) > 1

    @staticmethod
    def _values_equal(left: Any, right: Any) -> bool:
        """
        Compare source values conservatively.

        Decimal and numeric values are compared numerically.
        Everything else uses normal equality.
        """

        if isinstance(left, Decimal) or isinstance(right, Decimal):
            try:
                return Decimal(str(left)) == Decimal(str(right))
            except Exception:
                return left == right

        return left == right

    # ------------------------------------------------------------------
    # Candidate selection
    # ------------------------------------------------------------------

    @staticmethod
    def _candidates(
        facts: list[SourceValue],
        field: str,
        *,
        period: str | None = None,
    ) -> list[SourceValue]:
        result = [
            fact
            for fact in facts
            if fact.field == field
            and fact.status == SourceStatus.FACT
        ]

        if period is not None:
            result = [
                fact
                for fact in result
                if fact.period == period
            ]

        return result

    @staticmethod
    def _preferred_candidate(
        candidates: list[SourceValue],
    ) -> SourceValue | None:
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda candidate: (
                _SOURCE_AUTHORITY_PRIORITY.get(
                    candidate.source_authority,
                    0,
                ),
                candidate.confidence
                if candidate.confidence is not None
                else Decimal("0"),
            ),
        )

    def _resolved_value(
        self,
        facts: list[SourceValue],
        field: str,
        conflicts: list[SourceConflict],
        *,
        period: str | None = None,
    ) -> Any:
        """
        Return a canonical value only when reconciliation is safe.

        If a material conflict exists, return None.
        """

        if any(
            conflict.field == field
            for conflict in conflicts
        ):
            return None

        candidate = self._preferred_candidate(
            self._candidates(
                facts,
                field,
                period=period,
            )
        )

        return candidate.value if candidate is not None else None

    # ------------------------------------------------------------------
    # Qualitative aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_text_values(
        facts: list[SourceValue],
        field: str,
    ) -> str | None:
        """
        Aggregate complementary qualitative FACT values.

        Values are:
        - restricted to FACTs
        - stripped
        - deduplicated case-insensitively
        - returned in deterministic source order

        Example:
            B2B
            b2b
            marketplace

        becomes:

            B2B, marketplace
        """

        aggregated: list[str] = []
        seen: set[str] = set()

        for fact in facts:
            if fact.field != field:
                continue

            if fact.status != SourceStatus.FACT:
                continue

            if fact.value is None:
                continue

            value = str(fact.value).strip()

            if not value:
                continue

            normalized = value.casefold()

            if normalized in seen:
                continue

            seen.add(normalized)
            aggregated.append(value)

        if not aggregated:
            return None

        return ", ".join(aggregated)

    # ------------------------------------------------------------------
    # Financials
    # ------------------------------------------------------------------

    def _reconcile_financials(
        self,
        current: FinancialAnalysis | None,
        facts: list[SourceValue],
        conflicts: list[SourceConflict],
    ) -> FinancialAnalysis | None:
        if current is None:
            current = FinancialAnalysis()

        updates: dict[str, Any] = {}

        # Current actual financials only.
        for field in (
            "revenue",
            "gross_sales",
            "gross_profit",
            "gross_margin",
            "ebitda",
            "ebitda_margin",
            "net_profit",
            "cash",
            "debt",
            "burn_rate",
            "runway_months",
            "contribution_profit_per_order",
        ):
            value = self._resolved_value(
                facts,
                field,
                conflicts,
            )

            if value is not None:
                updates[field] = value

        if updates:
            return current.model_copy(update=updates)

        return current

    # ------------------------------------------------------------------
    # Fundraising
    # ------------------------------------------------------------------

    def _reconcile_fundraising(
        self,
        current: FundraisingAnalysis | None,
        facts: list[SourceValue],
        conflicts: list[SourceConflict],
    ) -> FundraisingAnalysis | None:
        if current is None:
            current = FundraisingAnalysis()

        updates: dict[str, Any] = {}

        # Canonical schema field is amount_raising.
        #
        # Source intelligence may emit "raise_amount". Normalize it here
        # rather than adding a duplicate field to FundraisingAnalysis.
        amount_raising = self._resolved_fundraising_value(
            facts,
            canonical_field="amount_raising",
            aliases=("raise_amount",),
            conflicts=conflicts,
        )

        if amount_raising is not None:
            updates["amount_raising"] = amount_raising

        for field in (
            "amount_raised",
            "pre_money_valuation",
            "post_money_valuation",
            "valuation_cap",
            "instrument",
            "investor_commitments",
        ):
            value = self._resolved_value(
                facts,
                field,
                conflicts,
            )
        
            if value is not None:
                updates[field] = value
        
        # Source intelligence may emit the generic field "valuation".
        # For valuation-cap evidence, normalize it into the canonical
        # fundraising field "valuation_cap".
        valuation_cap = self._resolved_fundraising_value(
            facts,
            canonical_field="valuation_cap",
            aliases=("valuation",),
            conflicts=conflicts,
        )
        
        if valuation_cap is not None:
            updates["valuation_cap"] = valuation_cap


        # Transaction documents are authoritative for valuation type.
        # If pre-money valuation is present, do not populate valuation_cap
        # merely because an older summary used that terminology.
        if self._has_transaction_document_fact(
            facts,
            "pre_money_valuation",
        ):
            updates["valuation_cap"] = None

        if updates:
            return current.model_copy(update=updates)

        return current

    def _resolved_fundraising_value(
        self,
        facts: list[SourceValue],
        *,
        canonical_field: str,
        aliases: tuple[str, ...],
        conflicts: list[SourceConflict],
    ) -> Any:
        """
        Resolve a canonical fundraising field from canonical and legacy/
        producer aliases.

        This is deliberately explicit instead of renaming SourceValue fields
        globally. Source intelligence producers can use "raise_amount",
        while the public StartupAnalysis schema remains "amount_raising".
        """

        fields = (canonical_field, *aliases)

        # If any representation has a scalar conflict, do not silently
        # select another representation.
        if any(
            conflict.field in fields
            for conflict in conflicts
        ):
            return None

        candidates: list[SourceValue] = []

        for field in fields:
            candidates.extend(
                self._candidates(
                    facts,
                    field,
                )
            )

        candidate = self._preferred_candidate(candidates)

        return candidate.value if candidate is not None else None

    # ------------------------------------------------------------------
    # Market
    # ------------------------------------------------------------------

    def _reconcile_market(
        self,
        current: MarketAnalysis | None,
        facts: list[SourceValue],
    ) -> MarketAnalysis | None:
        if current is None:
            current = MarketAnalysis()

        updates: dict[str, Any] = {}

        # Market description is qualitative and multi-valued.
        market_description = self._aggregate_text_values(
            facts,
            "market_description",
        )

        if market_description is not None:
            updates["market_description"] = market_description

        # These remain scalar fields and therefore use authority preference.
        for field in (
            "tam",
            "sam",
            "som",
            "market_growth_rate",
            "geographic_market",
        ):
            candidates = self._candidates(
                facts,
                field,
            )

            candidate = self._preferred_candidate(candidates)

            if candidate is not None:
                updates[field] = candidate.value

        # Competitors are inherently multi-valued.
        competitor_facts = [
            fact
            for fact in facts
            if fact.field == "competitor"
            and fact.status == SourceStatus.FACT
        ]

        if competitor_facts:
            competitors: list[str] = []
            seen: set[str] = set()

            for fact in competitor_facts:
                if fact.value is None:
                    continue

                value = str(fact.value).strip()

                if not value:
                    continue

                normalized = value.casefold()

                if normalized in seen:
                    continue

                seen.add(normalized)
                competitors.append(value)

            updates["competitors"] = competitors

        if updates:
            return current.model_copy(update=updates)

        return current

    # ------------------------------------------------------------------
    # Traction
    # ------------------------------------------------------------------

    def _reconcile_traction(
        self,
        current: TractionAnalysis | None,
        facts: list[SourceValue],
        conflicts: list[SourceConflict],
    ) -> TractionAnalysis | None:
        if current is None:
            current = TractionAnalysis()

        updates: dict[str, Any] = {}

        for field in (
            "revenue",
            "revenue_growth_yoy",
            "customers",
            "paying_customers",
            "active_users",
            "repeat_customer_rate",
            "orders",
            "churn_rate",
            "customer_acquisition_cost",
            "average_order_value",
            "top_customer_concentration",
        ):
            value = self._resolved_value(
                facts,
                field,
                conflicts,
            )

            if value is not None:
                updates[field] = value

        if updates:
            return current.model_copy(update=updates)

        return current

    # ------------------------------------------------------------------
    # Transaction authority
    # ------------------------------------------------------------------

    @staticmethod
    def _has_transaction_document_fact(
        facts: list[SourceValue],
        field: str,
    ) -> bool:
        return any(
            fact.field == field
            and fact.status == SourceStatus.FACT
            and fact.source_authority
            == SourceAuthority.TRANSACTION_DOCUMENT
            for fact in facts
        )
