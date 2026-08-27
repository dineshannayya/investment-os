"""
Generic production runner for startup investment scorecard analysis.

Day-2.2.3

Usage:

    python -m scripts.run_startup_investment_analysis \
        --startup restomart

or:

    python scripts/run_startup_investment_analysis.py \
        --startup restomart

The runner is intentionally thin.

It is responsible for:
    - resolving the startup directory
    - loading startup metadata
    - loading the investment scorecard
    - loading dimension-specific evidence
    - constructing the application services
    - invoking the investment analysis pipeline
    - rendering the resulting InvestmentView

It does NOT:
    - construct LLM prompts
    - call Qwen directly
    - calculate dimension scores
    - calculate weighted scores
    - apply investment decision rules
    - modify evidence
    - modify scorecard configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.models.investment_scorecard import (
    InvestmentScorecard,
)
from app.services.dimension_evidence_loader import (
    DimensionEvidenceLoader,
)
from app.services.investment_analysis import (
    InvestmentAnalysisResult,
    InvestmentAnalysisService,
)
from app.services.investment_decision import (
    InvestmentDecisionService,
)
from app.services.investment_score_aggregation import (
    InvestmentScoreAggregationService,
)
from app.services.investment_scorecard_evaluation import (
    InvestmentScorecardEvaluationService,
)
from app.services.investment_view import (
    InvestmentViewService,
)


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_DATA_ROOT = Path(
    "/opt/investment-os/data/real_startups"
)

# Qwen completion budget.
#
# 2048 is intentional:
# multi-dimension evaluation can produce structured missing-information
# and evidence fields that require more than a tight 768-token budget.
DEFAULT_MAX_TOKENS = 2048

DEFAULT_TEMPERATURE = 0.0

DEFAULT_THINKING_ENABLED = False


# ============================================================================
# ARGUMENTS
# ============================================================================


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Run the complete startup investment "
            "scorecard analysis."
        )
    )

    parser.add_argument(
        "--startup",
        required=True,
        help=(
            "Startup directory identifier, "
            "for example: restomart"
        ),
    )

    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help=(
            "Root directory containing startup data. "
            f"Default: {DEFAULT_DATA_ROOT}"
        ),
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=(
            "Maximum Qwen completion tokens. "
            f"Default: {DEFAULT_MAX_TOKENS}"
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=(
            "LLM temperature. "
            f"Default: {DEFAULT_TEMPERATURE}"
        ),
    )

    parser.add_argument(
        "--thinking",
        action="store_true",
        help=(
            "Enable Qwen thinking mode. "
            "Default: disabled."
        ),
    )

    return parser.parse_args()


# ============================================================================
# ARGUMENT VALIDATION
# ============================================================================


def validate_args(
    args: argparse.Namespace,
) -> None:
    """
    Validate CLI-level configuration.

    Domain validation remains inside the appropriate services.
    """

    if args.max_tokens <= 0:
        raise ValueError(
            "--max-tokens must be greater than zero."
        )

    if args.temperature < 0.0:
        raise ValueError(
            "--temperature must be greater than or equal to zero."
        )


# ============================================================================
# PATH RESOLUTION
# ============================================================================


def resolve_startup_directory(
    *,
    data_root: Path,
    startup_name: str,
) -> Path:
    """
    Resolve a startup directory.

    No startup-specific paths are hardcoded.
    """

    if not startup_name:
        raise ValueError(
            "startup name must not be empty."
        )

    startup_dir = data_root / startup_name

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
# STARTUP METADATA
# ============================================================================


def load_startup_metadata(
    startup_dir: Path,
) -> dict:
    """
    Load startup.yaml.

    The current scorecard pipeline only requires the startup
    identifier/name, but the complete YAML is retained as metadata.
    """

    path = startup_dir / "startup.yaml"

    if not path.exists():
        raise FileNotFoundError(
            f"Startup metadata file not found: {path}"
        )

    try:
        import yaml

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = yaml.safe_load(handle)

    except Exception as exc:
        raise ValueError(
            "Unable to load startup metadata: "
            f"{path}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "Startup metadata must contain a YAML object: "
            f"{path}"
        )

    return payload


def resolve_startup_name(
    *,
    startup_identifier: str,
    startup_metadata: dict,
) -> str:
    """
    Resolve the display/startup name.

    Prefer an explicit 'name' field from startup.yaml.

    Fall back to the CLI startup identifier.
    """

    value = startup_metadata.get("name")

    if isinstance(value, str) and value.strip():
        return value.strip()

    return startup_identifier


# ============================================================================
# SCORECARD
# ============================================================================


def load_scorecard(
    startup_dir: Path,
) -> InvestmentScorecard:
    """
    Load and validate investment_scorecard.json.
    """

    path = (
        startup_dir
        / "investment_scorecard.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Investment scorecard not found: {path}"
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
# SERVICE CONSTRUCTION
# ============================================================================


def build_analysis_service() -> InvestmentAnalysisService:
    """
    Construct the complete investment-analysis service graph.

    The runner owns dependency wiring only.
    Business logic remains inside the application services.
    """

    evaluation_service = (
        InvestmentScorecardEvaluationService()
    )

    aggregation_service = (
        InvestmentScoreAggregationService()
    )

    decision_service = (
        InvestmentDecisionService()
    )

    view_service = InvestmentViewService()

    return InvestmentAnalysisService(
        evaluation_service=evaluation_service,
        aggregation_service=aggregation_service,
        decision_service=decision_service,
        view_service=view_service,
    )


# ============================================================================
# RENDERING HELPERS
# ============================================================================


def render_header(
    title: str,
) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def render_dimension_scores(
    result: InvestmentAnalysisResult,
) -> None:
    """
    Render deterministic weighted dimension results.
    """

    render_header(
        "DIMENSION SCORES"
    )

    print(
        f"{'DIMENSION':<36}"
        f"{'SCORE':>8}"
        f"{'WEIGHT':>9}"
        f"{'CONTRIBUTION':>16}"
    )

    print("-" * 88)

    for item in result.aggregation.dimension_scores:
        print(
            f"{item.dimension_id:<36}"
            f"{item.score:>8}"
            f"{item.weight:>9}"
            f"{item.weighted_score:>16.2f}"
        )


def render_list(
    title: str,
    values: list[str],
) -> None:
    """
    Render a simple list section.
    """

    render_header(title)

    if not values:
        print("NONE")
        return

    for value in values:
        print(f"- {value}")


def render_investment_view(
    result: InvestmentAnalysisResult,
) -> None:
    """
    Render the final human-readable investment view.
    """

    view = result.view

    render_header(
        f"{view.startup_name.upper()} — INVESTMENT VIEW"
    )

    print(
        f"Scorecard       : "
        f"{view.scorecard_name}"
    )

    print(
        f"Scorecard       : "
        f"version {view.scorecard_version}"
    )

    print(
        f"Overall Score   : "
        f"{view.overall_score:.2f} / 100"
    )

    print(
        f"Decision        : "
        f"{view.decision.upper()}"
    )

    print(
        f"Decision Reason : "
        f"{view.decision_reason}"
    )

    render_dimension_scores(result)

    render_list(
        "KEY POSITIVES",
        view.positive_factors,
    )

    render_list(
        "KEY RISKS",
        view.key_risks,
    )

    render_list(
        "MISSING INFORMATION",
        view.missing_information,
    )

    render_list(
        "DILIGENCE FOCUS",
        view.diligence_focus,
    )

    render_header(
        "INVESTMENT SUMMARY"
    )

    print(view.investment_summary)


def render_analysis_metadata(
    result: InvestmentAnalysisResult,
) -> None:
    """
    Render useful machine-generated analysis metadata.

    This is intentionally separate from InvestmentView rendering.
    """

    render_header(
        "ANALYSIS METADATA"
    )

    print(
        f"Startup          : "
        f"{result.evaluation.startup_name}"
    )

    print(
        f"Scorecard version : "
        f"{result.evaluation.scorecard_version}"
    )

    print(
        f"Dimensions       : "
        f"{len(result.evaluation.evaluations)}"
    )

    print(
        f"Overall score    : "
        f"{result.aggregation.overall_score:.2f}"
    )

    print(
        f"Total weight     : "
        f"{result.aggregation.total_weight}"
    )

    print(
        f"Decision         : "
        f"{result.decision.decision.value}"
    )

    print(
        f"High risks       : "
        f"{result.decision.high_risk_count}"
    )

    print(
        f"Critical risks   : "
        f"{result.decision.critical_risk_count}"
    )

    print(
        f"Medium risks     : "
        f"{result.decision.medium_risk_count}"
    )


# ============================================================================
# MAIN ANALYSIS
# ============================================================================


def run_analysis(
    *,
    startup_identifier: str,
    data_root: Path,
    temperature: float,
    max_tokens: int,
    thinking_enabled: bool,
) -> InvestmentAnalysisResult:
    """
    Execute the complete production investment analysis.
    """

    # ------------------------------------------------------------------
    # 1. Resolve startup directory
    # ------------------------------------------------------------------

    startup_dir = resolve_startup_directory(
        data_root=data_root,
        startup_name=startup_identifier,
    )

    # ------------------------------------------------------------------
    # 2. Load startup metadata
    # ------------------------------------------------------------------

    startup_metadata = load_startup_metadata(
        startup_dir
    )

    startup_name = resolve_startup_name(
        startup_identifier=startup_identifier,
        startup_metadata=startup_metadata,
    )

    # ------------------------------------------------------------------
    # 3. Load scorecard
    # ------------------------------------------------------------------

    scorecard = load_scorecard(
        startup_dir
    )

    # ------------------------------------------------------------------
    # 4. Load dimension-specific evidence
    # ------------------------------------------------------------------

    evidence_path = (
        startup_dir
        / "dimension_evidence.json"
    )

    evidence_set = (
        DimensionEvidenceLoader.load_for_scorecard(
            path=evidence_path,
            scorecard=scorecard,
        )
    )

    # ------------------------------------------------------------------
    # 5. Build production service graph
    # ------------------------------------------------------------------

    analysis_service = (
        build_analysis_service()
    )

    # ------------------------------------------------------------------
    # 6. Execute complete analysis
    # ------------------------------------------------------------------

    return analysis_service.analyze(
        startup_name=startup_name,
        scorecard=scorecard,
        evidence_set=evidence_set,
        temperature=temperature,
        max_tokens=max_tokens,
        thinking_enabled=thinking_enabled,
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    args = parse_args()

    try:
        validate_args(args)

        print("=" * 88)
        print(
            "INVESTMENT OS — STARTUP INVESTMENT ANALYSIS"
        )
        print("=" * 88)

        print()
        print(
            f"startup       : {args.startup}"
        )

        print(
            f"data root     : {args.data_root}"
        )

        print(
            f"temperature   : {args.temperature}"
        )

        print(
            f"max tokens    : {args.max_tokens}"
        )

        print(
            f"thinking      : {args.thinking}"
        )

        result = run_analysis(
            startup_identifier=args.startup,
            data_root=args.data_root,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            thinking_enabled=args.thinking,
        )

        render_analysis_metadata(
            result
        )

        render_investment_view(
            result
        )

    except Exception as exc:
        print()
        print("=" * 88)
        print("INVESTMENT ANALYSIS : FAILED")
        print("=" * 88)
        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        return 1

    print()
    print("=" * 88)
    print("INVESTMENT ANALYSIS : COMPLETE")
    print("=" * 88)

    return 0


if __name__ == "__main__":
    sys.exit(main())
