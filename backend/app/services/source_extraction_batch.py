"""
Production source extraction batch service.

Runs normal cache-aware extraction across all discovered sources
for a startup.

Responsibilities:
    - Iterate discovered SourceDocument objects.
    - Invoke SourceExtractionOrchestrator.extract().
    - Isolate failures per source.
    - Produce a deterministic batch summary.

Non-responsibilities:
    - Source discovery.
    - File hashing.
    - Native extraction.
    - OCR.
    - Persistence implementation.
    - Refresh/re-extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.models.source_document import SourceDocument
from app.models.source_extraction_record import (
    ExtractionMethod,
    SourceExtractionRecord,
)
from app.services.source_extraction_orchestrator import (
    SourceExtractionOrchestrator,
)


@dataclass(slots=True)
class SourceExtractionBatchItem:
    """Result for one source."""

    source: SourceDocument

    success: bool

    cached: bool = False

    extraction: SourceExtractionRecord | None = None

    error: str | None = None


@dataclass(slots=True)
class SourceExtractionBatchResult:
    """Aggregate result of a source extraction batch."""

    startup_id: str

    total: int = 0
    successful: int = 0
    failed: int = 0
    cache_hits: int = 0
    extracted: int = 0

    native: int = 0
    ocr: int = 0

    items: list[SourceExtractionBatchItem] = field(
        default_factory=list,
    )

    @property
    def success_rate(self) -> float:
        """Return successful extraction percentage."""

        if self.total == 0:
            return 100.0

        return (
            self.successful / self.total
        ) * 100.0


class SourceExtractionBatchService:
    """
    Production batch coordinator for source extraction.

    The service deliberately uses the normal orchestrator.extract()
    path. It does not use refresh().
    """

    def __init__(
        self,
        *,
        orchestrator: SourceExtractionOrchestrator,
    ) -> None:
        self._orchestrator = orchestrator

    def extract_all(
        self,
        *,
        startup_id: str,
        sources: list[SourceDocument],
        source_root: Path,
    ) -> SourceExtractionBatchResult:
        """
        Extract all supplied sources.

        A failure for one source does not stop processing of
        subsequent sources.
        """

        result = SourceExtractionBatchResult(
            startup_id=startup_id,
        )

        result.total = len(sources)

        print()
        print("=" * 100)
        print("SOURCE EXTRACTION BATCH")
        print("=" * 100)
        print("STARTUP :", startup_id)
        print("SOURCES :", len(sources))
        print()

        for index, source in enumerate(
            sources,
            start=1,
        ):
            print(
                f"[BATCH] {index}/{len(sources)} "
                f"file={source.filename}",
                flush=True,
            )

            item = self._extract_one(
                source=source,
                source_root=source_root,
            )

            result.items.append(item)

            if not item.success:
                result.failed += 1

                print(
                    "[BATCH] FAILED "
                    f"file={source.filename} "
                    f"error={item.error}",
                    flush=True,
                )

                continue

            result.successful += 1

            if item.cached:
                result.cache_hits += 1
            else:
                result.extracted += 1

            extraction = item.extraction

            if extraction is not None:
                method = extraction.provenance.method

                if method == ExtractionMethod.OCR:
                    result.ocr += 1
                elif method == ExtractionMethod.NATIVE:
                    result.native += 1

            print(
                "[BATCH] PASS "
                f"file={source.filename} "
                f"cached={item.cached}",
                flush=True,
            )

        self._print_summary(result)

        return result

    # ------------------------------------------------------------------
    # Single source
    # ------------------------------------------------------------------

    def _extract_one(
        self,
        *,
        source: SourceDocument,
        source_root: Path,
    ) -> SourceExtractionBatchItem:
        """
        Extract one source while isolating failures.

        Cache status is determined from the persisted extraction
        version before invoking the orchestrator.
        """

        try:
            # ----------------------------------------------------------
            # Determine whether this source is already persisted.
            #
            # This is only classification for batch reporting.
            # The orchestrator remains the owner of actual cache
            # behavior.
            # ----------------------------------------------------------

            existing = (
                self._orchestrator
                ._persistence_service
                .get_by_source_version(
                    source_id=source.source_id,
                    source_sha256=source.sha256,
                )
                if source.sha256
                else None
            )

            extraction = self._orchestrator.extract(
                source=source,
                source_root=source_root,
            )

            return SourceExtractionBatchItem(
                source=source,
                success=True,
                cached=existing is not None,
                extraction=extraction,
            )

        except Exception as exc:
            return SourceExtractionBatchItem(
                source=source,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @staticmethod
    def _print_summary(
        result: SourceExtractionBatchResult,
    ) -> None:
        """Print the production batch summary."""

        print()
        print("=" * 100)
        print("SOURCE EXTRACTION BATCH SUMMARY")
        print("=" * 100)

        print(
            f"STARTUP       : {result.startup_id}"
        )
        print(
            f"TOTAL         : {result.total}"
        )
        print(
            f"SUCCESS       : {result.successful}"
        )
        print(
            f"FAILED        : {result.failed}"
        )
        print(
            f"CACHE HIT     : {result.cache_hits}"
        )
        print(
            f"EXTRACTED     : {result.extracted}"
        )
        print(
            f"NATIVE        : {result.native}"
        )
        print(
            f"OCR           : {result.ocr}"
        )
        print(
            f"SUCCESS RATE  : {result.success_rate:.1f}%"
        )

        print()

        if result.failed:
            print("FAILED SOURCES")
            print("--------------")

            for item in result.items:
                if item.success:
                    continue

                print(
                    f"  {item.source.relative_path}"
                )
                print(
                    f"    {item.error}"
                )

        print()
        print(
            "BATCH STATUS  : "
            + (
                "PASS"
                if result.failed == 0
                else "COMPLETED_WITH_FAILURES"
            )
        )
