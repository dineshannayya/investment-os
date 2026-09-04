#!/usr/bin/env python3
# -----------------------------------------------------------------------------
#  treats investment_scorecard.json strictly as the template;
#  extracts dimension names/weights from the template;
#  looks for LLM-generated dimension scores in the persisted analysis;
#  supports the structured evaluation / aggregation representation from the investment-analysis architecture;
#  does not invent scores;
#  does not use the template's scoring bands as scores;
#  calculates weighted values only when actual LLM scores are available;
#  clearly reports when the selected historical analysis does not contain dimension scores;
#  still prints the complete analysis information;
#  remains read-only.
# -----------------------------------------------------------------------------
"""
Inspect a persisted StartupAnalysis and produce a human-readable report.

IMPORTANT
---------
investment_scorecard.json is a REFERENCE TEMPLATE.

It defines:
    - dimensions
    - weights
    - evaluation criteria
    - scoring guidance

It does NOT contain startup-specific scores.

Actual dimension scores must come from the LLM-generated
DimensionEvaluation / investment-analysis result.

This script is READ-ONLY.
It never executes a new analysis and never modifies the database.

Usage:
    python scripts/analyze_startup_analysis.py <analysis_id>

    python scripts/analyze_startup_analysis.py <analysis_id> \
        --out analysis_report.txt
"""

from __future__ import annotations

import argparse
import json
import pprint
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database.session import create_session
from app.models.analysis import StartupAnalysis


WIDTH = 120

SCORECARD_ROOT = Path(
    "/opt/investment-os/data/real_startups"
)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect a persisted StartupAnalysis by analysis ID."
    )

    parser.add_argument(
        "analysis_id",
        help="StartupAnalysis UUID",
    )

    parser.add_argument(
        "--out",
        "-o",
        dest="output",
        help="Write report to this file",
    )

    return parser.parse_args()


def section(title: str) -> list[str]:
    return [
        "",
        "-" * WIDTH,
        title,
        "-" * WIDTH,
    ]


def format_value(value: Any) -> str:
    if value is None:
        return "None"

    if isinstance(value, dict):
        return pprint.pformat(
            value,
            width=WIDTH,
            sort_dicts=False,
        )

    if isinstance(value, (list, tuple)):
        return pprint.pformat(
            value,
            width=WIDTH,
            sort_dicts=False,
        )

    return str(value)


def as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def get_attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def load_analysis(
    analysis_id: UUID,
) -> StartupAnalysis | None:

    session = create_session()

    try:
        return session.scalar(
            select(StartupAnalysis).where(
                StartupAnalysis.id == analysis_id
            )
        )
    finally:
        session.close()


def load_startup_name(
    startup_id: UUID,
) -> str | None:

    try:
        from app.models.startup import Startup
    except ImportError:
        return None

    session = create_session()

    try:
        startup = session.scalar(
            select(Startup).where(
                Startup.id == startup_id
            )
        )

        if startup is None:
            return None

        return startup.name

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Scorecard template
# ---------------------------------------------------------------------------

def find_scorecard_path(
    startup_name: str | None,
) -> Path | None:

    if not startup_name:
        return None

    startup_dir = (
        startup_name.strip()
        .lower()
        .replace(" ", "_")
    )

    path = (
        SCORECARD_ROOT
        / startup_dir
        / "investment_scorecard.json"
    )

    if path.exists() and path.is_file():
        return path

    return None


def load_scorecard(
    startup_name: str | None,
) -> tuple[dict[str, Any] | None, Path | None]:

    path = find_scorecard_path(startup_name)

    if path is None:
        return None, None

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle), path

    except (OSError, json.JSONDecodeError):
        return None, path


def extract_scorecard_dimensions(
    scorecard: dict[str, Any],
) -> list[dict[str, Any]]:

    dimensions = scorecard.get("dimensions")

    if not isinstance(dimensions, list):
        return []

    result: list[dict[str, Any]] = []

    for item in dimensions:
        if not isinstance(item, dict):
            continue

        dimension_id = item.get("id")
        name = item.get("name")
        weight = as_decimal(item.get("weight"))

        if not dimension_id or not name:
            continue

        result.append(
            {
                "id": str(dimension_id),
                "name": str(name),
                "weight": weight,
            }
        )

    return result


# ---------------------------------------------------------------------------
# Actual LLM score extraction
# ---------------------------------------------------------------------------

def find_evaluation_container(
    result_snapshot: Any,
) -> dict[str, Any] | None:

    if not isinstance(result_snapshot, dict):
        return None

    # Preferred structured investment-analysis result.
    evaluation = result_snapshot.get("evaluation")

    if isinstance(evaluation, dict):
        return evaluation

    # Some future persistence representations may place the
    # multi-dimension evaluation under a different explicit key.
    for key in (
        "multi_dimension_evaluation",
        "dimension_evaluation",
        "scorecard_evaluation",
    ):
        value = result_snapshot.get(key)

        if isinstance(value, dict):
            return value

    return None


def extract_llm_dimension_scores(
    result_snapshot: Any,
) -> dict[str, dict[str, Any]]:

    evaluation = find_evaluation_container(
        result_snapshot
    )

    if evaluation is None:
        return {}

    evaluations = evaluation.get("evaluations")

    if not isinstance(evaluations, list):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for item in evaluations:

        if not isinstance(item, dict):
            continue

        dimension_id = item.get("dimension_id")

        if not dimension_id:
            continue

        score = as_decimal(
            item.get("score")
        )

        confidence = as_decimal(
            item.get("confidence")
        )

        result[str(dimension_id)] = {
            "score": score,
            "confidence": confidence,
            "reasoning": item.get("reasoning"),
            "positive_observations": item.get(
                "positive_observations",
                [],
            ),
            "risk_observations": item.get(
                "risk_observations",
                [],
            ),
            "missing_information": item.get(
                "missing_information",
                [],
            ),
            "evidence": item.get(
                "evidence",
                [],
            ),
        }

    return result


# ---------------------------------------------------------------------------
# Aggregation extraction
# ---------------------------------------------------------------------------

def extract_persisted_aggregation(
    result_snapshot: Any,
) -> dict[str, Any] | None:

    if not isinstance(result_snapshot, dict):
        return None

    aggregation = result_snapshot.get(
        "aggregation"
    )

    if isinstance(aggregation, dict):
        return aggregation

    for key in (
        "weighted_score_aggregation",
        "score_aggregation",
    ):
        value = result_snapshot.get(key)

        if isinstance(value, dict):
            return value

    return None


# ---------------------------------------------------------------------------
# Score table
# ---------------------------------------------------------------------------

def build_score_rows(
    scorecard_dimensions: list[dict[str, Any]],
    result_snapshot: Any,
) -> tuple[list[dict[str, Any]], Decimal | None]:

    llm_scores = extract_llm_dimension_scores(
        result_snapshot
    )

    aggregation = extract_persisted_aggregation(
        result_snapshot
    )

    persisted_dimension_scores: dict[str, dict[str, Any]] = {}

    persisted_overall: Decimal | None = None

    if aggregation is not None:

        persisted_overall = as_decimal(
            aggregation.get("overall_score")
        )

        dimension_scores = aggregation.get(
            "dimension_scores"
        )

        if isinstance(dimension_scores, list):

            for item in dimension_scores:

                if not isinstance(item, dict):
                    continue

                dimension_id = item.get(
                    "dimension_id"
                )

                if dimension_id:
                    persisted_dimension_scores[
                        str(dimension_id)
                    ] = item

    rows: list[dict[str, Any]] = []

    calculated_total = Decimal("0")

    has_any_score = False

    for dimension in scorecard_dimensions:

        dimension_id = dimension["id"]
        weight = dimension["weight"]

        llm_item = llm_scores.get(
            dimension_id,
            {},
        )

        persisted_item = (
            persisted_dimension_scores.get(
                dimension_id,
                {},
            )
        )

        score = llm_item.get("score")

        if score is None:
            score = as_decimal(
                persisted_item.get("score")
            )

        confidence = llm_item.get(
            "confidence"
        )

        if confidence is None:
            confidence = as_decimal(
                persisted_item.get("confidence")
            )

        persisted_weighted = as_decimal(
            persisted_item.get(
                "weighted_score"
            )
        )

        weighted = None

        if score is not None and weight is not None:

            weighted = (
                score * weight / Decimal("100")
            ).quantize(
                Decimal("0.01")
            )

            calculated_total += weighted
            has_any_score = True

        elif persisted_weighted is not None:

            weighted = persisted_weighted
            calculated_total += weighted
            has_any_score = True

        rows.append(
            {
                "id": dimension_id,
                "name": dimension["name"],
                "score": score,
                "confidence": confidence,
                "weight": weight,
                "weighted_score": weighted,
            }
        )

    if persisted_overall is not None:
        overall = persisted_overall
    elif has_any_score:
        overall = calculated_total.quantize(
            Decimal("0.01")
        )
    else:
        overall = None

    return rows, overall


def format_score_table(
    scorecard_dimensions: list[dict[str, Any]],
    result_snapshot: Any,
) -> list[str]:

    rows, overall = build_score_rows(
        scorecard_dimensions,
        result_snapshot,
    )

    lines: list[str] = []

    if not rows:
        lines.append(
            "No scorecard dimensions were found."
        )
        return lines

    lines.append(
        f"{'Dimension':<32}"
        f"{'Score':>10}"
        f"{'Confidence':>13}"
        f"{'Weight':>10}"
        f"{'Weighted':>15}"
    )

    lines.append("-" * 80)

    total_weight = Decimal("0")
    has_scores = False

    for row in rows:

        name = row["name"]
        score = row["score"]
        confidence = row["confidence"]
        weight = row["weight"]
        weighted = row["weighted_score"]

        if weight is not None:
            total_weight += weight

        if score is not None:
            has_scores = True

        score_text = (
            f"{score:.2f}"
            if score is not None
            else "-"
        )

        confidence_text = (
            f"{confidence:.2f}"
            if confidence is not None
            else "-"
        )

        weight_text = (
            f"{weight:.2f}"
            if weight is not None
            else "-"
        )

        weighted_text = (
            f"{weighted:.2f}"
            if weighted is not None
            else "-"
        )

        lines.append(
            f"{name:<32}"
            f"{score_text:>10}"
            f"{confidence_text:>13}"
            f"{weight_text:>10}"
            f"{weighted_text:>15}"
        )

    lines.append("-" * 80)

    overall_text = (
        f"{overall:.2f}"
        if overall is not None
        else "-"
    )

    lines.append(
        f"{'OVERALL SCORE':<32}"
        f"{overall_text:>10}"
        f"{'':>13}"
        f"{total_weight:>10.2f}"
        f"{overall_text:>15}"
    )

    lines.append("")

    if not has_scores:
        lines.append(
            "NOTE: This persisted StartupAnalysis does not "
            "contain LLM-generated investment dimension scores."
        )
        lines.append(
            "The investment_scorecard.json file is only the "
            "reference scoring template and was not used to "
            "invent or infer scores."
        )

    return lines


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def extract_decision(
    result_snapshot: Any,
    analysis: StartupAnalysis,
) -> Any:

    aggregation = extract_persisted_aggregation(
        result_snapshot
    )

    if isinstance(result_snapshot, dict):

        decision = result_snapshot.get(
            "decision"
        )

        if isinstance(decision, dict):
            value = decision.get("decision")

            if value is not None:
                return value

        for key in (
            "investment_decision",
            "decision",
        ):
            value = result_snapshot.get(key)

            if value is not None and not isinstance(
                value,
                dict,
            ):
                return value

    recommendation = get_attr(
        analysis,
        "recommendation",
    )

    if recommendation is not None:
        return recommendation

    if aggregation is not None:
        return aggregation.get(
            "decision"
        )

    return None


# ---------------------------------------------------------------------------
# Quality flags
# ---------------------------------------------------------------------------

def build_quality_flags(
    analysis: StartupAnalysis,
    result_snapshot: Any,
    scorecard_dimensions: list[dict[str, Any]],
) -> list[str]:

    flags: list[str] = []

    rows, overall = build_score_rows(
        scorecard_dimensions,
        result_snapshot,
    )

    scored = [
        row
        for row in rows
        if row["score"] is not None
    ]

    if not scored:
        flags.append(
            "No LLM-generated investment dimension scores "
            "are persisted in this StartupAnalysis record."
        )

    elif len(scored) != len(rows):
        missing = [
            row["name"]
            for row in rows
            if row["score"] is None
        ]

        flags.append(
            "Missing LLM dimension scores: "
            + ", ".join(missing)
        )

    if overall is None:
        flags.append(
            "No persisted/calculable overall investment score."
        )

    metrics = get_attr(
        analysis,
        "metrics_snapshot",
    )

    if metrics is None:
        flags.append(
            "Metrics snapshot is missing."
        )

    elif isinstance(metrics, dict):

        empty_metrics = [
            key
            for key, value in metrics.items()
            if value is None
        ]

        if empty_metrics:
            flags.append(
                "Missing metrics: "
                + ", ".join(empty_metrics)
            )

    if isinstance(result_snapshot, dict):

        missing_information = result_snapshot.get(
            "missing_information"
        )

        if missing_information:
            flags.append(
                "Analysis contains explicitly identified "
                "missing information."
            )

        if not result_snapshot.get(
            "traction_assessment"
        ):
            flags.append(
                "Traction assessment is missing."
            )

        if not result_snapshot.get(
            "competitive_assessment"
        ):
            flags.append(
                "Competitive assessment is missing."
            )

        if not result_snapshot.get(
            "financial_assessment"
        ):
            flags.append(
                "Detailed financial assessment is missing."
            )

    return flags


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    analysis: StartupAnalysis,
    startup_name: str | None,
) -> str:

    lines: list[str] = []

    scorecard, scorecard_path = load_scorecard(
        startup_name
    )

    result_snapshot = get_attr(
        analysis,
        "result_snapshot",
    )

    scorecard_dimensions: list[
        dict[str, Any]
    ] = []

    if scorecard is not None:
        scorecard_dimensions = (
            extract_scorecard_dimensions(
                scorecard
            )
        )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    lines.extend(
        [
            "=" * WIDTH,
            "STARTUP ANALYSIS REPORT",
            "=" * WIDTH,
            "",
            f"Analysis ID       : {analysis.id}",
            f"Startup ID        : {analysis.startup_id}",
            f"Startup           : {startup_name or 'Unknown'}",
            f"Status            : {get_attr(analysis, 'status')}",
            f"Mode              : {get_attr(analysis, 'mode')}",
            f"Analysis Version  : {get_attr(analysis, 'analysis_version')}",
            f"Model             : {get_attr(analysis, 'model_name')}",
            f"Thinking Enabled  : {get_attr(analysis, 'thinking_enabled')}",
            f"Max Tokens        : {get_attr(analysis, 'max_tokens')}",
            f"Temperature       : {get_attr(analysis, 'temperature')}",
            f"Finish Reason     : {get_attr(analysis, 'finish_reason')}",
            f"Prompt Tokens     : {get_attr(analysis, 'prompt_tokens')}",
            f"Completion Tokens : {get_attr(analysis, 'completion_tokens')}",
            f"Total Tokens      : {get_attr(analysis, 'total_tokens')}",
            f"Inference Time    : {get_attr(analysis, 'inference_time_seconds')}",
        ]
    )

    # ------------------------------------------------------------------
    # Investment Scorecard
    # ------------------------------------------------------------------

    lines.extend(
        section("INVESTMENT SCORECARD")
    )

    if scorecard is None:

        lines.append(
            "Investment scorecard template not available."
        )

        if scorecard_path is not None:
            lines.append(
                f"Scorecard path: {scorecard_path}"
            )

    else:

        lines.append(
            f"Template: {scorecard_path}"
        )

        metadata = scorecard.get(
            "scorecard",
            {},
        )

        if isinstance(metadata, dict):

            lines.append(
                f"Scorecard Name   : "
                f"{metadata.get('name', '-')}"
            )

            lines.append(
                f"Scorecard Version: "
                f"{metadata.get('version', '-')}"
            )

        lines.append("")

        lines.extend(
            format_score_table(
                scorecard_dimensions,
                result_snapshot,
            )
        )

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    lines.extend(
        section("INVESTMENT DECISION")
    )

    decision = extract_decision(
        result_snapshot,
        analysis,
    )

    lines.append(
        format_value(decision)
    )

    # ------------------------------------------------------------------
    # AI Recommendation
    # ------------------------------------------------------------------

    lines.extend(
        section("AI RECOMMENDATION")
    )

    lines.append(
        format_value(
            get_attr(
                analysis,
                "recommendation",
            )
        )
    )

    # ------------------------------------------------------------------
    # Investment Thesis
    # ------------------------------------------------------------------

    lines.extend(
        section("INVESTMENT THESIS")
    )

    lines.append(
        format_value(
            get_attr(
                analysis,
                "investment_thesis",
            )
        )
    )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    metrics = get_attr(
        analysis,
        "metrics_snapshot",
    )

    lines.extend(
        section("METRICS SNAPSHOT")
    )

    lines.append(
        format_value(metrics)
    )

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    lines.extend(
        section("RESULT SNAPSHOT")
    )

    lines.append(
        format_value(result_snapshot)
    )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    input_snapshot = get_attr(
        analysis,
        "input_snapshot",
    )

    lines.extend(
        section("INPUT SNAPSHOT")
    )

    lines.append(
        format_value(input_snapshot)
    )

    # ------------------------------------------------------------------
    # Error
    # ------------------------------------------------------------------

    error_message = get_attr(
        analysis,
        "error_message",
    )

    lines.extend(
        section("ERROR MESSAGE")
    )

    lines.append(
        str(error_message)
        if error_message
        else "None"
    )

    # ------------------------------------------------------------------
    # Quality
    # ------------------------------------------------------------------

    flags = build_quality_flags(
        analysis,
        result_snapshot,
        scorecard_dimensions,
    )

    lines.extend(
        section("QUALITY FLAGS")
    )

    if flags:

        for index, flag in enumerate(
            flags,
            start=1,
        ):
            lines.append(
                f"{index}. {flag}"
            )

    else:

        lines.append(
            "No automatic reporting flags detected."
        )

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    lines.extend(
        [
            "",
            "=" * WIDTH,
            "END OF REPORT",
            "=" * WIDTH,
        ]
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:

    args = parse_args()

    try:
        analysis_id = UUID(
            args.analysis_id
        )

    except ValueError:

        print(
            f"ERROR: Invalid analysis UUID: "
            f"{args.analysis_id}",
            file=sys.stderr,
        )

        return 2

    analysis = load_analysis(
        analysis_id
    )

    if analysis is None:

        print(
            f"ERROR: Analysis not found: "
            f"{analysis_id}",
            file=sys.stderr,
        )

        return 1

    startup_name = load_startup_name(
        analysis.startup_id
    )

    report = build_report(
        analysis,
        startup_name,
    )

    if args.output:

        output_path = Path(
            args.output
        )

        try:

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_path.write_text(
                report,
                encoding="utf-8",
            )

        except OSError as exc:

            print(
                f"ERROR: Could not write report: "
                f"{exc}",
                file=sys.stderr,
            )

            return 1

        print(
            report,
            end="",
        )

        print(
            f"\nReport written to: "
            f"{output_path}",
            file=sys.stderr,
        )

    else:

        print(
            report,
            end="",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
