"""
Production startup source extraction runner.

Runs the normal cache-aware source extraction flow for every
source discovered under a startup's source directory.

The runner resolves the user-facing startup key/name to the
canonical persisted Startup UUID before source discovery.

Flow:

    CLI startup key/name
        ->
    StartupService
        ->
    canonical Startup.id
        ->
    SourceDiscoveryService
        ->
    SourceExtractionOrchestrator.extract_with_result()
        ->
    persisted SourceExtraction

The runner intentionally uses the existing production
SourceDiscoveryService and SourceExtractionOrchestrator.

It does not directly invoke document processors or OCR.

Exit codes:

    0  All discovered sources processed successfully.
    1  One or more sources failed or batch is incomplete.
    2  Invalid command-line/configuration error.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.core.database.session import create_session
from app.models.source_document import SourceDocument
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_orchestrator import (
    SourceExtractionOrchestrator,
)
from app.services.startup import StartupService


# =============================================================================
# Result
# =============================================================================


@dataclass(slots=True)
class BatchStats:
    """Runtime statistics for one startup extraction run."""

    total: int = 0
    success: int = 0
    failed: int = 0

    cache_hits: int = 0
    extracted: int = 0

    native: int = 0
    ocr: int = 0

    def record_success(
        self,
        *,
        cached: bool,
        method: str | None,
    ) -> None:
        """Record a successful extraction."""

        self.success += 1

        if cached:
            self.cache_hits += 1
        else:
            self.extracted += 1

        if method == "native":
            self.native += 1
        elif method == "ocr":
            self.ocr += 1

    def record_failure(self) -> None:
        """Record a failed extraction."""

        self.failed += 1


# =============================================================================
# Argument parsing
# =============================================================================


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Run production source extraction for all sources "
            "discovered under a startup."
        ),
    )

    parser.add_argument(
        "--startup",
        "--startup-id",
        dest="startup",
        required=True,
        help=(
            "Startup key, name, or UUID. "
            "Example: restomart"
        ),
    )

    parser.add_argument(
        "--source-root",
        required=False,
        type=Path,
        default=None,
        help=(
            "Optional root directory containing startup source files. "
            "If omitted, it is derived from the configured "
            "real_startups_root and the startup name."
        ),
    )

    return parser


# =============================================================================
# Startup resolution
# =============================================================================


def _normalize_startup_key(value: str) -> str:
    """
    Normalize a user-facing startup key.

    This normalization is intentionally limited to startup lookup.
    It must NOT be used as the persisted source identity.
    """

    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def resolve_startup(
    *,
    startup_service: StartupService,
    startup_reference: str,
):
    """
    Resolve a CLI startup reference to the persisted Startup.

    Supported forms:

        restomart
        RestoMart
        resto-mart
        <startup UUID>

    The returned Startup object is the authoritative source for:

        startup.id
        startup.name
    """

    reference = startup_reference.strip()

    if not reference:
        raise ValueError(
            "--startup must not be empty."
        )

    # -------------------------------------------------------------------------
    # Exact UUID lookup
    # -------------------------------------------------------------------------

    try:
        startup_uuid = UUID(reference)
    except ValueError:
        startup_uuid = None

    if startup_uuid is not None:
        startup = startup_service.get_startup(startup_uuid)

        if startup is None:
            raise ValueError(
                f"Startup not found for UUID: {startup_uuid}"
            )

        return startup

    # -------------------------------------------------------------------------
    # User-facing name/key lookup
    # -------------------------------------------------------------------------

    normalized_reference = _normalize_startup_key(reference)

    startups = startup_service.list_startups()

    matches = []

    for startup in startups:
        normalized_name = _normalize_startup_key(
            startup.name
        )

        if normalized_name == normalized_reference:
            matches.append(startup)

    if not matches:
        raise ValueError(
            f"Startup not found: {startup_reference}"
        )

    if len(matches) > 1:
        names = ", ".join(
            f"{startup.name} ({startup.id})"
            for startup in matches
        )

        raise ValueError(
            "Startup reference is ambiguous: "
            f"{startup_reference}. Matches: {names}"
        )

    return matches[0]


# =============================================================================
# Source-root resolution
# =============================================================================


def resolve_source_root(
    *,
    startup_name: str,
    explicit_source_root: Path | None,
) -> Path:
    """
    Resolve the source directory for the persisted startup.

    An explicitly supplied source root is honored.

    Otherwise:

        settings.real_startups_root
            /
        normalized startup name
            /
        sources
    """

    if explicit_source_root is not None:
        return explicit_source_root.resolve()

    startup_key = _normalize_startup_key(
        startup_name
    )

    root = (
        Path(settings.real_startups_root)
        / startup_key
        / "sources"
    )

    return root.resolve()


# =============================================================================
# Validation
# =============================================================================


def validate_source_root(
    *,
    source_root: Path,
) -> None:
    """Validate the source directory."""

    if not source_root.exists():
        raise ValueError(
            f"Source root does not exist: {source_root}"
        )

    if not source_root.is_dir():
        raise ValueError(
            f"Source root is not a directory: {source_root}"
        )


# =============================================================================
# Source extraction
# =============================================================================


def extract_sources(
    *,
    startup_id: str,
    source_root: Path,
    orchestrator: SourceExtractionOrchestrator,
) -> BatchStats:
    """
    Extract all discovered sources.

    A failure in one source is isolated so that processing continues
    for the remaining sources.
    """

    discovery = SourceDiscoveryService()

    sources = discovery.discover(
        startup_id=startup_id,
        source_root=source_root,
    )

    stats = BatchStats(
        total=len(sources),
    )

    print()
    print("=" * 100)
    print("PRODUCTION SOURCE EXTRACTION")
    print("=" * 100)
    print("CANONICAL STARTUP UUID :", startup_id)
    print("SOURCE ROOT            :", source_root)
    print("SOURCES                :", len(sources))
    print()

    if not sources:
        print("No sources discovered.")
        print()
        print("BATCH STATUS: PASS")
        return stats

    for index, source in enumerate(
        sources,
        start=1,
    ):
        _process_source(
            index=index,
            total=len(sources),
            source=source,
            source_root=source_root,
            orchestrator=orchestrator,
            stats=stats,
        )

    return stats


def _process_source(
    *,
    index: int,
    total: int,
    source: SourceDocument,
    source_root: Path,
    orchestrator: SourceExtractionOrchestrator,
    stats: BatchStats,
) -> None:
    """Process one source and isolate failures."""

    print(
        "-" * 100,
        flush=True,
    )

    print(
        f"[BATCH] {index}/{total} "
        f"file={source.filename}",
        flush=True,
    )

    print(
        f"[BATCH] path={source.relative_path}",
        flush=True,
    )

    print(
        f"[BATCH] source_id={source.source_id}",
        flush=True,
    )

    print(
        f"[BATCH] sha256={source.sha256}",
        flush=True,
    )

    try:
        execution = orchestrator.extract_with_result(
            source=source,
            source_root=source_root,
        )

        result = execution.record
        cached = execution.cached
        method = result.provenance.method.value

        stats.record_success(
            cached=cached,
            method=method,
        )

        if cached:
            print(
                f"[BATCH] CACHE_HIT "
                f"file={source.filename}",
                flush=True,
            )
        else:
            print(
                f"[BATCH] EXTRACTED "
                f"file={source.filename}",
                flush=True,
            )

        print(
            f"[BATCH] method={method} "
            f"text_chars={len(result.text)} "
            f"segments={len(result.segments)} "
            f"quality={result.quality.value}",
            flush=True,
        )

        if result.provenance.fallback_used:
            print(
                "[BATCH] fallback="
                f"{result.provenance.fallback_reason}",
                flush=True,
            )

        print(
            "[BATCH] PASS",
            flush=True,
        )

    except Exception as exc:
        stats.record_failure()

        print(
            f"[BATCH] FAILED file={source.filename}",
            flush=True,
        )

        print(
            f"[BATCH] error={type(exc).__name__}: {exc}",
            flush=True,
        )


# =============================================================================
# Summary
# =============================================================================


def print_summary(
    *,
    startup_name: str,
    startup_id: str,
    source_root: Path,
    stats: BatchStats,
) -> None:
    """Print the final batch summary."""

    print()
    print("=" * 100)
    print("PRODUCTION SOURCE EXTRACTION SUMMARY")
    print("=" * 100)

    print("STARTUP NAME :", startup_name)
    print("STARTUP UUID :", startup_id)
    print("SOURCE ROOT  :", source_root)
    print()

    print("TOTAL        :", stats.total)
    print("SUCCESS      :", stats.success)
    print("FAILED       :", stats.failed)
    print()

    print("CACHE HIT    :", stats.cache_hits)
    print("EXTRACTED    :", stats.extracted)
    print()

    print("NATIVE       :", stats.native)
    print("OCR          :", stats.ocr)

    if stats.total:
        success_rate = (
            stats.success / stats.total
        ) * 100.0
    else:
        success_rate = 100.0

    print(
        f"SUCCESS RATE : {success_rate:.1f}%"
    )

    print()

    if stats.failed == 0 and stats.success == stats.total:
        print("BATCH STATUS : PASS")
    else:
        print(
            "BATCH STATUS : "
            "COMPLETED_WITH_FAILURES"
        )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Application entry point."""

    parser = build_argument_parser()
    args = parser.parse_args()

    session = None

    try:
        # ---------------------------------------------------------------------
        # Database
        # ---------------------------------------------------------------------

        session = create_session()

        startup_service = StartupService(
            session=session,
        )

        # ---------------------------------------------------------------------
        # Resolve startup
        # ---------------------------------------------------------------------

        startup = resolve_startup(
            startup_service=startup_service,
            startup_reference=args.startup,
        )

        canonical_startup_id = str(startup.id)

        # ---------------------------------------------------------------------
        # Resolve source root
        # ---------------------------------------------------------------------

        source_root = resolve_source_root(
            startup_name=startup.name,
            explicit_source_root=args.source_root,
        )

        validate_source_root(
            source_root=source_root,
        )

        # ---------------------------------------------------------------------
        # Runtime identity
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("SOURCE EXTRACTION RUN")
        print("=" * 100)

        print(
            "STARTUP REFERENCE :",
            args.startup,
        )

        print(
            "PERSISTED STARTUP :",
            startup.name,
        )

        print(
            "CANONICAL UUID    :",
            canonical_startup_id,
        )

        print(
            "SOURCE ROOT       :",
            source_root,
        )

        print()

        # ---------------------------------------------------------------------
        # Production orchestrator
        # ---------------------------------------------------------------------

        orchestrator = SourceExtractionOrchestrator(
            session=session,
        )

        # ---------------------------------------------------------------------
        # Extract all sources
        # ---------------------------------------------------------------------

        stats = extract_sources(
            startup_id=canonical_startup_id,
            source_root=source_root,
            orchestrator=orchestrator,
        )

        # ---------------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------------

        print_summary(
            startup_name=startup.name,
            startup_id=canonical_startup_id,
            source_root=source_root,
            stats=stats,
        )

        # ---------------------------------------------------------------------
        # Transaction handling
        # ---------------------------------------------------------------------

        if stats.failed == 0:
            session.commit()
            return 0

        session.rollback()
        return 1

    except ValueError as exc:
        if session is not None:
            session.rollback()

        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )

        return 2

    except Exception as exc:
        if session is not None:
            session.rollback()

        print(
            "=" * 100,
            file=sys.stderr,
        )

        print(
            "PRODUCTION SOURCE EXTRACTION FAILED",
            file=sys.stderr,
        )

        print(
            "=" * 100,
            file=sys.stderr,
        )

        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
