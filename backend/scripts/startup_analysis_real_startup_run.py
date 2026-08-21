"""Run STANDARD startup analysis against a persisted real startup."""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from app.core.database.session import create_session
from app.models.analysis import StartupAnalysisMode
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run STANDARD startup analysis against "
            "a persisted startup."
        )
    )

    parser.add_argument(
        "--startup-id",
        required=True,
        type=UUID,
        help="Persisted startup UUID.",
    )

    parser.add_argument(
        "--mode",
        choices=("STANDARD", "DEEP"),
        default="STANDARD",
        help="Analysis mode. Defaults to STANDARD.",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    mode = StartupAnalysisMode[args.mode]

    print()
    print("=" * 80)
    print("REAL STARTUP ANALYSIS")
    print("=" * 80)
    print(f"Startup ID : {args.startup_id}")
    print(f"Mode       : {mode.value}")

    session = create_session()

    try:
        service = StartupAnalysisApplicationService(
            session
        )

        print()
        print("Running production startup analysis...")
        print("This may take several minutes.")

        analysis = service.analyze(
            args.startup_id,
            mode=mode,
        )

        print()
        print("=" * 80)
        print("REAL STARTUP ANALYSIS: PASS")
        print("=" * 80)

        print(f"Analysis ID       : {analysis.id}")
        print(f"Startup ID        : {analysis.startup_id}")
        print(f"Mode              : {analysis.mode.value}")
        print(f"Status            : {analysis.status.value}")
        print(f"Model             : {analysis.model_name}")
        print(
            f"Thinking enabled  : "
            f"{analysis.thinking_enabled}"
        )
        print(
            f"Max tokens        : "
            f"{analysis.max_tokens}"
        )
        print(
            f"Recommendation     : "
            f"{analysis.recommendation}"
        )

        return 0

    except Exception as exc:
        session.rollback()

        print()
        print("=" * 80)
        print("REAL STARTUP ANALYSIS: FAILED")
        print("=" * 80)
        print(
            f"Exception type : {type(exc).__name__}"
        )
        print(
            f"Exception      : {exc}"
        )

        return 1

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
