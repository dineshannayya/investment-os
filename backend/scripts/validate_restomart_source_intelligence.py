"""
C.7.7.4 — RestoMart Real Source Intelligence Validation.

Read-only diagnostic script for validating the real:

    documents
        -> InvestmentProfile
        -> SourceValue[]
        -> reconciliation
        -> StartupAnalysisInput

This script intentionally does NOT:
    - persist anything to the database
    - run the startup-analysis LLM
    - modify startup/document records

It reports:
    1. Startup/document inventory
    2. InvestmentProfile extraction per document
    3. SourceValue generation
    4. Reconciled StartupAnalysisInput
    5. Source conflicts
    6. Field-level validation classification
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database.session import create_session
from app.models.document import Document
from app.models.startup import Startup
from app.schemas.analysis import SourceStatus, SourceValue
from app.services.source_intelligence_reconciliation import (
    SourceIntelligenceReconciliationService,
)
from app.services.startup_analysis_document_intelligence import (
    StartupAnalysisDocumentIntelligenceService,
)


DEFAULT_STARTUP_ID = "dbb520d7-0979-4db3-8464-523f5710455f"

# ============================================================================
# Formatting / serialization helpers
# ============================================================================


def _to_serializable(value: Any) -> Any:
    """
    Convert the heterogeneous intelligence-domain objects into
    JSON-serializable structures.

    The intelligence layer currently contains both Pydantic models
    and ordinary domain/model classes. The validation script must
    inspect both without imposing a new serialization contract on
    production models.
    """

    if value is None:
        return None

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump(
            mode="json"
        )

    if hasattr(value, "dict"):
        return value.dict()

    if isinstance(value, dict):
        return {
            key: _to_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _to_serializable(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        return {
            key: _to_serializable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def _json_default(value: Any) -> Any:
    return _to_serializable(value)


def _dump(value: Any) -> str:
    return json.dumps(
        _to_serializable(value),
        indent=2,
        ensure_ascii=False,
        default=_json_default,
    )


def _section(title: str) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def _subsection(title: str) -> None:
    print()
    print(title)
    print("-" * 88)


def _value(value: Any) -> str:
    if value is None:
        return "NULL"

    if isinstance(value, Decimal):
        return str(value)

    return str(value)




# ============================================================================
# Database loading
# ============================================================================


def _load_startup(
    db,
    startup_id: UUID,
) -> Startup:
    startup = db.execute(
        select(Startup).where(
            Startup.id == startup_id
        )
    ).scalar_one_or_none()

    if startup is None:
        raise RuntimeError(
            f"Startup not found: {startup_id}"
        )

    return startup


def _load_documents(
    db,
    startup_id: UUID,
) -> list[Document]:
    result = db.execute(
        select(Document)
        .where(
            Document.startup_id == startup_id
        )
        .order_by(
            Document.created_at,
            Document.id,
        )
    )

    return list(result.scalars().all())

# ============================================================================
# InvestmentProfile inspection
# ============================================================================


def _profile_summary(
    profile: Any,
) -> dict[str, Any]:
    financials = getattr(
        profile,
        "financials",
        None,
    )

    signals = getattr(
        profile,
        "signals",
        None,
    )

    entities = getattr(
        profile,
        "entities",
        None,
    )

    return {
        "document_id": str(
            profile.document_id
        ),
        "metadata": _to_serializable(
            getattr(
                profile,
                "metadata",
                None,
            )
        ),
        "entities": _to_serializable(
            entities
        ),
        "signals": _to_serializable(
            signals
        ),
        "financials": _to_serializable(
            financials
        ),
        "evidence_count": len(
            getattr(
                profile,
                "evidence",
                [],
            )
            or []
        ),
    }


def _profile_source_facts(
    profile: Any,
) -> list[SourceValue]:
    """
    Convert one InvestmentProfile into the exact SourceValue
    representation currently used by production document intelligence.
    """
    return (
        StartupAnalysisDocumentIntelligenceService
        ._build_source_facts(
            (profile,)
        )
    )

# ============================================================================
# SourceValue inspection
# ============================================================================

def _print_source_values(
    source_values: list[SourceValue],
) -> None:
    if not source_values:
        print("No source values generated.")
        return

    for index, source in enumerate(
        source_values,
        start=1,
    ):
        print()
        print(f"[{index}] {source.field}")

        print(
            f"    value             : "
            f"{_value(source.value)}"
        )

        print(
            f"    status            : "
            f"{_value(source.status)}"
        )

        print(
            f"    source_document  : "
            f"{_value(source.source_document_id)}"
        )

        print(
            f"    source_name      : "
            f"{_value(source.source_name)}"
        )

        print(
            f"    source_authority : "
            f"{_value(source.source_authority)}"
        )

        print(
            f"    confidence       : "
            f"{_value(source.confidence)}"
        )

        print(
            f"    period           : "
            f"{_value(source.period)}"
        )


# ============================================================================
# Empty canonical input
# ============================================================================


def _empty_startup_input(
    startup: Startup,
) -> Any:
    """
    Build the minimum valid StartupAnalysisInput required by
    SourceIntelligenceReconciliationService.

    This is intentionally NOT the production StartupAnalysisInputBuilder.

    C.7.7.4 is testing the source-intelligence reconciliation boundary
    in isolation from the rest of startup analysis.
    """

    from app.schemas.analysis import (
        BusinessModelAnalysis,
        CompanyAnalysis,
        FinancialAnalysis,
        FundraisingAnalysis,
        MarketAnalysis,
        StartupAnalysisInput,
        TractionAnalysis,
    )

    return StartupAnalysisInput(
        startup_id=startup.id,

        company=CompanyAnalysis(
            name=startup.name,
            description=getattr(
                startup,
                "description",
                None,
            ),
            industry=getattr(
                startup,
                "industry",
                None,
            ),
            sector=getattr(
                startup,
                "sector",
                None,
            ),
            stage=getattr(
                startup,
                "stage",
                None,
            ),
            founded_year=getattr(
                startup,
                "founded_year",
                None,
            ),
            headquarters=getattr(
                startup,
                "headquarters",
                None,
            ),
        ),

        founders=[],

        product=None,

        market=MarketAnalysis(),

        traction=TractionAnalysis(),

        financials=FinancialAnalysis(),

        fundraising=FundraisingAnalysis(),

        business_model=BusinessModelAnalysis(),

        evidence=[],

        source_facts=[],

        source_conflicts=[],
    )


# ============================================================================
# Field validation
# ============================================================================


IMPORTANT_FIELDS = (
    # Financial
    "revenue",
    "gross_profit",
    "gross_margin",
    "ebitda",
    "ebitda_margin",
    "net_profit",
    "cash",
    "debt",
    "burn_rate",
    "runway_months",

    # Fundraise / valuation
    "raise_amount",
    "amount_raising",
    "amount_raised",
    "pre_money_valuation",
    "post_money_valuation",
    "valuation",

    # Market
    "market_description",
    "tam",
    "sam",
    "som",
    "market_growth_rate",
    "geographic_market",

    # Business model
    "business_model",
    "pricing_model",
    "revenue_streams",
)


def _field_sources(
    source_values: list[SourceValue],
) -> dict[str, list[SourceValue]]:
    grouped: dict[
        str,
        list[SourceValue],
    ] = defaultdict(list)

    for source in source_values:
        grouped[source.field].append(
            source
        )

    return grouped


def _has_actual_fact(
    values: list[SourceValue],
) -> bool:
    return any(
        value.status == SourceStatus.FACT
        and value.value is not None
        for value in values
    )


def _has_projection_only(
    values: list[SourceValue],
) -> bool:
    meaningful = [
        value
        for value in values
        if value.value is not None
    ]

    if not meaningful:
        return False

    return all(
        value.status
        == SourceStatus.PROJECTION
        for value in meaningful
    )


def _has_derived_only(
    values: list[SourceValue],
) -> bool:
    meaningful = [
        value
        for value in values
        if value.value is not None
    ]

    if not meaningful:
        return False

    return all(
        value.status
        == SourceStatus.DERIVED
        for value in meaningful
    )


def _has_conflict(
    field: str,
    conflicts: list[Any],
) -> bool:
    return any(
        conflict.field == field
        for conflict in conflicts
    )


def _classify_field(
    field: str,
    values: list[SourceValue],
    conflicts: list[Any],
) -> str:
    if _has_conflict(
        field,
        conflicts,
    ):
        return "CONFLICT"

    if _has_actual_fact(values):
        return "POPULATED"

    if _has_projection_only(values):
        return "PROJECTED_ONLY"

    if _has_derived_only(values):
        return "DERIVED_ONLY"

    if values:
        return "UNSUPPORTED"

    return "MISSING"


# ============================================================================
# Canonical field access
# ============================================================================


def _reconciled_field_value(
    reconciled: Any,
    field: str,
) -> Any:
    """
    Resolve the canonical value from StartupAnalysisInput.

    Explicit mappings are used intentionally so this diagnostic report
    remains auditable and doesn't depend on broad reflection.
    """

    locations = {
        # Financial
        "revenue": (
            "financials",
            "revenue",
        ),
        "gross_profit": (
            "financials",
            "gross_profit",
        ),
        "gross_margin": (
            "financials",
            "gross_margin",
        ),
        "ebitda": (
            "financials",
            "ebitda",
        ),
        "ebitda_margin": (
            "financials",
            "ebitda_margin",
        ),
        "net_profit": (
            "financials",
            "net_profit",
        ),
        "cash": (
            "financials",
            "cash",
        ),
        "debt": (
            "financials",
            "debt",
        ),
        "burn_rate": (
            "financials",
            "burn_rate",
        ),
        "runway_months": (
            "financials",
            "runway_months",
        ),

        # Fundraise
        "raise_amount": (
            "fundraising",
            "raise_amount",
        ),
        "amount_raising": (
            "fundraising",
            "amount_raising",
        ),
        "amount_raised": (
            "fundraising",
            "amount_raised",
        ),
        "pre_money_valuation": (
            "fundraising",
            "pre_money_valuation",
        ),
        "post_money_valuation": (
            "fundraising",
            "post_money_valuation",
        ),
        "valuation": (
            "fundraising",
            "valuation",
        ),

        # Market
        "market_description": (
            "market",
            "market_description",
        ),
        "tam": (
            "market",
            "tam",
        ),
        "sam": (
            "market",
            "sam",
        ),
        "som": (
            "market",
            "som",
        ),
        "market_growth_rate": (
            "market",
            "market_growth_rate",
        ),
        "geographic_market": (
            "market",
            "geographic_market",
        ),

        # Business model
        "business_model": (
            "business_model",
            "business_model",
        ),
        "pricing_model": (
            "business_model",
            "pricing_model",
        ),
        "revenue_streams": (
            "business_model",
            "revenue_streams",
        ),
    }

    location = locations.get(
        field
    )

    if location is None:
        return None

    parent_name, attribute = location

    parent = getattr(
        reconciled,
        parent_name,
        None,
    )

    if parent is None:
        return None

    return getattr(
        parent,
        attribute,
        None,
    )


def _print_validation_matrix(
    source_values: list[SourceValue],
    reconciled: Any,
    conflicts: list[Any],
) -> None:
    grouped = _field_sources(
        source_values
    )

    _section(
        "FIELD VALIDATION MATRIX"
    )

    print(
        f"{'FIELD':30} "
        f"{'CLASSIFICATION':18} "
        f"{'SOURCES':8} "
        f"{'RECONCILED VALUE'}"
    )

    print("-" * 88)

    for field in IMPORTANT_FIELDS:
        values = grouped.get(
            field,
            [],
        )

        classification = _classify_field(
            field,
            values,
            conflicts,
        )

        canonical_value = (
            _reconciled_field_value(
                reconciled,
                field,
            )
        )

        print(
            f"{field:30} "
            f"{classification:18} "
            f"{len(values):8} "
            f"{_value(canonical_value)}"
        )


# ============================================================================
# Main validation
# ============================================================================


def validate(
    startup_id: UUID,
) -> int:
    db = create_session()

    try:
        startup = _load_startup(
            db,
            startup_id,
        )

        documents = _load_documents(
            db,
            startup_id,
        )

        _section(
            "C.7.7.4 — RESTOMART REAL SOURCE "
            "INTELLIGENCE VALIDATION"
        )

        # ------------------------------------------------------------------
        # Startup
        # ------------------------------------------------------------------

        _subsection(
            "STARTUP"
        )

        print(
            f"startup_id : {startup.id}"
        )

        print(
            f"name       : {startup.name}"
        )

        # ------------------------------------------------------------------
        # Document inventory
        # ------------------------------------------------------------------

        _subsection(
            "DOCUMENT INVENTORY"
        )

        print(
            f"document_count : {len(documents)}"
        )

        for index, document in enumerate(
            documents,
            start=1,
        ):
            print()
            print(
                f"[{index}]"
            )

            print(
                f"    id          : "
                f"{document.id}"
            )

            print(
                f"    title       : "
                f"{getattr(document, 'title', None)}"
            )

            print(
                f"    type        : "
                f"{getattr(document, 'document_type', None)}"
            )

            print(
                f"    status      : "
                f"{getattr(document, 'status', None)}"
            )

        # ------------------------------------------------------------------
        # Production dependency graph
        # ------------------------------------------------------------------

        from app.chunking.text import TextChunker
        from app.core.config.settings import settings
        from app.intelligence.factory import (
            create_intelligence_factory,
        )
        from app.processors.factory import (
            create_processor_factory,
        )
        from app.services.document import (
            DocumentService,
        )
        from app.services.document_processing import (
            DocumentProcessingService,
        )
        from app.services.investment_intelligence import (
            InvestmentIntelligenceService,
        )
        from app.storage.local import (
            LocalStorageProvider,
        )
        from app.storage.service import (
            StorageService,
        )

        documents_service = (
            DocumentService(db)
        )

        storage = StorageService(
            LocalStorageProvider(
                settings.storage_root,
            )
        )

        processing = (
            DocumentProcessingService(
                documents=documents_service,
                storage=storage,
                processors=(
                    create_processor_factory()
                ),
                chunker=TextChunker(),
            )
        )

        intelligence = (
            InvestmentIntelligenceService(
                factory=(
                    create_intelligence_factory()
                ),
            )
        )

        # ONE reconciliation service instance is shared
        # by document intelligence and final reconciliation.
        reconciliation = (
            SourceIntelligenceReconciliationService()
        )

        document_intelligence = (
            StartupAnalysisDocumentIntelligenceService(
                document_processing=processing,
                intelligence=intelligence,
                reconciliation=reconciliation,
            )
        )

        # ------------------------------------------------------------------
        # Stage 1/2 — InvestmentProfile extraction
        # ------------------------------------------------------------------

        profiles: list[Any] = []

        source_values: list[SourceValue] = []

        _section(
            "INVESTMENT INTELLIGENCE PROFILES"
        )

        for index, document in enumerate(
            documents,
            start=1,
        ):
            print()
            print(
                f"DOCUMENT [{index}/{len(documents)}] "
                f"{document.id}"
            )

            # IMPORTANT:
            # _analyze_document() expects the Document ID,
            # not the SQLAlchemy Document ORM object.
            profile = (
                document_intelligence._analyze_document(
                    document.id
                )
            )

            profiles.append(
                profile
            )

            print(
                _dump(
                    _profile_summary(
                        profile
                    )
                )
            )

            # Convert the profile to the exact SourceValue
            # representation used by reconciliation.
            facts = _profile_source_facts(
                profile,
            )

            print()
            print(
                f"SOURCE VALUES GENERATED: "
                f"{len(facts)}"
            )

            _print_source_values(
                facts
            )

            source_values.extend(
                facts
            )

        # ------------------------------------------------------------------
        # Stage 3 — all SourceValue objects
        # ------------------------------------------------------------------

        _section(
            "ALL SOURCE VALUES"
        )

        print(
            f"total_source_values : "
            f"{len(source_values)}"
        )

        _print_source_values(
            source_values
        )

        # ------------------------------------------------------------------
        # Stage 4 — reconciliation
        # ------------------------------------------------------------------

        _section(
            "SOURCE INTELLIGENCE RECONCILIATION"
        )

        startup_input = (
            _empty_startup_input(
                startup
            )
        )

        # Reuse the SAME reconciliation service instance.
        reconciled = (
            reconciliation.reconcile(
                startup_input,
                source_values,
            )
        )

        print(
            _dump(
                reconciled.model_dump(
                    mode="json"
                )
            )
        )

        # ------------------------------------------------------------------
        # Stage 5 — conflicts
        # ------------------------------------------------------------------

        conflicts = (
            reconciled.source_conflicts
        )

        _section(
            "SOURCE CONFLICTS"
        )

        print(
            f"conflict_count : "
            f"{len(conflicts)}"
        )

        for index, conflict in enumerate(
            conflicts,
            start=1,
        ):
            print()
            print(
                f"[{index}] FIELD: "
                f"{conflict.field}"
            )

            print(
                _dump(
                    conflict.model_dump(
                        mode="json"
                    )
                )
            )

        # ------------------------------------------------------------------
        # Stage 6 — validation matrix
        # ------------------------------------------------------------------

        _print_validation_matrix(
            source_values,
            reconciled,
            conflicts,
        )

        # ------------------------------------------------------------------
        # Machine-readable summary
        # ------------------------------------------------------------------

        grouped = _field_sources(
            source_values
        )

        classification_counts: dict[
            str,
            int,
        ] = defaultdict(int)

        classifications: dict[
            str,
            str,
        ] = {}

        for field in IMPORTANT_FIELDS:
            classification = (
                _classify_field(
                    field,
                    grouped.get(
                        field,
                        [],
                    ),
                    conflicts,
                )
            )

            classifications[
                field
            ] = classification

            classification_counts[
                classification
            ] += 1

        _section(
            "VALIDATION SUMMARY"
        )

        print(
            _dump(
                {
                    "startup_id": startup.id,
                    "startup": startup.name,
                    "document_count": len(
                        documents
                    ),
                    "profile_count": len(
                        profiles
                    ),
                    "source_value_count": len(
                        source_values
                    ),
                    "conflict_count": len(
                        conflicts
                    ),
                    "classification_counts": dict(
                        classification_counts
                    ),
                    "classifications": (
                        classifications
                    ),
                }
            )
        )

        print()
        print("=" * 88)
        print(
            "READ-ONLY VALIDATION COMPLETE"
        )
        print("=" * 88)

        return 0

    finally:
        db.close()


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate real RestoMart source intelligence "
            "without modifying the database."
        )
    )

    parser.add_argument(
        "--startup-id",
        default=DEFAULT_STARTUP_ID,
        help=(
            "Startup UUID. Defaults to the current "
            "RestoMart startup."
        ),
    )

    args = parser.parse_args()

    try:
        startup_id = UUID(
            args.startup_id
        )
    except ValueError as exc:
        parser.error(
            f"Invalid startup UUID: "
            f"{args.startup_id}"
        )
        raise exc

    return validate(
        startup_id
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
