"""
Production startup source extraction runner.

Runs the normal cache-aware source extraction flow for every
source discovered under a startup's source directory.

Usage:

    python scripts/extract_startup_sources.py \
        --startup-id restomart \
        --source-root /opt/investment-os/data/real_startups/restomart/sources

The script intentionally uses:

    SourceDiscoveryService
        ->
    SourceExtractionOrchestrator.extract()

It does not directly invoke document processors or OCR.

Exit codes:

    0  All sources processed successfully.
    1  One or more sources failed.
    2  Invalid command-line/configuration error.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.database.session import create_session
from app.models.source_document import SourceDocument
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_orchestrator import (
    SourceExtractionOrchestrator,
)


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
        "--startup-id",
        required=True,
        help="Startup identifier, for example: restomart",
    )

    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Root directory containing startup source files.",
    )

    return parser


# =============================================================================
# Validation
# =============================================================================


def validate_arguments(
    *,
    startup_id: str,
    source_root: Path,
) -> None:
    """Validate command-line inputs."""

    if not startup_id.strip():
        raise ValueError(
            "--startup-id must not be empty."
        )

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
    print("STARTUP     :", startup_id)
    print("SOURCE ROOT :", source_root)
    print("SOURCES     :", len(sources))
    print()

    if not sources:
        print("No sources discovered.")
        print()
        print("BATCH STATUS : PASS")
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
        f"[BATCH] sha256={source.sha256}",
        flush=True,
    )

    try:
        execution = orchestrator.extract_with_result(
            source=source,
            source_root=source_root,
        )

        # The orchestrator owns cache behavior and explicitly reports the
        # request outcome. Do not infer cache state from persisted provenance.
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
    startup_id: str,
    source_root: Path,
    stats: BatchStats,
) -> None:
    """Print the final batch summary."""

    print()
    print("=" * 100)
    print("PRODUCTION SOURCE EXTRACTION SUMMARY")
    print("=" * 100)

    print("STARTUP     :", startup_id)
    print("SOURCE ROOT :", source_root)
    print()
    print("TOTAL       :", stats.total)
    print("SUCCESS     :", stats.success)
    print("FAILED      :", stats.failed)
    print()
    print("CACHE HIT   :", stats.cache_hits)
    print("EXTRACTED   :", stats.extracted)
    print()
    print("NATIVE      :", stats.native)
    print("OCR         :", stats.ocr)

    if stats.total:
        success_rate = (
            stats.success / stats.total
        ) * 100.0
    else:
        success_rate = 100.0

    print(
        f"SUCCESS RATE: {success_rate:.1f}%"
    )

    print()

    if stats.failed == 0:
        print("BATCH STATUS: PASS")
    else:
        print(
            "BATCH STATUS: "
            "COMPLETED_WITH_FAILURES"
        )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Application entry point."""

    parser = build_argument_parser()
    args = parser.parse_args()

    startup_id = args.startup_id
    source_root = args.source_root.resolve()

    try:
        validate_arguments(
            startup_id=startup_id,
            source_root=source_root,
        )

    except ValueError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    session = create_session()

    try:
        orchestrator = SourceExtractionOrchestrator(
            session=session,
        )

        stats = extract_sources(
            startup_id=startup_id,
            source_root=source_root,
            orchestrator=orchestrator,
        )

        print_summary(
            startup_id=startup_id,
            source_root=source_root,
            stats=stats,
        )

        return 0 if stats.failed == 0 else 1

    except Exception as exc:
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
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
