"""
Real startup-analysis production E2E validation.

This script validates the complete production startup-analysis path
against a real Qwen GGUF model and a real SQLAlchemy database session.

Flow:

    Startup ORM
        ->
    StartupAnalysisApplicationService
        ->
    StartupService
        ->
    StartupAnalysisOrchestrator
        ->
    StartupAnalysisInputBuilder
        ->
    FinancialMetricsService
        ->
    StartupAnalysisService
        ->
    QwenProvider
        ->
    StartupAnalysisParser
        ->
    StartupAnalysisExecution
        ->
    StartupAnalysisPersistenceService
        ->
    StartupAnalysisMapper
        ->
    StartupAnalysisRepository
        ->
    SQLite database
        ->
    StartupAnalysisHistoryService
        ->
    persisted historical analysis

This is intentionally NOT part of the normal pytest regression suite.

The existing Qwen smoke/benchmark scripts validate model/provider
capability separately. This script validates the production application
integration around that capability.

Usage:

    python -u -m scripts.startup_analysis_real_e2e

or:

    python -u backend/scripts/startup_analysis_real_e2e.py
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models import Base, Founder, Startup
from app.models.enums import (
    FounderRole,
    StartupStage,
    StartupStatus,
)
from app.models.analysis import (
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)
from app.services.startup_analysis_history import (
    StartupAnalysisHistoryService,
)


# =============================================================================
# E2E configuration
# =============================================================================


E2E_STARTUP_NAME = "Real E2E Semiconductor AI"

E2E_STARTUP_DESCRIPTION = (
    "AI-enabled semiconductor startup building "
    "edge inference solutions for surveillance applications."
)

E2E_STARTUP_SECTOR = "Semiconductor"
E2E_STARTUP_INDUSTRY = "AI"
E2E_STARTUP_FOUNDED_YEAR = 2024
E2E_STARTUP_HEADQUARTERS = "Bangalore"

E2E_FOUNDER_NAME = "E2E Founder"
E2E_FOUNDER_EXPERIENCE_YEARS = 15
E2E_FOUNDER_PREVIOUS_COMPANIES = (
    "Company A; Company B"
)

E2E_MODE = StartupAnalysisMode.STANDARD


# =============================================================================
# Database
# =============================================================================


def create_test_engine():
    """
    Create an isolated in-memory SQLite database.

    The pytest database fixture uses the same SQLite/StaticPool strategy.
    This keeps the real application persistence path intact while avoiding
    any dependency on the development database.
    """

    return create_engine(
        "sqlite://",
        future=True,
        echo=False,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )


def create_session(engine) -> Session:
    """Create a SQLAlchemy session bound to the E2E database."""

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

    return session_factory()


# =============================================================================
# Startup fixture
# =============================================================================


def create_real_startup(session: Session) -> Startup:
    """
    Create the real startup aggregate used by the E2E execution.

    This intentionally uses only data currently consumed by
    StartupAnalysisInputBuilder.

    Product, market, financial, fundraising and business-model data are
    not fabricated here because the current input builder intentionally
    leaves those fields unset.
    """

    startup = Startup(
        name=E2E_STARTUP_NAME,
        legal_name=None,
        description=E2E_STARTUP_DESCRIPTION,
        sector=E2E_STARTUP_SECTOR,
        industry=E2E_STARTUP_INDUSTRY,
        stage=StartupStage.IDEA,
        status=StartupStatus.ACTIVE,
        founded_year=E2E_STARTUP_FOUNDED_YEAR,
        website=None,
        headquarters=E2E_STARTUP_HEADQUARTERS,
    )

    session.add(startup)
    session.flush()

    founder = Founder(
        startup=startup,
        full_name=E2E_FOUNDER_NAME,
        designation=FounderRole.CEO,
        experience_years=E2E_FOUNDER_EXPERIENCE_YEARS,
        previous_companies=E2E_FOUNDER_PREVIOUS_COMPANIES,
        education=None,
        notes=None,
        email=None,
    )

    session.add(founder)

    # Commit startup fixture before invoking the application service.
    #
    # StartupAnalysisPersistenceService owns the transaction for the
    # analysis execution itself.
    session.commit()

    session.refresh(startup)

    return startup


# =============================================================================
# Validation helpers
# =============================================================================


def validate_persisted_analysis(
    analysis,
    startup: Startup,
) -> None:
    """
    Validate the persisted StartupAnalysis record.

    These checks deliberately validate structural invariants rather than
    asserting a particular Qwen investment recommendation.
    """

    assert analysis is not None

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    assert analysis.id is not None
    assert analysis.startup_id == startup.id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    assert analysis.status == StartupAnalysisStatus.COMPLETED
    assert analysis.mode == E2E_MODE

    # ------------------------------------------------------------------
    # Execution configuration
    # ------------------------------------------------------------------

    assert analysis.analysis_version
    assert analysis.model_name
    assert analysis.max_tokens > 0
    assert analysis.temperature >= 0.0

    # ------------------------------------------------------------------
    # Real LLM execution metadata
    # ------------------------------------------------------------------

    assert analysis.finish_reason is not None
    assert analysis.prompt_tokens is not None
    assert analysis.completion_tokens is not None
    assert analysis.total_tokens is not None

    assert analysis.prompt_tokens >= 0
    assert analysis.completion_tokens >= 0
    assert analysis.total_tokens >= 0

    # ------------------------------------------------------------------
    # Historical execution artifacts
    # ------------------------------------------------------------------

    assert analysis.input_snapshot is not None
    assert analysis.metrics_snapshot is not None
    assert analysis.result_snapshot is not None

    assert isinstance(
        analysis.input_snapshot,
        dict,
    )

    assert isinstance(
        analysis.metrics_snapshot,
        dict,
    )

    assert isinstance(
        analysis.result_snapshot,
        dict,
    )

    # ------------------------------------------------------------------
    # Input snapshot
    # ------------------------------------------------------------------

    input_snapshot = analysis.input_snapshot

    assert input_snapshot["startup_id"] == str(startup.id)

    assert (
        input_snapshot["company"]["name"]
        == E2E_STARTUP_NAME
    )

    assert (
        input_snapshot["company"]["description"]
        == E2E_STARTUP_DESCRIPTION
    )

    assert (
        input_snapshot["company"]["industry"]
        == E2E_STARTUP_INDUSTRY
    )

    assert (
        input_snapshot["company"]["sector"]
        == E2E_STARTUP_SECTOR
    )

    assert (
        input_snapshot["company"]["founded_year"]
        == E2E_STARTUP_FOUNDED_YEAR
    )

    assert (
        input_snapshot["company"]["headquarters"]
        == E2E_STARTUP_HEADQUARTERS
    )

    # ------------------------------------------------------------------
    # Founder snapshot
    # ------------------------------------------------------------------

    founders = input_snapshot["founders"]

    assert len(founders) == 1

    founder_snapshot = founders[0]

    assert founder_snapshot["name"] == E2E_FOUNDER_NAME
    assert founder_snapshot["role"] == FounderRole.CEO.value

    assert (
        founder_snapshot["relevant_experience"]
        == (
            f"{E2E_FOUNDER_EXPERIENCE_YEARS} years experience; "
            f"Previous companies: "
            f"{E2E_FOUNDER_PREVIOUS_COMPANIES}"
        )
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    assert analysis.created_at is not None
    assert analysis.updated_at is not None


def validate_history_round_trip(
    history_service: StartupAnalysisHistoryService,
    startup: Startup,
    analysis,
) -> None:
    """
    Verify that the persisted analysis can be recovered through the
    production history service.
    """

    # ------------------------------------------------------------------
    # List history
    # ------------------------------------------------------------------

    items, total_items = history_service.list_history(
        startup.id,
        page=1,
        per_page=20,
    )

    assert total_items == 1
    assert len(items) == 1

    history_item = items[0]

    assert history_item.id == analysis.id
    assert history_item.startup_id == startup.id
    assert history_item.mode == E2E_MODE
    assert history_item.status == StartupAnalysisStatus.COMPLETED

    # ------------------------------------------------------------------
    # Detail lookup
    # ------------------------------------------------------------------

    historical = history_service.get_history(
        startup.id,
        analysis.id,
    )

    assert historical is not None

    assert historical.id == analysis.id
    assert historical.startup_id == startup.id

    # ------------------------------------------------------------------
    # Snapshot identity
    # ------------------------------------------------------------------

    assert historical.input_snapshot == (
        analysis.input_snapshot
    )

    assert historical.metrics_snapshot == (
        analysis.metrics_snapshot
    )

    assert historical.result_snapshot == (
        analysis.result_snapshot
    )


# =============================================================================
# Output
# =============================================================================


def print_header() -> None:
    """Print E2E configuration."""

    print("=" * 80)
    print("REAL STARTUP ANALYSIS E2E")
    print("=" * 80)

    print(f"Model path       : {settings.qwen_model_path}")
    print(f"Qwen threads     : {settings.qwen_threads}")
    print(f"Context size     : {settings.qwen_context_size}")
    print(
        f"Thinking         : "
        f"{settings.qwen_enable_thinking}"
    )
    print(
        f"Max tokens       : "
        f"{settings.startup_analysis_max_tokens}"
    )
    print(
        f"Temperature      : "
        f"{settings.startup_analysis_temperature}"
    )
    print(f"Analysis mode    : {E2E_MODE.value}")

    print()
    print(f"Startup          : {E2E_STARTUP_NAME}")
    print(f"Founder          : {E2E_FOUNDER_NAME}")
    print()


def print_analysis_summary(analysis) -> None:
    """Print a compact successful-analysis summary."""

    print()
    print("-" * 80)
    print("PERSISTED ANALYSIS")
    print("-" * 80)

    print(f"Analysis ID      : {analysis.id}")
    print(f"Startup ID       : {analysis.startup_id}")
    print(f"Status           : {analysis.status.value}")
    print(f"Mode             : {analysis.mode.value}")
    print(f"Model            : {analysis.model_name}")
    print(f"Thinking         : {analysis.thinking_enabled}")
    print(f"Max tokens       : {analysis.max_tokens}")
    print(f"Temperature      : {analysis.temperature}")

    print()
    print("LLM metadata:")
    print(f"  Finish reason  : {analysis.finish_reason}")
    print(f"  Prompt tokens  : {analysis.prompt_tokens}")
    print(
        f"  Completion     : "
        f"{analysis.completion_tokens}"
    )
    print(f"  Total tokens   : {analysis.total_tokens}")

    print()
    print("Artifacts:")
    print(
        f"  Input snapshot   : "
        f"{'YES' if analysis.input_snapshot else 'NO'}"
    )
    print(
        f"  Metrics snapshot : "
        f"{'YES' if analysis.metrics_snapshot else 'NO'}"
    )
    print(
        f"  Result snapshot  : "
        f"{'YES' if analysis.result_snapshot else 'NO'}"
    )

    if analysis.recommendation is not None:
        print(
            f"  Recommendation   : "
            f"{analysis.recommendation}"
        )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Run the complete real startup-analysis E2E validation."""

    print_header()

    model_path = Path(
        settings.qwen_model_path,
    )

    if not model_path.exists():
        print()
        print("ERROR: Qwen model file does not exist.")
        print(f"       {model_path}")
        print()
        return 1

    engine = create_test_engine()

    try:
        # --------------------------------------------------------------
        # Database schema
        # --------------------------------------------------------------

        print("-" * 80)
        print("Creating E2E database")
        print("-" * 80)

        Base.metadata.create_all(engine)

        session = create_session(engine)

        try:
            # ----------------------------------------------------------
            # Real startup fixture
            # ----------------------------------------------------------

            print()
            print("-" * 80)
            print("Creating startup fixture")
            print("-" * 80)

            startup = create_real_startup(session)

            print(f"Startup ID       : {startup.id}")

            # ----------------------------------------------------------
            # Production application service
            # ----------------------------------------------------------

            print()
            print("-" * 80)
            print("Running production startup analysis")
            print("-" * 80)

            print()
            print(
                "IMPORTANT: This invokes the real Qwen GGUF model."
            )
            print()

            analysis_start = time.perf_counter()

            application_service = (
                StartupAnalysisApplicationService(
                    session=session,
                )
            )

            analysis = application_service.analyze(
                startup_id=startup.id,
                mode=E2E_MODE,
            )

            analysis_elapsed = (
                time.perf_counter()
                - analysis_start
            )

            print(
                f"Analysis time    : "
                f"{analysis_elapsed:.2f} sec"
            )

            # ----------------------------------------------------------
            # Persistence validation
            # ----------------------------------------------------------

            print()
            print("-" * 80)
            print("Validating persisted analysis")
            print("-" * 80)

            validate_persisted_analysis(
                analysis,
                startup,
            )

            print("Persistence validation: PASS")

            print_analysis_summary(analysis)

            # ----------------------------------------------------------
            # History validation
            # ----------------------------------------------------------

            print()
            print("-" * 80)
            print("Validating analysis history")
            print("-" * 80)

            repository = StartupAnalysisRepository(
                session,
            )

            history_service = (
                StartupAnalysisHistoryService(
                    repository=repository,
                )
            )

            validate_history_round_trip(
                history_service,
                startup,
                analysis,
            )

            print("History round-trip: PASS")

            # ----------------------------------------------------------
            # Final validation
            # ----------------------------------------------------------

            print()
            print("=" * 80)
            print("REAL STARTUP ANALYSIS E2E: PASS")
            print("=" * 80)

            print()
            print("Validated:")
            print("  [PASS] Real Startup ORM")
            print("  [PASS] StartupAnalysisApplicationService")
            print("  [PASS] StartupAnalysisOrchestrator")
            print("  [PASS] AnalysisInputBuilder")
            print("  [PASS] FinancialMetricsService")
            print("  [PASS] Real QwenProvider")
            print("  [PASS] StartupAnalysisParser")
            print("  [PASS] StartupAnalysisExecution")
            print("  [PASS] StartupAnalysisPersistenceService")
            print("  [PASS] StartupAnalysisMapper")
            print("  [PASS] StartupAnalysisRepository")
            print("  [PASS] Persisted execution artifacts")
            print("  [PASS] StartupAnalysisHistoryService")
            print()

            return 0

        finally:
            session.close()

    except Exception as exc:
        print()
        print("=" * 80)
        print("REAL STARTUP ANALYSIS E2E: FAILED")
        print("=" * 80)
        print()
        print(
            f"Exception type   : "
            f"{type(exc).__name__}"
        )
        print(
            f"Exception        : "
            f"{exc}"
        )

        print()
        print("Traceback:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)

        return 1

    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
