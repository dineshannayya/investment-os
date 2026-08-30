"""
Startup Analysis production regression runner.

Default:
    Deterministic application regression only.
    No Qwen inference is executed.

Optional:
    --real-qwen
        Execute real Qwen STANDARD and DEEP analyses against RestoMart
        through StartupAnalysisApplicationService.

Design:
    - Uses the production application/orchestrator path.
    - Does not require pre-existing persisted analyses.
    - Does not create persistent test data in the default path.
    - Validates document-intelligence enrichment and prompt-budget contracts.
    - Optionally validates real Qwen generation + persistence.

This is the canonical 3.7.5 startup-analysis regression entry point.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from app.core.database.session import create_session
from app.models.analysis import StartupAnalysisMode
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)
from app.services.startup_analysis_config import (
    get_startup_analysis_config,
)
import app.prompt.startup_analysis as prompt


# ---------------------------------------------------------------------------
# Regression identity
# ---------------------------------------------------------------------------

RESTOMART_STARTUP_ID = UUID(
    "dbb520d7-0979-4db3-8464-523f5710455f"
)

EXPECTED_VERSION = "3.7.5"
EXPECTED_MODEL = "qwen3-8b-q4"
EXPECTED_CONTEXT = 8192

EXPECTED_STANDARD_MAX_TOKENS = 768
EXPECTED_DEEP_MAX_TOKENS = 2048

MAX_PAYLOAD_CHARS = prompt.MAX_STARTUP_PAYLOAD_CHARS
MAX_EVIDENCE_ITEMS = prompt.MAX_EVIDENCE_ITEMS
MAX_EVIDENCE_CHARS = prompt.MAX_EVIDENCE_CHARS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def check(condition: bool, message: str) -> None:
    """Raise AssertionError when a regression contract fails."""
    if not condition:
        raise AssertionError(message)


def get_restomart(application):
    """Resolve the known RestoMart startup."""
    startup = next(
        (
            item
            for item in application._startup_service.list_startups()
            if item.id == RESTOMART_STARTUP_ID
        ),
        None,
    )

    check(
        startup is not None,
        f"RestoMart startup not found: {RESTOMART_STARTUP_ID}",
    )

    return startup


# ---------------------------------------------------------------------------
# 1. Configuration regression
# ---------------------------------------------------------------------------


def test_configuration() -> None:
    print("[PASS] Configuration")

    session = create_session()

    try:
        application = StartupAnalysisApplicationService(
            session=session,
        )

        orchestrator = application._orchestrator

        startup = get_restomart(application)

        check(
            startup.name.strip().lower() == "restomart",
            "Resolved startup is not RestoMart",
        )

        for mode in (
            StartupAnalysisMode.STANDARD,
            StartupAnalysisMode.DEEP,
        ):
            config = get_startup_analysis_config(mode)

            check(
                config.model_name == EXPECTED_MODEL,
                f"{mode.value}: unexpected model "
                f"{config.model_name}",
            )

            check(
                config.analysis_version == EXPECTED_VERSION,
                f"{mode.value}: unexpected analysis version "
                f"{config.analysis_version}",
            )

            check(
                config.temperature == 0.0,
                f"{mode.value}: temperature must be 0.0",
            )

            if mode == StartupAnalysisMode.STANDARD:
                check(
                    config.thinking_enabled is False,
                    "STANDARD thinking must be disabled",
                )

                check(
                    config.max_tokens == EXPECTED_STANDARD_MAX_TOKENS,
                    "STANDARD max_tokens mismatch",
                )

            else:
                check(
                    config.thinking_enabled is True,
                    "DEEP thinking must be enabled",
                )

                check(
                    config.max_tokens == EXPECTED_DEEP_MAX_TOKENS,
                    "DEEP max_tokens mismatch",
                )


    finally:
        session.close()


# ---------------------------------------------------------------------------
# 2. Document intelligence / prompt regression
# ---------------------------------------------------------------------------


def build_enriched_input(application, startup):
    """
    Build the same enriched StartupAnalysisInput used by production
    orchestration.
    """

    source_extractions = (
        application._load_current_source_extractions(
            startup,
        )
    )

    check(
        len(source_extractions) > 0,
        "No source extractions found for RestoMart",
    )

    orchestrator = application._orchestrator

    base_input = orchestrator._input_builder.build(
        startup,
    )

    enriched_input = (
        orchestrator._document_intelligence_service.enrich(
            startup=startup,
            analysis_input=base_input,
            source_extractions=source_extractions,
        )
    )

    return enriched_input, source_extractions


def test_document_enrichment_and_prompt_budget() -> None:
    print("[PASS] Document enrichment / prompt budget")

    session = create_session()

    try:
        application = StartupAnalysisApplicationService(
            session=session,
        )

        startup = get_restomart(application)

        enriched_input, source_extractions = (
            build_enriched_input(
                application,
                startup,
            )
        )

        check(
            len(source_extractions) > 0,
            "Expected at least one source extraction",
        )

        check(
            len(enriched_input.evidence) > 0,
            "Expected canonical evidence records",
        )

        metrics = FinancialMetricsService.calculate(
            financials=enriched_input.financials,
            fundraising=enriched_input.fundraising,
            business_model=enriched_input.business_model,
        )

        messages = prompt.build_startup_analysis_messages(
            enriched_input,
            metrics,
        )

        check(
            len(messages) == 2,
            "Expected system + user messages",
        )

        user_message = messages[1]

        payload_chars = len(user_message.content)

        check(
            payload_chars <= MAX_PAYLOAD_CHARS,
            (
                "Final user prompt exceeds configured payload budget: "
                f"{payload_chars} > {MAX_PAYLOAD_CHARS}"
            ),
        )

        projected = prompt._build_input_payload(
            enriched_input,
            metrics,
        )

        serialized_chars = len(
            json.dumps(
                projected,
                ensure_ascii=False,
            )
        )

        check(
            serialized_chars <= MAX_PAYLOAD_CHARS,
            (
                "Prompt payload exceeds configured budget: "
                f"{serialized_chars} > {MAX_PAYLOAD_CHARS}"
            ),
        )

        selected_evidence = projected["startup"]["evidence"]

        check(
            len(selected_evidence) <= MAX_EVIDENCE_ITEMS,
            (
                "Evidence item budget exceeded: "
                f"{len(selected_evidence)} > "
                f"{MAX_EVIDENCE_ITEMS}"
            ),
        )

        evidence_chars = len(
            json.dumps(
                selected_evidence,
                ensure_ascii=False,
            )
        )

        check(
            evidence_chars <= MAX_EVIDENCE_CHARS,
            (
                "Evidence character budget exceeded: "
                f"{evidence_chars} > {MAX_EVIDENCE_CHARS}"
            ),
        )

        print(
            f"       source extractions : {len(source_extractions)}"
        )
        print(
            f"       canonical evidence : {len(enriched_input.evidence)}"
        )
        print(
            f"       selected evidence  : {len(selected_evidence)}"
        )
        print(
            f"       payload chars      : {serialized_chars}"
        )
        print(
            f"       payload budget     : {MAX_PAYLOAD_CHARS}"
        )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# 3. Financial metrics regression
# ---------------------------------------------------------------------------


def test_financial_metrics() -> None:
    print("[PASS] Financial metrics")

    session = create_session()

    try:
        application = StartupAnalysisApplicationService(
            session=session,
        )

        startup = get_restomart(application)

        enriched_input, _ = build_enriched_input(
            application,
            startup,
        )

        metrics = FinancialMetricsService.calculate(
            financials=enriched_input.financials,
            fundraising=enriched_input.fundraising,
            business_model=enriched_input.business_model,
        )

        check(
            metrics is not None,
            "FinancialMetricsService returned None",
        )

        # Structural contract rather than startup-specific numerical values.
        for name in (
            "revenue_multiple",
            "ebitda_multiple",
            "valuation_to_growth",
        ):
            check(
                hasattr(metrics, name),
                f"Missing financial metric: {name}",
            )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# 4. Persistence / history contract
# ---------------------------------------------------------------------------


def test_persistence_contract() -> None:
    """
    Validate repository/history structure without requiring an existing
    Standard or Deep analysis.

    The regression must work against a fresh database.
    """

    print("[PASS] Persistence / history contract")

    session = create_session()

    try:
        repository = StartupAnalysisRepository(
            session,
        )

        history, total = repository.list_by_startup(
            RESTOMART_STARTUP_ID,
            page=1,
            per_page=20,
        )

        check(
            total >= 0,
            "Invalid history total",
        )

        check(
            len(history) <= 20,
            "History pagination contract violated",
        )

        for item in history:
            check(
                item.startup_id == RESTOMART_STARTUP_ID,
                "History item belongs to another startup",
            )

            check(
                item.analysis_version is not None,
                "History item missing analysis_version",
            )

            check(
                item.model_name is not None,
                "History item missing model_name",
            )

            check(
                item.status is not None,
                "History item missing status",
            )

        print(
            f"       existing history records : {total}"
        )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# 5. Real Qwen regression
# ---------------------------------------------------------------------------


def validate_real_analysis(
    analysis,
    mode: StartupAnalysisMode,
) -> None:
    """Validate one persisted real-Qwen analysis."""

    check(
        analysis is not None,
        f"{mode.value}: analysis is None",
    )

    check(
        analysis.analysis_version == EXPECTED_VERSION,
        f"{mode.value}: analysis version mismatch",
    )

    check(
        analysis.mode == mode,
        f"{mode.value}: mode mismatch",
    )

    check(
        analysis.status.value == "completed",
        f"{mode.value}: analysis not completed",
    )

    check(
        analysis.model_name == EXPECTED_MODEL,
        f"{mode.value}: model mismatch",
    )

    check(
        analysis.temperature == 0.0,
        f"{mode.value}: temperature mismatch",
    )

    check(
        analysis.finish_reason == "stop",
        (
            f"{mode.value}: expected finish_reason='stop', "
            f"got {analysis.finish_reason!r}"
        ),
    )

    check(
        analysis.prompt_tokens is not None,
        f"{mode.value}: missing prompt_tokens",
    )

    check(
        analysis.completion_tokens is not None,
        f"{mode.value}: missing completion_tokens",
    )

    check(
        analysis.total_tokens is not None,
        f"{mode.value}: missing total_tokens",
    )

    check(
        analysis.total_tokens
        == analysis.prompt_tokens
        + analysis.completion_tokens,
        f"{mode.value}: token accounting mismatch",
    )

    check(
        isinstance(analysis.input_snapshot, dict),
        f"{mode.value}: missing input_snapshot",
    )

    check(
        isinstance(analysis.metrics_snapshot, dict),
        f"{mode.value}: missing metrics_snapshot",
    )

    check(
        isinstance(analysis.result_snapshot, dict),
        f"{mode.value}: missing result_snapshot",
    )

    if mode == StartupAnalysisMode.STANDARD:
        check(
            analysis.thinking_enabled is False,
            "STANDARD thinking mismatch",
        )

        check(
            analysis.max_tokens == EXPECTED_STANDARD_MAX_TOKENS,
            "STANDARD max_tokens mismatch",
        )

    else:
        check(
            analysis.thinking_enabled is True,
            "DEEP thinking mismatch",
        )

        check(
            analysis.max_tokens == EXPECTED_DEEP_MAX_TOKENS,
            "DEEP max_tokens mismatch",
        )


def run_real_qwen() -> None:
    print()
    print("=" * 100)
    print("REAL QWEN REGRESSION")
    print("=" * 100)

    session = create_session()

    try:
        application = StartupAnalysisApplicationService(
            session=session,
        )

        startup = get_restomart(application)

        for mode in (
            StartupAnalysisMode.STANDARD,
            StartupAnalysisMode.DEEP,
        ):
            print()
            print(
                f"Running real Qwen: {mode.value.upper()}"
            )
            print("-" * 80)

            analysis = application.analyze(
                startup_id=startup.id,
                mode=mode,
            )

            validate_real_analysis(
                analysis,
                mode,
            )

            print(
                f"[PASS] {mode.value.upper()} "
                f"analysis_id={analysis.id} "
                f"prompt={analysis.prompt_tokens} "
                f"completion={analysis.completion_tokens} "
                f"total={analysis.total_tokens}"
            )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Startup Analysis 3.7.5 production regression."
        )
    )

    parser.add_argument(
        "--real-qwen",
        action="store_true",
        help=(
            "Run real Qwen STANDARD + DEEP analyses "
            "against RestoMart."
        ),
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    print("=" * 100)
    print("STARTUP ANALYSIS 3.7.5 REGRESSION")
    print("=" * 100)
    print()
    print("Startup : RestoMart")
    print(f"Version : {EXPECTED_VERSION}")
    print(f"Model   : {EXPECTED_MODEL}")
    print()

    try:
        test_configuration()
        test_document_enrichment_and_prompt_budget()
        test_financial_metrics()
        test_persistence_contract()

        if args.real_qwen:
            run_real_qwen()

    except Exception as exc:
        print()
        print("=" * 100)
        print("STARTUP ANALYSIS REGRESSION: FAIL")
        print("=" * 100)
        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print()

        return 1

    print()
    print("=" * 100)

    if args.real_qwen:
        print(
            "STARTUP ANALYSIS 3.7.5 REGRESSION: PASS "
            "(INCLUDING REAL QWEN)"
        )
    else:
        print(
            "STARTUP ANALYSIS 3.7.5 REGRESSION: PASS"
        )

    print("=" * 100)

    return 0


if __name__ == "__main__":
    sys.exit(main())
