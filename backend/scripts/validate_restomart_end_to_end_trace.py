#!/usr/bin/env python3
"""
C.7.7.7 — Production RestoMart End-to-End Source → Analysis Trace.

Production diagnostic / acceptance script.

This script validates the real production path:

    Startup
      ↓
    Production documents
      ↓
    DocumentProcessingService
      ↓
    InvestmentProfile
      ↓
    SourceValue[]
      ↓
    SourceIntelligenceReconciliationService
      ↓
    StartupAnalysisInput
      ↓
    FinancialMetricsService
      ↓
    build_startup_analysis_messages()
      ↓
    QwenProvider [optional]
      ↓
    StartupAnalysisParser
      ↓
    StartupAnalysisResult

Important:
    - This script does NOT persist StartupAnalysis.
    - It does NOT reconstruct document intelligence.
    - It does NOT replace production reconciliation.
    - It observes the InvestmentProfile boundary using the
      production factory's diagnostic profile_observer hook.
    - SourceValue[] and SourceConflict[] are obtained from the
      actual reconciled StartupAnalysisInput returned by production.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID


# ============================================================================
# Repository import path
# ============================================================================

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


# ============================================================================
# Application imports
# ============================================================================

from sqlalchemy import select

from app.core.database.session import create_session
from app.core.config import settings

from app.models.analysis import StartupAnalysisMode
from app.models.startup import Startup

from app.prompt.startup_analysis import (
    build_startup_analysis_messages,
)

from app.schemas.analysis import (
    FinancialMetrics,
    StartupAnalysisInput,
    StartupAnalysisResult,
)

from app.services.financial_metrics import (
    FinancialMetricsService,
)

from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)

from app.services.startup_analysis_input_builder import (
    StartupAnalysisInputBuilder,
)

from app.services.startup_analysis_parser import (
    StartupAnalysisParser,
)

from app.llm.models import LLMRequest
from app.llm.providers.qwen import QwenProvider


# ============================================================================
# Constants
# ============================================================================

DEFAULT_STARTUP_ID = (
    "dbb520d7-0979-4db3-8464-523f5710455f"
)

EXPECTED_STARTUP_NAME = "RestoMart"

EXPECTED_FACTS = (
    "revenue",
    "valuation",
    "raise_amount",
    "runway_months",
    "business_model",
)

EXPECTED_DOCUMENT_INTELLIGENCE_COMPONENTS = (
    "metadata",
    "entities",
    "financials",
    "signals",
    "risks",
)


# ============================================================================
# Source-intelligence vocabulary → canonical analysis vocabulary
# ============================================================================

CANONICAL_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "revenue": (
        "financials",
        "revenue",
    ),

    "valuation": (
        "fundraising",
        "valuation_cap",
    ),

    "raise_amount": (
        "fundraising",
        "amount_raising",
    ),

    "runway_months": (
        "financials",
        "runway_months",
    ),

    "business_model": (
        "business_model",
        "business_model",
    ),
}


# ============================================================================
# Trace state
# ============================================================================

@dataclass
class TraceState:
    """
    State captured while walking the production pipeline.
    """

    profiles: list[Any]

    source_facts: list[Any]

    source_conflicts: list[Any]

    baseline_input: StartupAnalysisInput | None = None

    enriched_input: StartupAnalysisInput | None = None

    metrics: FinancialMetrics | None = None

    messages: tuple[Any, ...] | None = None

    llm_response: Any | None = None

    analysis_result: StartupAnalysisResult | None = None


# ============================================================================
# Reporter
# ============================================================================

class TraceReporter:
    """Simple deterministic terminal reporter."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def header(self, title: str) -> None:
        print()
        print("=" * 88)
        print(title)
        print("=" * 88)

    def section(self, title: str) -> None:
        print()
        print("-" * 88)
        print(title)
        print("-" * 88)

    def pass_(self, message: str) -> None:
        print(f"[PASS] {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"[FAIL] {message}")

    def info(self, label: str, value: Any) -> None:
        print(f"{label:<30}: {value}")

    def result(self) -> int:
        self.header("C.7.7.7 RESULT")

        if self.failures:
            print("RESULT : FAIL")
            print()
            print("Failures:")

            for failure in self.failures:
                print(f"  - {failure}")

            if self.warnings:
                print()
                print("Warnings:")

                for warning in self.warnings:
                    print(f"  - {warning}")

            return 1

        if self.warnings:
            print("RESULT : PASS WITH WARNINGS")
            print()
            print("Warnings:")

            for warning in self.warnings:
                print(f"  - {warning}")

            return 0

        print("RESULT : PASS")
        return 0


# ============================================================================
# Generic helpers
# ============================================================================

def get_canonical_value(
    analysis_input: StartupAnalysisInput,
    path: tuple[str, ...],
) -> Any:
    """
    Resolve a canonical StartupAnalysisInput value.

    Example:

        ("fundraising", "valuation_cap")
    """

    current: Any = analysis_input

    for attribute in path:
        if current is None:
            return None

        current = getattr(
            current,
            attribute,
            None,
        )

    return current


def _json_safe(value: Any) -> Any:
    """Convert common application values into JSON-safe values."""

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return str(value)

    if hasattr(value, "value") and not isinstance(
        value,
        (str, bytes, dict, list, tuple),
    ):
        try:
            return value.value
        except Exception:
            pass

    if hasattr(value, "model_dump"):
        return value.model_dump(
            mode="json",
            exclude_none=False,
        )

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


def _dump_model(value: Any) -> dict[str, Any]:
    """Dump a Pydantic/dataclass-like model for diagnostics."""

    if hasattr(value, "model_dump"):
        return value.model_dump(
            mode="json",
            exclude_none=False,
        )

    if hasattr(value, "__dict__"):
        return {
            key: _json_safe(item)
            for key, item in value.__dict__.items()
            if not key.startswith("_")
        }

    return {}


def _normalize_business_models(
    value: Any,
) -> set[str]:
    """
    Normalize business-model values.

    Examples:

        "b2b"
        "marketplace"

    and:

        "b2b, marketplace"

    both become:

        {"b2b", "marketplace"}
    """

    if value is None:
        return set()

    if isinstance(value, str):
        return {
            item.strip().lower()
            for item in value.split(",")
            if item.strip()
        }

    if isinstance(value, (list, tuple, set)):
        normalized: set[str] = set()

        for item in value:
            normalized.update(
                _normalize_business_models(item)
            )

        return normalized

    return {
        str(value).strip().lower()
    }


def _normalise_scalar(value: Any) -> Any:
    """Normalize scalar values for semantic comparison."""

    if value is None:
        return None

    if isinstance(value, Decimal):
        return value.normalize()

    if isinstance(value, float):
        return Decimal(str(value)).normalize()

    if isinstance(value, int):
        return Decimal(value).normalize()

    if isinstance(value, str):
        stripped = value.strip()

        try:
            return Decimal(stripped).normalize()
        except Exception:
            return stripped.lower()

    return value


def _values_equal(
    left: Any,
    right: Any,
) -> bool:
    """Compare scalar values without semantic loss."""

    return (
        _normalise_scalar(left)
        == _normalise_scalar(right)
    )


def _value_text_candidates(value: Any) -> set[str]:
    """
    Produce representations likely to appear in a textual LLM payload.

    This avoids making the validator depend on one particular Decimal
    formatting choice.
    """

    if value is None:
        return set()

    candidates = {
        str(value),
        str(_json_safe(value)),
    }

    if isinstance(value, Decimal):
        candidates.add(
            format(value, "f")
        )

        candidates.add(
            str(value.normalize())
        )

    return {
        candidate
        for candidate in candidates
        if candidate
    }


# ============================================================================
# Startup loading
# ============================================================================

def load_startup(
    session,
    startup_id: UUID,
) -> Startup | None:
    """Load the real persisted startup aggregate."""

    return session.execute(
        select(Startup).where(
            Startup.id == startup_id,
        )
    ).scalar_one_or_none()


# ============================================================================
# Profile observer
# ============================================================================

def build_profile_observer(
    state: TraceState,
):
    """
    Create the diagnostic InvestmentProfile observer.

    This observes the production boundary without changing production
    behavior.
    """

    def observe(profile: Any) -> None:
        state.profiles.append(profile)

    return observe


# ============================================================================
# Startup / source inventory
# ============================================================================

def print_startup_inventory(
    reporter: TraceReporter,
    startup: Startup,
) -> None:
    """Print the persisted RestoMart source inventory."""

    reporter.section(
        "1. STARTUP / SOURCE INVENTORY"
    )

    reporter.info(
        "startup_id",
        startup.id,
    )

    reporter.info(
        "startup_name",
        startup.name,
    )

    documents = startup.documents or []

    reporter.info(
        "document_count",
        len(documents),
    )

    if startup.name != EXPECTED_STARTUP_NAME:
        reporter.warn(
            f"Expected '{EXPECTED_STARTUP_NAME}', "
            f"found '{startup.name}'."
        )
    else:
        reporter.pass_(
            f"Startup identity verified: {EXPECTED_STARTUP_NAME}."
        )

    if not documents:
        reporter.fail(
            "Startup has no production source documents."
        )
        return

    reporter.pass_(
        f"{len(documents)} production source document(s) found."
    )

    for document in documents:
        print()
        print(f"DOCUMENT {document.id}")
        print("-" * 88)

        reporter.info(
            "title",
            getattr(
                document,
                "title",
                None,
            ),
        )

        reporter.info(
            "filename",
            getattr(
                document,
                "filename",
                None,
            ),
        )

        reporter.info(
            "mime_type",
            getattr(
                document,
                "mime_type",
                None,
            ),
        )

        reporter.info(
            "storage_path",
            getattr(
                document,
                "storage_path",
                None,
            ),
        )


# ============================================================================
# Document → InvestmentProfile
# ============================================================================

def process_documents_for_observation(
    reporter: TraceReporter,
    state: TraceState,
    startup: Startup,
    document_intelligence: Any,
) -> None:
    """
    Run the actual production document-intelligence enrichment.

    This deliberately calls the production service.
    """

    reporter.section(
        "2. DOCUMENT → INVESTMENT PROFILE"
    )

    if not startup.documents:
        reporter.fail(
            "RestoMart has no documents."
        )
        return

    if state.baseline_input is None:
        reporter.fail(
            "Baseline StartupAnalysisInput is missing."
        )
        return

    try:
        state.enriched_input = (
            document_intelligence.enrich(
                startup,
                state.baseline_input,
            )
        )
    except Exception as exc:
        reporter.fail(
            "Production document-intelligence enrichment failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return

    reporter.pass_(
        "Production document-intelligence enrichment completed."
    )

    # ------------------------------------------------------------------
    # IMPORTANT:
    #
    # Source facts and conflicts are taken from the actual production
    # result rather than from a second diagnostic observer.
    # ------------------------------------------------------------------

    state.source_facts = list(
        state.enriched_input.source_facts or []
    )

    state.source_conflicts = list(
        state.enriched_input.source_conflicts or []
    )

    reporter.info(
        "profiles_observed",
        len(state.profiles),
    )

    reporter.info(
        "source_facts",
        len(state.source_facts),
    )

    reporter.info(
        "source_conflicts",
        len(state.source_conflicts),
    )


# ============================================================================
# InvestmentProfile validation
# ============================================================================

def validate_profiles(
    reporter: TraceReporter,
    state: TraceState,
    startup: Startup,
) -> None:
    """Validate the InvestmentProfile production boundary."""

    reporter.section(
        "3. INVESTMENT PROFILE HANDSHAKE"
    )

    documents = startup.documents or []

    if not state.profiles:
        reporter.fail(
            "No InvestmentProfile was observed."
        )
        return

    reporter.pass_(
        f"Observed {len(state.profiles)} InvestmentProfile(s)."
    )

    if len(state.profiles) != len(documents):
        reporter.fail(
            "InvestmentProfile count does not match "
            f"document count: "
            f"{len(state.profiles)} profiles vs "
            f"{len(documents)} documents."
        )
    else:
        reporter.pass_(
            "InvestmentProfile count matches document count."
        )

    startup_document_ids = {
        document.id
        for document in documents
    }

    observed_document_ids = {
        getattr(
            profile,
            "document_id",
            None,
        )
        for profile in state.profiles
    }

    unknown_profiles = (
        observed_document_ids
        - startup_document_ids
    )

    if unknown_profiles:
        reporter.fail(
            "InvestmentProfile contains document IDs "
            f"not belonging to startup: {unknown_profiles}"
        )
    else:
        reporter.pass_(
            "Every observed InvestmentProfile belongs "
            "to a RestoMart source document."
        )

    for index, profile in enumerate(
        state.profiles,
        start=1,
    ):
        reporter.info(
            f"profile[{index}].document_id",
            getattr(
                profile,
                "document_id",
                None,
            ),
        )

        evidence_count = len(
            getattr(
                profile,
                "evidence",
                None,
            )
            or ()
        )

        reporter.info(
            f"profile[{index}].evidence_count",
            evidence_count,
        )

        if evidence_count:
            reporter.pass_(
                f"Profile {index} contains source evidence."
            )
        else:
            reporter.warn(
                f"Profile {index} contains no evidence."
            )

        missing_components = []

        for component in (
            EXPECTED_DOCUMENT_INTELLIGENCE_COMPONENTS
        ):
            value = getattr(
                profile,
                component,
                None,
            )

            if value is None:
                missing_components.append(
                    component
                )

        if missing_components:
            reporter.warn(
                f"Profile {index} missing components: "
                f"{missing_components}"
            )
        else:
            reporter.pass_(
                f"Profile {index} contains all core "
                "InvestmentProfile components."
            )


# ============================================================================
# SourceValue helpers
# ============================================================================

def get_source_values(
    state: TraceState,
    field: str,
) -> list[Any]:
    """Return SourceValue facts for a producer field."""

    return [
        source_value
        for source_value in state.source_facts
        if getattr(
            source_value,
            "field",
            None,
        ) == field
    ]


def print_source_value(
    reporter: TraceReporter,
    source_value: Any,
) -> None:
    """Print one SourceValue."""

    reporter.info(
        "field",
        getattr(
            source_value,
            "field",
            None,
        ),
    )

    reporter.info(
        "value",
        getattr(
            source_value,
            "value",
            None,
        ),
    )

    reporter.info(
        "status",
        getattr(
            source_value,
            "status",
            None,
        ),
    )

    reporter.info(
        "source_document_id",
        getattr(
            source_value,
            "source_document_id",
            None,
        ),
    )

    reporter.info(
        "source_name",
        getattr(
            source_value,
            "source_name",
            None,
        ),
    )

    reporter.info(
        "source_authority",
        getattr(
            source_value,
            "source_authority",
            None,
        ),
    )

    reporter.info(
        "section",
        getattr(
            source_value,
            "section",
            None,
        ),
    )

    reporter.info(
        "confidence",
        getattr(
            source_value,
            "confidence",
            None,
        ),
    )

    reporter.info(
        "source_text",
        getattr(
            source_value,
            "source_text",
            None,
        )
    )


# ============================================================================
# Source → canonical reconciliation
# ============================================================================

def validate_reconciliation(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """
    Validate SourceValue → StartupAnalysisInput.

    Missing source information is a warning.

    Information loss after a source fact exists is a failure.

    Material reconciliation conflicts are failures for this production
    acceptance trace.
    """

    reporter.section(
        "4. SOURCE VALUE → CANONICAL ANALYSIS INPUT"
    )

    if not state.source_facts:
        reporter.fail(
            "No SourceValue facts were produced."
        )
        return

    reporter.pass_(
        f"Produced {len(state.source_facts)} SourceValue fact(s)."
    )

    reporter.info(
        "source_conflicts",
        len(state.source_conflicts),
    )

    if state.source_conflicts:
        reporter.fail(
            "Material source conflicts were detected."
        )

        for conflict in state.source_conflicts:
            reporter.info(
                "conflict.field",
                getattr(
                    conflict,
                    "field",
                    None,
                ),
            )

    else:
        reporter.pass_(
            "No source reconciliation conflicts detected."
        )

    if state.enriched_input is None:
        reporter.fail(
            "No reconciled StartupAnalysisInput was produced."
        )
        return

    reporter.pass_(
        "StartupAnalysisInput was produced after reconciliation."
    )

    for field in EXPECTED_FACTS:
        source_values = get_source_values(
            state,
            field,
        )

        print()
        print(f"FACT: {field}")
        print("." * 88)

        reporter.info(
            "source_value_count",
            len(source_values),
        )

        canonical_path = CANONICAL_FIELD_MAP.get(
            field
        )

        if canonical_path is None:
            reporter.fail(
                f"No canonical mapping defined for '{field}'."
            )
            continue

        reporter.info(
            "canonical_path",
            ".".join(canonical_path),
        )

        # --------------------------------------------------------------
        # Missing source information.
        #
        # This is not a reconciliation failure.
        # --------------------------------------------------------------

        if not source_values:
            canonical_value = get_canonical_value(
                state.enriched_input,
                canonical_path,
            )

            reporter.info(
                "canonical_value",
                canonical_value,
            )

            if canonical_value is None:
                reporter.warn(
                    f"No SourceValue found for '{field}'."
                )
            else:
                reporter.warn(
                    f"No SourceValue found for '{field}', "
                    f"but canonical value exists at "
                    f"'{'.'.join(canonical_path)}'."
                )

            continue

        canonical_value = get_canonical_value(
            state.enriched_input,
            canonical_path,
        )

        reporter.info(
            "canonical_value",
            canonical_value,
        )

        for source_value in source_values:
            print_source_value(
                reporter,
                source_value,
            )

        # --------------------------------------------------------------
        # Business model is semantically multi-valued.
        # --------------------------------------------------------------

        if field == "business_model":
            source_models: set[str] = set()

            for source_value in source_values:
                source_models.update(
                    _normalize_business_models(
                        getattr(
                            source_value,
                            "value",
                            None,
                        )
                    )
                )

            canonical_models = (
                _normalize_business_models(
                    canonical_value
                )
            )

            reporter.info(
                "normalized_source_models",
                sorted(source_models),
            )

            reporter.info(
                "normalized_canonical_models",
                sorted(canonical_models),
            )

            if source_models == canonical_models:
                reporter.pass_(
                    "business_model: SourceValue values "
                    "normalized into canonical input."
                )
            else:
                reporter.fail(
                    "business_model: canonical values differ "
                    "from normalized SourceValue values."
                )

            continue

        # --------------------------------------------------------------
        # Scalar source facts.
        # --------------------------------------------------------------

        if canonical_value is None:
            reporter.fail(
                f"'{field}' existed in SourceValue[] but was not "
                f"preserved at canonical path "
                f"'{'.'.join(canonical_path)}'."
            )
            continue

        matching_values = [
            source_value
            for source_value in source_values
            if _values_equal(
                getattr(
                    source_value,
                    "value",
                    None,
                ),
                canonical_value,
            )
        ]

        if matching_values:
            reporter.pass_(
                f"{field} → "
                f"{'.'.join(canonical_path)} preserved."
            )
        else:
            reporter.fail(
                f"{field}: SourceValue exists but canonical "
                f"value differs at "
                f"'{'.'.join(canonical_path)}'."
            )


# ============================================================================
# Baseline → enriched input
# ============================================================================

def validate_baseline_and_enriched_input(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Validate the baseline → document-intelligence boundary."""

    reporter.section(
        "5. BASELINE → ENRICHED ANALYSIS INPUT"
    )

    baseline = state.baseline_input
    enriched = state.enriched_input

    if baseline is None:
        reporter.fail(
            "Baseline StartupAnalysisInput was not created."
        )
        return

    reporter.pass_(
        "Baseline StartupAnalysisInput created."
    )

    if enriched is None:
        reporter.fail(
            "Enriched StartupAnalysisInput was not created."
        )
        return

    reporter.pass_(
        "Enriched StartupAnalysisInput created."
    )

    baseline_payload = _dump_model(
        baseline
    )

    enriched_payload = _dump_model(
        enriched
    )

    for field in (
        "company",
        "founders",
        "product",
        "market",
        "traction",
        "financials",
        "fundraising",
        "business_model",
        "evidence",
        "source_facts",
        "source_conflicts",
    ):
        before = baseline_payload.get(
            field
        )

        after = enriched_payload.get(
            field
        )

        if before == after:
            print(
                f"  {field:<20} unchanged"
            )
        else:
            print(
                f"  {field:<20} enriched/changed"
            )

    if not enriched.source_facts:
        reporter.fail(
            "Enriched StartupAnalysisInput contains "
            "no source_facts."
        )
    else:
        reporter.pass_(
            "Enriched StartupAnalysisInput contains "
            f"{len(enriched.source_facts)} source fact(s)."
        )


# ============================================================================
# Deterministic financial metrics
# ============================================================================

def calculate_metrics(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Run the production deterministic financial metric service."""

    reporter.section(
        "6. DETERMINISTIC FINANCIAL METRICS"
    )

    if state.enriched_input is None:
        reporter.fail(
            "Cannot calculate metrics without canonical input."
        )
        return

    state.metrics = (
        FinancialMetricsService.calculate(
            financials=state.enriched_input.financials,
            fundraising=state.enriched_input.fundraising,
            business_model=state.enriched_input.business_model,
        )
    )

    reporter.pass_(
        "FinancialMetricsService.calculate() completed."
    )

    payload = _dump_model(
        state.metrics
    )

    print(
        json.dumps(
            _json_safe(payload),
            indent=2,
            ensure_ascii=False,
        )
    )


# ============================================================================
# Canonical input → LLM payload
# ============================================================================

def build_llm_payload(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Build and validate the exact production startup-analysis messages."""

    reporter.section(
        "7. CANONICAL INPUT → LLM PAYLOAD"
    )

    if state.enriched_input is None:
        reporter.fail(
            "Cannot build LLM payload without canonical input."
        )
        return

    if state.metrics is None:
        reporter.fail(
            "Cannot build LLM payload without deterministic metrics."
        )
        return

    state.messages = (
        build_startup_analysis_messages(
            analysis_input=state.enriched_input,
            metrics=state.metrics,
        )
    )

    reporter.pass_(
        "Production startup analysis messages generated."
    )

    for index, message in enumerate(
        state.messages
    ):
        print()
        print(
            f"MESSAGE[{index}] role={message.role}"
        )
        print("-" * 88)
        print(message.content)

    user_messages = [
        message
        for message in state.messages
        if message.role == "user"
    ]

    if not user_messages:
        reporter.fail(
            "No user message found in production LLM messages."
        )
        return

    user_content = user_messages[-1].content

    # --------------------------------------------------------------
    # Verify that canonical fields actually reach the real payload.
    # --------------------------------------------------------------

    for field in EXPECTED_FACTS:
        canonical_value = get_canonical_value(
            state.enriched_input,
            CANONICAL_FIELD_MAP[field],
        )

        # Missing source/canonical value is already handled by the
        # reconciliation stage.
        if canonical_value is None:
            continue

        value_candidates = _value_text_candidates(
            canonical_value
        )

        if any(
            candidate in user_content
            for candidate in value_candidates
        ):
            reporter.pass_(
                f"LLM payload contains canonical {field}."
            )
        else:
            reporter.fail(
                f"LLM payload lost canonical {field}."
            )

    # --------------------------------------------------------------
    # Deterministic metrics must also reach the payload.
    # --------------------------------------------------------------

    metrics_payload = _dump_model(
        state.metrics
    )

    for metric_name, metric_value in (
        metrics_payload.items()
    ):
        if metric_value is None:
            continue

        candidates = _value_text_candidates(
            metric_value
        )

        if any(
            candidate in user_content
            for candidate in candidates
        ):
            reporter.pass_(
                f"LLM payload contains deterministic metric "
                f"'{metric_name}'."
            )
        else:
            reporter.warn(
                f"LLM payload does not visibly contain "
                f"metric '{metric_name}'."
            )


# ============================================================================
# Real Qwen execution
# ============================================================================

def run_llm(
    reporter: TraceReporter,
    state: TraceState,
    mode: StartupAnalysisMode,
) -> None:
    """Execute the real production Qwen provider."""

    reporter.section(
        "8. REAL QWEN EXECUTION"
    )

    if state.messages is None:
        reporter.fail(
            "Cannot execute Qwen without LLM messages."
        )
        return

    from app.services.startup_analysis_config import (
        get_startup_analysis_config,
    )

    config = get_startup_analysis_config(
        mode,
        config=settings,
    )

    request = LLMRequest(
        messages=state.messages,
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        metadata={
            "thinking_enabled": config.thinking_enabled,
        },
    )

    reporter.info(
        "model",
        config.model_name,
    )

    reporter.info(
        "mode",
        mode,
    )

    reporter.info(
        "thinking_enabled",
        config.thinking_enabled,
    )

    reporter.info(
        "max_tokens",
        config.max_tokens,
    )

    provider = QwenProvider(
        config=settings,
    )

    try:
        state.llm_response = provider.generate(
            request
        )
    except Exception as exc:
        reporter.fail(
            "Qwen generation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return

    response = state.llm_response

    reporter.info(
        "finish_reason",
        response.finish_reason,
    )

    reporter.info(
        "usage",
        response.usage,
    )

    if response.finish_reason == "length":
        reporter.fail(
            "Qwen response was truncated."
        )
        return

    if not response.text:
        reporter.fail(
            "Qwen returned an empty response."
        )
        return

    reporter.pass_(
        "Qwen returned a non-truncated response."
    )

    print()
    print("RAW QWEN RESPONSE")
    print("-" * 88)
    print(response.text)


# ============================================================================
# LLM response → StartupAnalysisResult
# ============================================================================

def parse_llm_result(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Run the production StartupAnalysisParser."""

    reporter.section(
        "9. LLM RESPONSE → ANALYSIS RESULT"
    )

    if state.llm_response is None:
        reporter.warn(
            "LLM execution was skipped."
        )
        return

    if (
        state.llm_response.finish_reason
        == "length"
    ):
        reporter.fail(
            "Cannot parse truncated LLM response."
        )
        return

    parser = StartupAnalysisParser()

    try:
        state.analysis_result = parser.parse(
            state.llm_response.text
        )
    except Exception as exc:
        reporter.fail(
            "StartupAnalysisParser failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return

    reporter.pass_(
        "StartupAnalysisResult parsed successfully."
    )

    payload = _dump_model(
        state.analysis_result
    )

    print(
        json.dumps(
            _json_safe(payload),
            indent=2,
            ensure_ascii=False,
        )
    )

    recommendation = getattr(
        state.analysis_result,
        "preliminary_recommendation",
        None,
    )

    if recommendation is not None:
        reporter.info(
            "preliminary_recommendation",
            recommendation,
        )


# ============================================================================
# Argument parsing
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Validate the production RestoMart "
            "Document → InvestmentProfile → "
            "SourceValue → Reconciliation → "
            "LLM → StartupAnalysisResult flow."
        )
    )

    parser.add_argument(
        "--startup-id",
        default=DEFAULT_STARTUP_ID,
        help=(
            "RestoMart startup UUID. "
            f"Default: {DEFAULT_STARTUP_ID}"
        ),
    )

    parser.add_argument(
        "--mode",
        choices=(
            "standard",
            "deep",
        ),
        default="standard",
        help="Startup analysis LLM mode.",
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Execute the real Qwen provider.",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=(
            "Explicitly skip Qwen execution. "
            "Useful for deterministic handshake validation."
        ),
    )

    return parser.parse_args()


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    """Run the complete production trace."""

    args = parse_args()

    reporter = TraceReporter()

    try:
        startup_id = UUID(
            args.startup_id
        )
    except ValueError:
        print(
            f"Invalid startup UUID: {args.startup_id}",
            file=sys.stderr,
        )
        return 2

    if args.llm and args.no_llm:
        print(
            "--llm and --no-llm are mutually exclusive.",
            file=sys.stderr,
        )
        return 2

    run_llm_enabled = (
        args.llm
        and not args.no_llm
    )

    mode = (
        StartupAnalysisMode.DEEP
        if args.mode == "deep"
        else StartupAnalysisMode.STANDARD
    )

    reporter.header(
        "C.7.7.7 — RESTOMART PRODUCTION "
        "END-TO-END SOURCE → ANALYSIS TRACE"
    )

    reporter.info(
        "startup_id",
        startup_id,
    )

    reporter.info(
        "LLM execution",
        "ENABLED"
        if run_llm_enabled
        else "DISABLED",
    )

    reporter.info(
        "analysis mode",
        mode,
    )

    session = create_session()

    try:
        # --------------------------------------------------------------
        # 1. Startup / source inventory
        # --------------------------------------------------------------

        startup = load_startup(
            session,
            startup_id,
        )

        if startup is None:
            reporter.fail(
                f"Startup not found: {startup_id}"
            )
            return reporter.result()

        reporter.pass_(
            "RestoMart startup loaded from production database."
        )

        print_startup_inventory(
            reporter,
            startup,
        )

        # --------------------------------------------------------------
        # 2. Baseline StartupAnalysisInput
        # --------------------------------------------------------------

        reporter.section(
            "BASELINE ANALYSIS INPUT"
        )

        state = TraceState(
            profiles=[],
            source_facts=[],
            source_conflicts=[],
        )

        builder = StartupAnalysisInputBuilder()

        try:
            state.baseline_input = (
                builder.build(
                    startup
                )
            )
        except Exception as exc:
            reporter.fail(
                "StartupAnalysisInputBuilder failed: "
                f"{type(exc).__name__}: {exc}"
            )
            return reporter.result()

        reporter.pass_(
            "StartupAnalysisInputBuilder completed."
        )

        # --------------------------------------------------------------
        # 3. Production document-intelligence factory
        # --------------------------------------------------------------

        reporter.section(
            "PRODUCTION DOCUMENT INTELLIGENCE FACTORY"
        )

        profile_observer = (
            build_profile_observer(state)
        )

        try:
            document_intelligence = (
                StartupAnalysisApplicationService
                .create_startup_analysis_document_intelligence(
                    session,
                    profile_observer=profile_observer,
                )
            )
        except Exception as exc:
            reporter.fail(
                "Production document-intelligence factory failed: "
                f"{type(exc).__name__}: {exc}"
            )
            return reporter.result()

        reporter.pass_(
            "Production document-intelligence factory created."
        )

        # --------------------------------------------------------------
        # 4. Execute real document-intelligence path
        # --------------------------------------------------------------

        process_documents_for_observation(
            reporter,
            state,
            startup,
            document_intelligence,
        )

        # --------------------------------------------------------------
        # 5. InvestmentProfile boundary
        # --------------------------------------------------------------

        validate_profiles(
            reporter,
            state,
            startup,
        )

        # --------------------------------------------------------------
        # 6. SourceValue → canonical reconciliation
        # --------------------------------------------------------------

        validate_reconciliation(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 7. Baseline → enriched input
        # --------------------------------------------------------------

        validate_baseline_and_enriched_input(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 8. Deterministic financial metrics
        # --------------------------------------------------------------

        calculate_metrics(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 9. Canonical input → LLM payload
        # --------------------------------------------------------------

        build_llm_payload(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 10. Optional real Qwen execution
        # --------------------------------------------------------------

        if run_llm_enabled:
            run_llm(
                reporter,
                state,
                mode,
            )

            parse_llm_result(
                reporter,
                state,
            )
        else:
            reporter.section(
                "10. LLM EXECUTION"
            )

            reporter.info(
                "status",
                "SKIPPED (--no-llm)",
            )

        return reporter.result()

    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
