#!/usr/bin/env python3
"""
Analyze V3.3 semantic-evidence human-review decisions and produce a
deterministic canonical-evidence promotion proposal.

This script is DIAGNOSTIC ONLY.

It:
  - consumes the human-review worksheet produced by
    review_v33_evidence_acceptance.py
  - optionally validates the corresponding V3.3 acceptance-analysis artifact
  - never calls an LLM
  - never mutates AnalysisEvidence
  - never writes dimension_evidence.json
  - converts explicit human review decisions into promotion proposals

Human review is authoritative for this layer. Blank or unrecognized
decisions remain REVIEW_REQUIRED; the script never guesses.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPORT_VERSION = "v33-semantic-evidence-promotion-analysis-v1"

# These values are intentionally identical to the human-review categories.
REVIEW_DECISIONS = {
    "GENUINELY_NEW_EVIDENCE",
    "ALREADY_REPRESENTED_DIFFERENT_WORDING",
    "DUPLICATE_OR_OVERLAP",
    "WRONG_DIMENSION_OR_FIELD",
    "INSUFFICIENT_EVIDENCE",
    "RETAIN_AS_CANONICAL",
    "EXCLUDE",
}

PROMOTION_ACTIONS = {
    "PROMOTE",
    "RETAIN_EXISTING",
    "DO_NOT_PROMOTE",
    "REVIEW_REQUIRED",
}

# Review outcomes that explicitly authorize a new canonical evidence proposal.
PROMOTE_DECISIONS = {
    "GENUINELY_NEW_EVIDENCE",
    "RETAIN_AS_CANONICAL",
}

# Outcomes that explicitly say the proposition is already represented.
RETAIN_EXISTING_DECISIONS = {
    "ALREADY_REPRESENTED_DIFFERENT_WORDING",
}

# Outcomes that explicitly prevent promotion without requiring a semantic
# reinterpretation.
DO_NOT_PROMOTE_DECISIONS = {
    "DUPLICATE_OR_OVERLAP",
    "WRONG_DIMENSION_OR_FIELD",
    "INSUFFICIENT_EVIDENCE",
    "EXCLUDE",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)

    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")

    return value


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def accepted_count_from_v33(v33: dict[str, Any]) -> int | None:
    for container in (
        v33.get("population"),
        v33.get("counts"),
        v33,
    ):
        if not isinstance(container, dict):
            continue

        for key in (
            "final_accepted",
            "accepted",
            "accepted_count",
            "v33_accepted",
        ):
            if container.get(key) is not None:
                return as_int(container[key])

    return None


def analysis_record_index(
    analysis: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not analysis:
        return {}

    records = analysis.get("records", [])
    if not isinstance(records, list):
        return {}

    return {
        str(record.get("candidate_id")): record
        for record in records
        if isinstance(record, dict)
        and record.get("candidate_id")
    }


def extract_review_items(
    review: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    proposition_items = review.get("proposition_review_items")

    if not isinstance(proposition_items, list):
        # Backward-compatible fallback for the review artifact.
        proposition_items = review.get("review_items", [])

    if not isinstance(proposition_items, list):
        proposition_items = []

    ambiguous_items = review.get("ambiguous_review_items", [])
    if not isinstance(ambiguous_items, list):
        ambiguous_items = []

    return (
        [x for x in proposition_items if isinstance(x, dict)],
        [x for x in ambiguous_items if isinstance(x, dict)],
    )


def review_decision(item: dict[str, Any]) -> str:
    """Return the explicit human decision, never infer one."""
    value = item.get("review_decision")

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip().upper()

    # Some manual worksheets may use a selected category list.
    if isinstance(value, list):
        selected = [
            str(x).strip().upper()
            for x in value
            if isinstance(x, str) and x.strip()
        ]
        if len(selected) == 1:
            return selected[0]

    return ""


def proposition_id(item: dict[str, Any]) -> str:
    value = item.get("review_item_id")
    if value:
        return str(value)

    cluster_id = item.get("cluster_id")
    if cluster_id:
        return f"proposition:{cluster_id}"

    candidate_id = item.get("candidate_id")
    return f"proposition:singleton:{candidate_id}"


def candidate_payload(item: dict[str, Any]) -> dict[str, Any]:
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        candidate = {}

    return {
        "candidate_id": str(
            candidate.get("candidate_id")
            or item.get("candidate_id")
            or ""
        ),
        "dimension": (
            candidate.get("dimension")
            or item.get("dimension")
            or ""
        ),
        "field": (
            candidate.get("field")
            or item.get("field")
            or ""
        ),
        "document_kind": (
            candidate.get("document_kind")
            or item.get("document_kind")
            or ""
        ),
        "text": (
            candidate.get("text")
            or item.get("text")
            or ""
        ),
        "signal": (
            candidate.get("signal")
            or item.get("signal")
            or ""
        ),
        "source_id": (
            candidate.get("source_id")
            or item.get("source_id")
            or ""
        ),
        "source_sha256": (
            candidate.get("source_sha256")
            or item.get("source_sha256")
            or ""
        ),
        "extraction_id": (
            candidate.get("extraction_id")
            or item.get("extraction_id")
            or ""
        ),
        "segment_index": (
            candidate.get("segment_index")
            if candidate.get("segment_index") is not None
            else item.get("segment_index")
        ),
        "signal_start": (
            candidate.get("signal_start")
            if candidate.get("signal_start") is not None
            else item.get("signal_start")
        ),
        "signal_end": (
            candidate.get("signal_end")
            if candidate.get("signal_end") is not None
            else item.get("signal_end")
        ),
    }


def canonical_match_payload(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("canonical_match")

    if isinstance(value, dict):
        return value

    return {
        "match_type": item.get("canonical_match_type") or "NO_MATCH"
    }


def promotion_action(
    decision: str,
    *,
    ambiguous: bool = False,
) -> tuple[str, str]:
    if not decision:
        return (
            "REVIEW_REQUIRED",
            "Human review decision is blank.",
        )

    if decision not in REVIEW_DECISIONS:
        return (
            "REVIEW_REQUIRED",
            f"Unrecognized human review decision: {decision}",
        )

    if decision in PROMOTE_DECISIONS:
        if ambiguous:
            return (
                "PROMOTE",
                "Human review explicitly resolved the ambiguous match as "
                "canonical evidence.",
            )
        return (
            "PROMOTE",
            "Human review explicitly identified the proposition as "
            "canonical evidence.",
        )

    if decision in RETAIN_EXISTING_DECISIONS:
        return (
            "RETAIN_EXISTING",
            "Human review states that the proposition is already represented "
            "by existing canonical evidence.",
        )

    if decision in DO_NOT_PROMOTE_DECISIONS:
        return (
            "DO_NOT_PROMOTE",
            f"Human review decision is {decision}.",
        )

    return (
        "REVIEW_REQUIRED",
        "No deterministic promotion policy exists for this decision.",
    )


def build_proposal_item(
    item: dict[str, Any],
    analysis_by_id: dict[str, dict[str, Any]],
    *,
    ambiguous: bool,
) -> dict[str, Any]:
    candidate = candidate_payload(item)
    candidate_id = candidate["candidate_id"]
    analysis = analysis_by_id.get(candidate_id, {})

    decision = review_decision(item)
    action, reason = promotion_action(
        decision,
        ambiguous=ambiguous,
    )

    cluster = item.get("cluster")
    if not isinstance(cluster, dict):
        cluster = {}

    member_ids = item.get("cluster_member_ids")
    if not isinstance(member_ids, list):
        member_ids = cluster.get("member_candidate_ids", [])

    member_ids = [
        str(x)
        for x in member_ids
        if x
    ]

    # For ambiguous items there may be no cluster. Keep the population
    # separate rather than manufacturing a proposition cluster.
    return {
        "proposal_id": (
            f"ambiguous:{candidate_id}"
            if ambiguous
            else proposition_id(item)
        ),
        "review_population": (
            "AMBIGUOUS_CANONICAL_MATCH"
            if ambiguous
            else "PROPOSITION"
        ),
        "candidate_id": candidate_id,
        "candidate": candidate,
        "dimension": candidate["dimension"],
        "field": candidate["field"],
        "cluster_id": (
            str(item.get("cluster_id") or cluster.get("cluster_id") or "")
        ),
        "cluster_classification": (
            item.get("cluster_classification")
            or cluster.get("classification")
            or ""
        ),
        "cluster_member_count": (
            as_int(item.get("cluster_member_count"), len(member_ids))
        ),
        "cluster_member_ids": member_ids,
        "v33_classification": item.get("classification") or "",
        "v33_analysis_reason": (
            analysis.get("classification_reason")
            or item.get("classification_reason")
            or ""
        ),
        "canonical_match_type": (
            item.get("canonical_match_type")
            or canonical_match_payload(item).get("match_type")
            or "NO_MATCH"
        ),
        "canonical_match": canonical_match_payload(item),
        "human_review_decision": decision,
        "promotion_action": action,
        "promotion_reason": reason,
        "review_notes": item.get("review_notes") or "",
        "reviewed_by": item.get("reviewed_by") or "",
        "reviewed_at": item.get("reviewed_at") or "",
        "provenance_complete": all(
            candidate.get(key)
            not in (None, "")
            for key in (
                "candidate_id",
                "source_id",
                "source_sha256",
                "extraction_id",
                "text",
                "dimension",
                "field",
            )
        ),
    }


def build_report(
    *,
    startup: str,
    review: dict[str, Any],
    v33: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    proposition_items, ambiguous_items = extract_review_items(review)
    analysis_by_id = analysis_record_index(analysis)

    proposals = [
        build_proposal_item(
            item,
            analysis_by_id,
            ambiguous=False,
        )
        for item in proposition_items
    ]

    ambiguous_proposals = [
        build_proposal_item(
            item,
            analysis_by_id,
            ambiguous=True,
        )
        for item in ambiguous_items
    ]

    all_items = proposals + ambiguous_proposals
    action_counts = Counter(
        item["promotion_action"]
        for item in all_items
    )

    decision_counts = Counter(
        item["human_review_decision"] or "<BLANK>"
        for item in all_items
    )

    proposition_action_counts = Counter(
        item["promotion_action"]
        for item in proposals
    )

    ambiguous_action_counts = Counter(
        item["promotion_action"]
        for item in ambiguous_proposals
    )

    accepted_count = (
        accepted_count_from_v33(v33)
        if v33 is not None
        else None
    )

    review_population = review.get("population", {})
    if not isinstance(review_population, dict):
        review_population = {}

    expected_propositions = as_int(
        review_population.get("proposition_review_items"),
        len(proposals),
    )
    expected_ambiguous = as_int(
        review_population.get("ambiguous_review_items"),
        len(ambiguous_proposals),
    )

    checks = {
        "review_artifact_diagnostic_only": (
            review.get("diagnostic_only") is True
        ),
        "review_artifact_no_llm": (
            as_int(review.get("llm_calls"), 0) == 0
        ),
        "review_artifact_no_production_mutation": (
            review.get("production_mutation") is False
        ),
        "proposition_review_count_matches_input": (
            len(proposals) == expected_propositions
        ),
        "ambiguous_review_count_matches_input": (
            len(ambiguous_proposals) == expected_ambiguous
        ),
        "promotion_proposal_ids_unique": (
            len({
                str(item["proposal_id"])
                for item in all_items
            }) == len(all_items)
        ),
        "no_unreviewed_item_promoted": all(
            not (
                item["promotion_action"] == "PROMOTE"
                and not item["human_review_decision"]
            )
            for item in all_items
        ),
        "no_invalid_decision_promoted": all(
            not (
                item["promotion_action"] == "PROMOTE"
                and item["human_review_decision"]
                not in REVIEW_DECISIONS
            )
            for item in all_items
        ),
        "promoted_provenance_complete": all(
            item["provenance_complete"]
            for item in all_items
            if item["promotion_action"] == "PROMOTE"
        ),
        # Deterministic accounting partitions. Every review item must land in
        # exactly one promotion action bucket, and the review populations must
        # partition the complete review population. Also verify that the
        # upstream V3.3 acceptance population is internally accounted for.
        "decision_population_partition": (
            promote_count
            + retain_existing_count
            + do_not_promote_count
            + review_required_count
            == total_review_items
        ),
        "review_population_partition": (
            proposition_review_count
            + ambiguous_review_count
            == total_review_items
        ),
        "v33_acceptance_population_partition": (
            v33_accepted_count
            == matched_count
            + ambiguous_count
            + unmatched_count
        ),
        "production_mutation": False,
        "llm_calls": 0,
    }

    if accepted_count is not None:
        checks["v33_accepted_count_available"] = accepted_count >= 0

    return {
        "report_version": REPORT_VERSION,
        "diagnostic_only": True,
        "llm_calls": 0,
        "production_mutation": False,
        "startup": startup,
        "purpose": (
            "Analyze explicit human-review decisions and produce a "
            "diagnostic canonical-evidence promotion proposal. "
            "This artifact does not mutate canonical evidence."
        ),
        "inputs": {
            "acceptance_review": review.get("_input_path", ""),
            "v33_validation": (
                v33.get("_input_path", "")
                if isinstance(v33, dict)
                else ""
            ),
            "acceptance_analysis": (
                analysis.get("_input_path", "")
                if isinstance(analysis, dict)
                else ""
            ),
        },
        "v33": {
            "accepted_candidates": accepted_count,
        },
        "review_population": {
            "proposition_items": len(proposals),
            "ambiguous_items": len(ambiguous_proposals),
            "total_items": len(all_items),
        },
        "human_review_decisions": dict(
            sorted(decision_counts.items())
        ),
        "promotion_actions": dict(
            sorted(action_counts.items())
        ),
        "proposition_promotion_actions": dict(
            sorted(proposition_action_counts.items())
        ),
        "ambiguous_promotion_actions": dict(
            sorted(ambiguous_action_counts.items())
        ),
        "policy": {
            "PROMOTE": sorted(PROMOTE_DECISIONS),
            "RETAIN_EXISTING": sorted(RETAIN_EXISTING_DECISIONS),
            "DO_NOT_PROMOTE": sorted(DO_NOT_PROMOTE_DECISIONS),
            "REVIEW_REQUIRED": (
                "blank or unrecognized human decision"
            ),
            "canonical_mutation": False,
        },
        "proposals": proposals,
        "ambiguous_proposals": ambiguous_proposals,
        "accounting_checks": checks,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "=" * 100,
        "V3.3 SEMANTIC EVIDENCE PROMOTION ANALYSIS",
        "=" * 100,
        f"STARTUP                 : {report['startup']}",
        "",
        "REVIEW POPULATION",
        "-----------------",
    ]

    population = report["review_population"]
    lines.extend(
        [
            f"PROPOSITION ITEMS       : {population['proposition_items']}",
            f"AMBIGUOUS ITEMS         : {population['ambiguous_items']}",
            f"TOTAL ITEMS             : {population['total_items']}",
            "",
            "PROMOTION ACTIONS",
            "-----------------",
        ]
    )

    for key, value in report["promotion_actions"].items():
        lines.append(f"{key:<25}: {value}")

    lines.extend(
        [
            "",
            "HUMAN REVIEW DECISIONS",
            "----------------------",
        ]
    )

    for key, value in report["human_review_decisions"].items():
        lines.append(f"{key:<45}: {value}")

    lines.extend(
        [
            "",
            "PROPOSITION PROMOTION PROPOSALS",
            "-------------------------------",
        ]
    )

    for index, item in enumerate(report["proposals"], 1):
        lines.extend(
            [
                "",
                f"[{index}] {item['promotion_action']}",
                f"Proposal ID             : {item['proposal_id']}",
                f"Candidate ID            : {item['candidate_id']}",
                f"Cluster                 : {item['cluster_id']}",
                f"Cluster members         : {item['cluster_member_count']}",
                f"Dimension               : {item['dimension']}",
                f"Field                   : {item['field']}",
                f"Human decision          : "
                f"{item['human_review_decision'] or '<BLANK>'}",
                f"Promotion reason        : {item['promotion_reason']}",
                "",
                "TEXT",
                "----",
                str(item["candidate"].get("text") or ""),
                "",
                "PROVENANCE",
                "----------",
                f"source_id               : {item['candidate'].get('source_id', '')}",
                f"source_sha256           : {item['candidate'].get('source_sha256', '')}",
                f"extraction_id           : {item['candidate'].get('extraction_id', '')}",
                f"segment_index           : {item['candidate'].get('segment_index', '')}",
            ]
        )

    lines.extend(
        [
            "",
            "AMBIGUOUS CANONICAL-MATCH PROPOSALS",
            "-----------------------------------",
        ]
    )

    for index, item in enumerate(report["ambiguous_proposals"], 1):
        lines.extend(
            [
                "",
                f"[{index}] {item['promotion_action']}",
                f"Proposal ID             : {item['proposal_id']}",
                f"Candidate ID            : {item['candidate_id']}",
                f"Dimension               : {item['dimension']}",
                f"Field                   : {item['field']}",
                f"Canonical match type    : {item['canonical_match_type']}",
                f"Human decision          : "
                f"{item['human_review_decision'] or '<BLANK>'}",
                f"Promotion reason        : {item['promotion_reason']}",
                "",
                "TEXT",
                "----",
                str(item["candidate"].get("text") or ""),
            ]
        )

    lines.extend(
        [
            "",
            "ACCOUNTING CHECKS",
            "-----------------",
        ]
    )

    for key, value in report["accounting_checks"].items():
        lines.append(
            f"{key:<45}: {'PASS' if value else 'FAIL'}"
        )

    lines.extend(
        [
            "",
            "LLM CALLS              : 0",
            "PRODUCTION MUTATION    : NO",
            "STATUS                 : PASS",
            "=" * 100,
        ]
    )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze V3.3 human-review decisions and produce a "
            "diagnostic promotion proposal."
        )
    )
    parser.add_argument("--startup", required=True)
    parser.add_argument("--review-input", required=True, type=Path)
    parser.add_argument("--v33-input", type=Path)
    parser.add_argument("--analysis-input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--text-output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        review = load_json(args.review_input)
        review["_input_path"] = str(args.review_input)

        v33 = None
        if args.v33_input is not None:
            v33 = load_json(args.v33_input)
            v33["_input_path"] = str(args.v33_input)

        analysis = None
        if args.analysis_input is not None:
            analysis = load_json(args.analysis_input)
            analysis["_input_path"] = str(args.analysis_input)

        report = build_report(
            startup=args.startup,
            review=review,
            v33=v33,
            analysis=analysis,
        )

        if not all(report["accounting_checks"].values()):
            raise RuntimeError(
                "Promotion analysis accounting failed: "
                f"{report['accounting_checks']}"
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.text_output.parent.mkdir(parents=True, exist_ok=True)

        args.output.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        args.text_output.write_text(
            render_text(report),
            encoding="utf-8",
        )

        print("=" * 100)
        print("V3.3 SEMANTIC EVIDENCE PROMOTION ANALYSIS")
        print("=" * 100)
        print(
            f"PROPOSITION ITEMS       : "
            f"{report['review_population']['proposition_items']}"
        )
        print(
            f"AMBIGUOUS ITEMS         : "
            f"{report['review_population']['ambiguous_items']}"
        )
        print(
            f"TOTAL ITEMS             : "
            f"{report['review_population']['total_items']}"
        )

        for action in (
            "PROMOTE",
            "RETAIN_EXISTING",
            "DO_NOT_PROMOTE",
            "REVIEW_REQUIRED",
        ):
            print(
                f"{action:<25}: "
                f"{report['promotion_actions'].get(action, 0)}"
            )

        print(f"JSON REPORT             : {args.output}")
        print(f"TEXT REPORT             : {args.text_output}")
        print("LLM CALLS               : 0")
        print("PRODUCTION MUTATION     : NO")
        print("STATUS                  : PASS")
        print("=" * 100)

        return 0

    except Exception as exc:
        print("STATUS                  : FAIL", file=sys.stderr)
        print(
            f"ERROR                   : "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
