#!/usr/bin/env python3
"""
C.7.7.7 — Production RestoMart End-to-End Source → Analysis Trace.

This is a production diagnostic script.

It intentionally lives under scripts/ rather than tests/ because:

    * it exercises the real document-processing pipeline;
    * it exercises the real InvestmentProfile generation;
    * it exercises source reconciliation;
    * it can optionally invoke the real Qwen provider;
    * it may take several minutes when Qwen is enabled.

The script NEVER persists a StartupAnalysis.

Production path validated:

    Startup
      ↓
    DocumentProcessingService
      ↓
    DocumentContent + Chunk[]
      ↓
    InvestmentIntelligenceService
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

Usage:

    docker compose exec -T backend \
        python -u scripts/validate_restomart_end_to_end_trace.py

Or explicitly:

    docker compose exec -T backend \
        python -u scripts/validate_restomart_end_to_end_trace.py \
        --startup-id dbb520d7-0979-4db3-8464-523f5710455f

Without Qwen:

    docker compose exec -T backend \
        python -u scripts/validate_restomart_end_to_end_trace.py \
        --no-llm

With Qwen:

    docker compose exec -T backend \
        python -u scripts/validate_restomart_end_to_end_trace.py \
        --llm
"""

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID


# ---------------------------------------------------------------------------
# Repository import path
# ---------------------------------------------------------------------------
#
# When executed as:
#
#     python scripts/validate_restomart_end_to_end_trace.py
#
# Python places scripts/ on sys.path, not the repository root.
#
# Add the repository root explicitly so production imports such as
# `from app...` work exactly like they do under pytest.
#

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


# ---------------------------------------------------------------------------
# Application imports
# ---------------------------------------------------------------------------

from sqlalchemy import select

from app.core.config import settings
from app.core.database.session import create_session

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Source-intelligence field → canonical StartupAnalysisInput path
#
# IMPORTANT:
# SourceValue.field names are producer/source vocabulary.
# StartupAnalysisInput fields are canonical application vocabulary.
# They must not be assumed to have identical names.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Trace state
# ---------------------------------------------------------------------------


@dataclass
class TraceState:
    """State captured while walking the production pipeline."""

    profiles: list[Any]

    source_facts: list[Any]

    source_conflicts: list[Any]

    baseline_input: StartupAnalysisInput | None = None

    enriched_input: StartupAnalysisInput | None = None

    metrics: FinancialMetrics | None = None

    messages: tuple[Any, ...] | None = None

    llm_response: Any | None = None

    analysis_result: StartupAnalysisResult | None = None


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def get_canonical_value(
    analysis_input: StartupAnalysisInput,
    path: tuple[str, ...],
):
    """
    Resolve a canonical value from StartupAnalysisInput using an explicit
    semantic field path.

    Example:
        ("fundraising", "valuation_cap")
    """
    current = analysis_input

    for attribute in path:
        if current is None:
            return None

        current = getattr(current, attribute, None)

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


def _get_nested(
    obj: Any,
    *names: str,
) -> Any:
    """Return the first existing nested attribute."""

    current = obj

    for name in names:
        if current is None:
            return None

        if isinstance(current, dict):
            current = current.get(name)
        else:
            current = getattr(
                current,
                name,
                None,
            )

    return current

def _normalize_business_models(
    value: Any,
) -> set[str]:
    """
    Normalize business-model values for handshake comparison.

    SourceValue[] may contain multiple scalar values such as:

        "b2b"
        "marketplace"

    while StartupAnalysisInput may contain the canonical combined
    representation:

        "b2b, marketplace"

    The validator compares semantic membership rather than raw
    string equality.
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
    """Normalize numeric values for comparison."""

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
    """Compare values without making semantic assumptions."""

    left_normalized = _normalise_scalar(left)
    right_normalized = _normalise_scalar(right)

    return left_normalized == right_normalized


# ---------------------------------------------------------------------------
# Startup loading
# ---------------------------------------------------------------------------


def load_startup(
    session,
    startup_id: UUID,
) -> Startup | None:
    """Load the real persisted startup aggregate."""

    return session.execute(
        select(Startup).where(
            Startup.id == startup_id
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Profile observer
# ---------------------------------------------------------------------------


def build_profile_observer(
    state: TraceState,
):
    """
    Create the diagnostic observer.

    This observer does not modify the production profile.
    """

    def observe(profile: Any) -> None:
        state.profiles.append(profile)

    return observe


# ---------------------------------------------------------------------------
# InvestmentProfile validation
# ---------------------------------------------------------------------------


def validate_profiles(
    reporter: TraceReporter,
    state: TraceState,
    startup: Startup,
) -> None:
    """Validate the InvestmentProfile boundary."""

    reporter.section(
        "3. INVESTMENT PROFILE HANDSHAKE"
    )

    if not state.profiles:
        reporter.fail(
            "No InvestmentProfile was observed."
        )
        return

    reporter.pass_(
        f"Observed {len(state.profiles)} InvestmentProfile(s)."
    )

    startup_document_ids = {
        document.id
        for document in (
            startup.documents or []
        )
    }

    if not startup_document_ids:
        reporter.warn(
            "Startup has no documents attached."
        )
        return

    observed_document_ids = {
        profile.document_id
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
            profile.document_id,
        )

        evidence_count = len(
            profile.evidence or ()
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


# ---------------------------------------------------------------------------
# SourceValue inspection
# ---------------------------------------------------------------------------


def source_value_matches(
    source_value: Any,
    field: str,
) -> bool:
    """Determine whether a SourceValue represents a field."""

    return (
        getattr(
            source_value,
            "field",
            None,
        )
        == field
    )


def get_source_values(
    state: TraceState,
    field: str,
) -> list[Any]:
    """Return observed source facts for a field."""

    return [
        source_value
        for source_value in state.source_facts
        if source_value_matches(
            source_value,
            field,
        )
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
        ),
    )


# ---------------------------------------------------------------------------
# Canonical StartupAnalysisInput validation
# ---------------------------------------------------------------------------


def get_canonical_fact(
    analysis_input: StartupAnalysisInput,
    field: str,
) -> Any:
    """
    Resolve the canonical StartupAnalysisInput value for a
    SourceValue field using CANONICAL_FIELD_MAP.
    """

    path = CANONICAL_FIELD_MAP.get(field)

    if path is None:
        return None

    return get_canonical_value(
        analysis_input,
        path,
    )


def validate_reconciliation(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Validate SourceValue → StartupAnalysisInput."""

    reporter.section(
        "5. SOURCE RECONCILIATION HANDSHAKE"
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
        reporter.warn(
            "Source conflicts were detected; "
            "they are intentionally preserved for diligence."
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
    
        canonical_path = CANONICAL_FIELD_MAP.get(field)
    
        if canonical_path is None:
            reporter.warn(
                f"No canonical mapping defined for '{field}'."
            )
            continue
    
        reporter.info(
            "canonical_path",
            ".".join(canonical_path),
        )
    
        # --------------------------------------------------------------
        # Missing source information is not a reconciliation failure.
        # --------------------------------------------------------------
    
        if not source_values:
            reporter.info(
                "canonical_value",
                None,
            )
    
            reporter.warn(
                f"No SourceValue found for '{field}'."
            )
    
            continue
    
        # --------------------------------------------------------------
        # SourceValue exists — canonical value must now exist.
        # --------------------------------------------------------------
    
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
    
            canonical_models = _normalize_business_models(
                canonical_value
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


# ---------------------------------------------------------------------------
# Baseline vs enriched input
# ---------------------------------------------------------------------------


def validate_baseline_and_enriched_input(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Show the actual baseline → enrichment boundary."""

    reporter.section(
        "4. DOCUMENT INTELLIGENCE → ANALYSIS INPUT"
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

    baseline_payload = _dump_model(baseline)
    enriched_payload = _dump_model(enriched)

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


# ---------------------------------------------------------------------------
# Financial metrics
# ---------------------------------------------------------------------------


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

    state.metrics = FinancialMetricsService.calculate(
        financials=state.enriched_input.financials,
        fundraising=state.enriched_input.fundraising,
        business_model=state.enriched_input.business_model,
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


# ---------------------------------------------------------------------------
# LLM payload
# ---------------------------------------------------------------------------


def build_llm_payload(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Build the exact production prompt."""

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

    # Verify canonical facts are present in the
    # actual user message rather than constructing
    # another payload ourselves.
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

    for field in EXPECTED_FACTS:
        canonical_value = get_canonical_fact(
            state.enriched_input,
            field,
        )

        if canonical_value is None:
            continue

        value_text = str(
            _json_safe(canonical_value)
        )

        if value_text in user_content:
            reporter.pass_(
                f"LLM payload contains canonical {field}."
            )
        else:
            reporter.fail(
                f"LLM payload lost canonical {field}."
            )


# ---------------------------------------------------------------------------
# Qwen execution
# ---------------------------------------------------------------------------


def run_llm(
    reporter: TraceReporter,
    state: TraceState,
    mode: StartupAnalysisMode,
) -> None:
    """Execute the real Qwen provider."""

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


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


def parse_llm_result(
    reporter: TraceReporter,
    state: TraceState,
) -> None:
    """Run the production response parser."""

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


# ---------------------------------------------------------------------------
# Startup / document trace
# ---------------------------------------------------------------------------


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

    reporter.info(
        "document_count",
        len(startup.documents or []),
    )

    if startup.name != EXPECTED_STARTUP_NAME:
        reporter.warn(
            f"Expected '{EXPECTED_STARTUP_NAME}', "
            f"found '{startup.name}'."
        )

    for document in (
        startup.documents or []
    ):
        print()
        print(
            f"DOCUMENT {document.id}"
        )
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


def process_documents_for_observation(
    reporter: TraceReporter,
    state: TraceState,
    startup: Startup,
    document_intelligence: Any,
) -> None:
    """
    Run the actual production document-intelligence enrichment.

    This deliberately calls the production service rather than
    reimplementing document processing.
    """

    reporter.section(
        "2. PRODUCTION DOCUMENT → INVESTMENT PROFILE"
    )

    if not startup.documents:
        reporter.fail(
            "RestoMart has no documents."
        )
        return

    if state.baseline_input is None:
        reporter.fail(
            "Baseline input is missing."
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

    reporter.info(
        "profiles_observed",
        len(state.profiles),
    )


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Validate the production RestoMart "
            "Document → InvestmentProfile → "
            "Reconciliation → LLM handshake."
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
        "ENABLED" if run_llm_enabled else "DISABLED",
    )

    reporter.info(
        "analysis mode",
        mode,
    )

    session = create_session()

    try:
        # --------------------------------------------------------------
        # 1. Load startup
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
        # 2. Baseline analysis input
        # --------------------------------------------------------------

        reporter.section(
            "BASELINE ANALYSIS INPUT"
        )

        builder = StartupAnalysisInputBuilder()

        try:
            state = TraceState(
                profiles=[],
                source_facts=[],
                source_conflicts=[],
            )

            state.baseline_input = builder.build(
                startup
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
        # 3. Production document intelligence
        # --------------------------------------------------------------
        #
        # Use the real production factory.
        #
        # The profile_observer is a diagnostic-only hook. It allows this
        # script to observe the InvestmentProfile boundary without
        # reconstructing or bypassing the production dependency graph.
        # --------------------------------------------------------------

        reporter.section(
            "3. PRODUCTION DOCUMENT INTELLIGENCE FACTORY"
        )

    
        def observe_profile(profile: Any) -> None:
            state.profiles.append(profile)

        #Debug 
        def observe_source_facts(
            source_facts: list[SourceValue],
        ) -> None:
            state.source_facts.extend(source_facts)
        
            print()
            print("-" * 88)
            print("C.7.7.7.B.8 — VALUATION SOURCE FACTS ENTERING RECONCILIATION")
            print("-" * 88)
        
            for fact in source_facts:
                if fact.field in {
                    "valuation",
                    "valuation_cap",
                    "pre_money_valuation",
                    "post_money_valuation",
                }:
                    print(
                        f"field={fact.field!r} "
                        f"value={fact.value!r} "
                        f"status={fact.status!r} "
                        f"authority={fact.source_authority!r} "
                        f"source={fact.source_name!r} "
                        f"document={fact.source_document_id!r}"
                    )


        try:
            document_intelligence = (
                StartupAnalysisApplicationService
                .create_startup_analysis_document_intelligence(
                    session,
                    profile_observer=observe_profile,
                    source_facts_observer=observe_source_facts,
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
        # Execute the actual production document-intelligence path.
        # --------------------------------------------------------------

        process_documents_for_observation(
            reporter,
            state,
            startup,
            document_intelligence,
        )

        # --------------------------------------------------------------
        # 4. InvestmentProfile boundary
        # --------------------------------------------------------------

        validate_profiles(
            reporter,
            state,
            startup,
        )

        # --------------------------------------------------------------
        # 5. Source reconciliation
        # --------------------------------------------------------------

        validate_reconciliation(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 6. Baseline → enriched analysis input
        # --------------------------------------------------------------

        validate_baseline_and_enriched_input(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 7. Deterministic financial metrics
        # --------------------------------------------------------------

        calculate_metrics(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 8. Canonical input → production LLM payload
        # --------------------------------------------------------------

        build_llm_payload(
            reporter,
            state,
        )

        # --------------------------------------------------------------
        # 9. Optional real Qwen execution
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
                "8/9. LLM EXECUTION"
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
