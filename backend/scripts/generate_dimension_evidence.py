"""
Generate dimension-scoped investment evidence for a startup.

Production flow
---------------

    Startup
        |
        v
    Current source discovery
        |
        v
    Exact source_id + SHA256 extraction lookup
        |
        v
    StartupAnalysisInputBuilder
        |
        v
    StartupAnalysisDocumentIntelligenceService
        |
        v
    Canonical AnalysisEvidence
        |
        v
    DimensionEvidenceBuilder
        |
        v
    dimension_evidence.json

Important
---------

This runner generates the investment scorecard evidence artifact.

It does NOT:

    - perform source extraction
    - perform OCR
    - run the investment scorecard evaluator
    - calculate investment scores
    - calculate weighted scores
    - apply investment decision rules
    - persist StartupAnalysis
    - modify investment_scorecard.json

The persisted SourceExtractionRecord is authoritative.  A source file is
considered current only when its source_id and SHA256 match a persisted
extraction record.

Document intelligence may invoke the configured intelligence/LLM provider.
That is intentional: this runner builds canonical evidence from the current
persisted source-extraction artifacts.  It does not invoke the investment
scorecard Qwen evaluator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from app.core.config.settings import settings
from app.core.database.session import create_session
from app.models.investment_scorecard import InvestmentScorecard
from app.services.dimension_evidence_builder import (
    DimensionEvidenceBuilder,
)
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)
from app.services.startup import StartupService
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)
from app.services.startup_analysis_input_builder import (
    StartupAnalysisInputBuilder,
)


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_DATA_ROOT = Path(
    "/opt/investment-os/data/real_startups"
)

DEFAULT_GENERATED_ROOT = Path(
    "/opt/investment-os/generated"
)

DEFAULT_SCHEMA_VERSION = "1.0"

STARTUP_ANALYSIS_STARTUP_ID = UUID(
    "dbb520d7-0979-4db3-8464-523f5710455f"
)


# ============================================================================
# ARGUMENTS
# ============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate dimension_evidence.json from current "
            "persisted source extractions."
        )
    )

    parser.add_argument(
        "--startup",
        required=True,
        help=(
            "Startup directory/name, for example: restomart"
        ),
    )

    parser.add_argument(
        "--data-root",
        default=str(DEFAULT_DATA_ROOT),
        help=(
            "Root containing startup directories. "
            f"Default: {DEFAULT_DATA_ROOT}"
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output JSON path. "
            "Default: /opt/investment-os/generated/"
            "<startup>/dimension_evidence.json"
        ),
    )

    parser.add_argument(
        "--schema-version",
        default=DEFAULT_SCHEMA_VERSION,
        help=(
            "Dimension evidence schema version. "
            f"Default: {DEFAULT_SCHEMA_VERSION}"
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Fail if any canonical evidence item cannot be "
            "routed to a scorecard dimension."
        ),
    )

    return parser.parse_args()


# ============================================================================
# PATH / STARTUP HELPERS
# ============================================================================


def normalize_startup_key(value: str) -> str:
    """Normalize a startup CLI identifier to its filesystem key."""

    return (
        value.strip()
        .lower()
        .replace(" ", "_")
    )


def resolve_startup_directory(
    *,
    data_root: Path,
    startup_identifier: str,
) -> Path:
    """Resolve the startup data directory."""

    if not startup_identifier.strip():
        raise ValueError(
            "--startup must not be blank."
        )

    startup_key = normalize_startup_key(
        startup_identifier
    )

    startup_dir = data_root / startup_key

    if not startup_dir.exists():
        raise FileNotFoundError(
            "Startup directory not found: "
            f"{startup_dir}"
        )

    if not startup_dir.is_dir():
        raise ValueError(
            "Startup path is not a directory: "
            f"{startup_dir}"
        )

    return startup_dir


# ============================================================================
# SCORECARD
# ============================================================================


def load_scorecard(
    startup_dir: Path,
) -> InvestmentScorecard:
    """Load and validate the investment scorecard."""

    path = (
        startup_dir
        / "investment_scorecard.json"
    )

    if not path.is_file():
        raise FileNotFoundError(
            "Investment scorecard not found: "
            f"{path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid JSON in investment scorecard: "
            f"{path}"
        ) from exc

    try:
        return InvestmentScorecard.model_validate(
            payload
        )
    except Exception as exc:
        raise ValueError(
            "Invalid investment scorecard structure: "
            f"{path}"
        ) from exc


# ============================================================================
# STARTUP RESOLUTION
# ============================================================================


def resolve_startup(
    *,
    startup_service: StartupService,
    startup_identifier: str,
):
    """
    Resolve a persisted Startup.

    Resolution policy:

        1. If --startup is a UUID, use get_startup(UUID).
        2. Otherwise compare persisted startup names using the same
           normalized filesystem convention.
        3. Require exactly one match.
    """

    identifier = startup_identifier.strip()

    # ------------------------------------------------------------------
    # UUID lookup
    # ------------------------------------------------------------------

    try:
        startup_id = UUID(identifier)
    except ValueError:
        startup_id = None

    if startup_id is not None:
        startup = startup_service.get_startup(
            startup_id
        )

        if startup is None:
            raise ValueError(
                f"Startup not found for UUID: {startup_id}"
            )

        return startup

    # ------------------------------------------------------------------
    # Name lookup
    # ------------------------------------------------------------------

    normalized = normalize_startup_key(
        identifier
    )

    matches = [
        startup
        for startup in startup_service.list_startups()
        if normalize_startup_key(startup.name)
        == normalized
    ]

    if not matches:
        raise ValueError(
            "Startup not found for identifier: "
            f"{startup_identifier}"
        )

    if len(matches) > 1:
        ids = ", ".join(
            str(startup.id)
            for startup in matches
        )

        raise ValueError(
            "Multiple startups matched "
            f"'{startup_identifier}': {ids}"
        )

    return matches[0]


# ============================================================================
# CURRENT SOURCE EXTRACTIONS
# ============================================================================


def resolve_current_source_extractions(
    *,
    startup,
    source_discovery: SourceDiscoveryService,
    extraction_persistence: SourceExtractionPersistenceService,
) -> tuple:
    """
    Resolve persisted source extractions for the startup's current sources.

    Source identity is generated from the canonical Startup UUID.

    The current extraction must match:

        source_id
        +
        source_sha256

    This prevents an older extraction from being reused after the source
    file changes.
    """

    startup_key = normalize_startup_key(
        startup.name
    )

    source_root = (
        Path(settings.real_startups_root)
        / startup_key
        / "sources"
    )

    if not source_root.exists():
        raise FileNotFoundError(
            "Source directory not found: "
            f"{source_root}"
        )

    print(
        f"SOURCE ROOT       : {source_root}"
    )

    # ------------------------------------------------------------------
    # IMPORTANT:
    #
    # source_id must be generated from the canonical Startup UUID.
    #
    # Do NOT use startup.name here.
    # ------------------------------------------------------------------

    sources = source_discovery.discover(
        startup_id=str(startup.id),
        source_root=source_root,
    )

    print(
        f"CURRENT SOURCES   : {len(sources)}"
    )

    records = []

    missing_extractions = []

    for source in sources:
        if source.sha256 is None:
            missing_extractions.append(
                source.filename
            )
            continue

        record = (
            extraction_persistence
            .get_by_source_version(
                source_id=source.source_id,
                source_sha256=source.sha256,
            )
        )

        if record is None:
            missing_extractions.append(
                source.filename
            )
            continue

        records.append(record)

    print(
        f"CURRENT EXTRACTS  : {len(records)}"
    )
    
    if missing_extractions:
        print(
            "MISSING EXTRACTS  : "
            f"{len(missing_extractions)}"
        )
    
        for filename in missing_extractions:
            print(
                f"  - {filename}"
            )
    
        raise RuntimeError(
            "Current source set is not fully extracted. "
            f"Missing {len(missing_extractions)} "
            "current source extraction(s)."
        )


    if not records:
        raise RuntimeError(
            "No current persisted source extractions "
            "were found."
        )

    return tuple(records)


# ============================================================================
# DOCUMENT INTELLIGENCE
# ============================================================================


def build_document_intelligence_service(
    session,
):
    """
    Build the same production document-intelligence service used by
    StartupAnalysisApplicationService.

    No StartupAnalysis is executed or persisted here.
    """

    return (
        StartupAnalysisApplicationService
        .create_startup_analysis_document_intelligence(
            session
        )
    )


# ============================================================================
# EVIDENCE GENERATION
# ============================================================================


def generate_dimension_evidence(
    *,
    session,
    startup,
    scorecard: InvestmentScorecard,
    source_extractions: tuple,
    strict: bool,
    schema_version: str,
):
    """
    Generate the DimensionEvidenceSet.

    Flow:

        StartupAnalysisInputBuilder
            ->
        Document Intelligence
            ->
        canonical AnalysisEvidence
            ->
        DimensionEvidenceBuilder
    """

    print()
    print("=" * 88)
    print(
        "INVESTMENT OS — DIMENSION EVIDENCE GENERATION"
    )
    print("=" * 88)

    print(
        f"STARTUP           : {startup.name}"
    )

    print(
        f"STARTUP ID        : {startup.id}"
    )

    print(
        "SCORECARD          : investment_scorecard.json"
    )

    print(
        f"DIMENSIONS        : "
        f"{len(scorecard.dimensions)}"
    )

    print(
        f"STRICT MODE       : {strict}"
    )

    # ------------------------------------------------------------------
    # 1. Build normalized startup-analysis input.
    # ------------------------------------------------------------------

    input_builder = (
        StartupAnalysisInputBuilder()
    )

    analysis_input = (
        input_builder.build(
            startup
        )
    )

    print()
    print(
        "BASE INPUT        : constructed"
    )

    # ------------------------------------------------------------------
    # 2. Build production document-intelligence service.
    # ------------------------------------------------------------------

    document_intelligence = (
        build_document_intelligence_service(
            session
        )
    )

    print(
        "DOCUMENT INTEL     : production service"
    )

    # ------------------------------------------------------------------
    # 3. Enrich from current persisted extractions.
    # ------------------------------------------------------------------

    enriched_input = (
        document_intelligence.enrich(
            startup=startup,
            analysis_input=analysis_input,
            source_extractions=source_extractions,
        )
    )

    # ------------------------------------------------------------------
    # 4. Validate canonical evidence availability.
    # ------------------------------------------------------------------

    canonical_evidence = (
        enriched_input.evidence
    )

    print()
    print(
        f"CANONICAL EVIDENCE : "
        f"{len(canonical_evidence)}"
    )

    if not canonical_evidence:
        raise RuntimeError(
            "Document intelligence produced no canonical "
            "AnalysisEvidence."
        )

    # ------------------------------------------------------------------
    # 5. Build dimension-specific evidence.
    # ------------------------------------------------------------------

    builder = DimensionEvidenceBuilder(
        strict=strict
    )

    build_result = builder.build(
        startup_name=startup.name,
        scorecard=scorecard,
        analysis_input=enriched_input,
        schema_version=schema_version,
    )

    return build_result


# ============================================================================
# JSON OUTPUT
# ============================================================================


def write_dimension_evidence(
    *,
    output_path: Path,
    evidence_set,
) -> None:
    """
    Atomically write DimensionEvidenceSet as JSON.

    The temporary file is created beside the target and then replaced.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = evidence_set.model_dump(
        mode="json"
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")

    temporary_path.replace(
        output_path
    )


# ============================================================================
# DIAGNOSTICS
# ============================================================================


def print_build_diagnostics(
    build_result,
) -> None:
    """Print deterministic builder diagnostics."""

    diagnostics = (
        build_result.diagnostics
    )

    print()
    print("-" * 88)
    print(
        "DIMENSION EVIDENCE DIAGNOSTICS"
    )
    print("-" * 88)

    print(
        f"Total canonical evidence : "
        f"{diagnostics.total_evidence}"
    )

    print(
        f"Routed evidence          : "
        f"{diagnostics.routed_evidence}"
    )

    print(
        f"Unrouted evidence        : "
        f"{diagnostics.unrouted_evidence}"
    )

    print(
        f"Duplicate evidence       : "
        f"{diagnostics.duplicate_evidence}"
    )

    print()
    print(
        f"{'DIMENSION':<36}"
        f"{'COUNT':>10}"
    )

    print("-" * 50)

    for dimension_id in sorted(
        diagnostics.dimension_counts
    ):
        count = (
            diagnostics.dimension_counts[
                dimension_id
            ]
        )

        print(
            f"{dimension_id:<36}"
            f"{count:>10}"
        )

    if diagnostics.unrouted_refs:
        print()
        print(
            "UNROUTED EVIDENCE REFERENCES:"
        )

        for evidence_ref in (
            diagnostics.unrouted_refs
        ):
            print(
                f"  - {evidence_ref}"
            )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    """CLI entry point."""

    args = parse_args()

    data_root = Path(
        args.data_root
    )

    try:
        # ------------------------------------------------------------------
        # Resolve startup directory.
        # ------------------------------------------------------------------

        startup_dir = (
            resolve_startup_directory(
                data_root=data_root,
                startup_identifier=args.startup,
            )
        )

        # ------------------------------------------------------------------
        # Create DB session using project-standard session factory.
        # ------------------------------------------------------------------

        session = create_session()

        try:
            # ------------------------------------------------------------------
            # Resolve persisted startup.
            # ------------------------------------------------------------------
            
            startup_service = (
                StartupService(session)
            )
            
            startup = resolve_startup(
                startup_service=startup_service,
                startup_identifier=args.startup,
            )
            
            # ------------------------------------------------------------------
            # Determine output path.
            # ------------------------------------------------------------------
            
            if args.output:
                output_path = Path(
                    args.output
                )
            
                if not output_path.is_absolute():
                    output_path = (
                        Path.cwd()
                        / output_path
                    )
            else:
                output_path = (
                    DEFAULT_GENERATED_ROOT
                    / normalize_startup_key(startup.name)
                    / "dimension_evidence.json"
                )
            
            print()
            print( f"DATA ROOT         : {data_root}")
            print( f"STARTUP DIRECTORY : {startup_dir}")
            print( f"PERSISTED STARTUP : {startup.name}")
            print( f"CANONICAL UUID    : {startup.id}")
            print( f"OUTPUT            : {output_path}")
            

            # --------------------------------------------------------------
            # Load scorecard.
            # --------------------------------------------------------------

            scorecard = load_scorecard(
                startup_dir
            )

            # --------------------------------------------------------------
            # Resolve current source extractions.
            # --------------------------------------------------------------

            source_discovery = (
                SourceDiscoveryService()
            )

            extraction_persistence = (
                SourceExtractionPersistenceService(
                    session=session
                )
            )

            source_extractions = (
                resolve_current_source_extractions(
                    startup=startup,
                    source_discovery=source_discovery,
                    extraction_persistence=(
                        extraction_persistence
                    ),
                )
            )

            # --------------------------------------------------------------
            # Generate dimension evidence.
            # --------------------------------------------------------------

            build_result = (
                generate_dimension_evidence(
                    session=session,
                    startup=startup,
                    scorecard=scorecard,
                    source_extractions=(
                        source_extractions
                    ),
                    strict=args.strict,
                    schema_version=(
                        args.schema_version
                    ),
                )
            )

            # --------------------------------------------------------------
            # Diagnostics.
            # --------------------------------------------------------------

            print_build_diagnostics(
                build_result
            )

            # --------------------------------------------------------------
            # Write JSON.
            # --------------------------------------------------------------

            write_dimension_evidence(
                output_path=output_path,
                evidence_set=(
                    build_result.evidence_set
                ),
            )

            print()
            print("=" * 88)
            print(
                "DIMENSION EVIDENCE GENERATION COMPLETE"
            )
            print("=" * 88)

            print(
                f"OUTPUT            : {output_path}"
            )

            print(
                f"FILE SIZE         : "
                f"{output_path.stat().st_size} bytes"
            )

            print(
                f"CANONICAL EVIDENCE: "
                f"{build_result.diagnostics.total_evidence}"
            )

            print(
                f"ROUTED EVIDENCE   : "
                f"{build_result.diagnostics.routed_evidence}"
            )

            print(
                f"UNROUTED          : "
                f"{build_result.diagnostics.unrouted_evidence}"
            )

            print(
                f"DUPLICATES        : "
                f"{build_result.diagnostics.duplicate_evidence}"
            )

            print()
            print("STATUS            : PASS")

            return 0

        finally:
            session.close()

    except Exception as exc:
        print()
        print("=" * 88)
        print(
            "DIMENSION EVIDENCE GENERATION FAILED"
        )
        print("=" * 88)
        print(
            f"{type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )
