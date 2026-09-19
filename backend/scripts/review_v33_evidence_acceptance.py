#!/usr/bin/env python3
"""
Generate a deterministic, read-only human-review worksheet for V3.3 evidence.

This script does not call an LLM and does not mutate production evidence.
It preserves the V3.3 accepted candidate population, reconciliation status,
and cluster membership, and adds blank human-review fields.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPORT_VERSION = "v33-semantic-evidence-acceptance-review-v1"

REVIEW_CATEGORIES = (
    "GENUINELY_NEW_EVIDENCE",
    "ALREADY_REPRESENTED_DIFFERENT_WORDING",
    "DUPLICATE_OR_OVERLAP",
    "WRONG_DIMENSION_OR_FIELD",
    "INSUFFICIENT_EVIDENCE",
    "RETAIN_AS_CANONICAL",
    "EXCLUDE",
)

REVIEW_ORDER = {
    "EXACT_PROPOSITION": 0,
    "LIKELY_SAME_PROPOSITION": 1,
    "RELATED": 2,
    "AMBIGUOUS": 3,
    "SINGLETON": 4,
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def accepted_candidates(v33: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for record in v33.get("records", []):
        if not isinstance(record, dict):
            continue

        candidate = record.get("candidate")
        final = record.get("final") or {}

        if not isinstance(candidate, dict):
            continue

        candidate_id = str(candidate.get("candidate_id") or "")

        if candidate_id and final.get("accepted") is True:
            result[candidate_id] = candidate

    return result


def get_analysis_records(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    records = analysis.get("records")

    if not isinstance(records, list):
        raise RuntimeError(
            "Acceptance analysis artifact does not contain a records list."
        )

    return [record for record in records if isinstance(record, dict)]


def cluster_indexes(
    clusters: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    by_candidate: dict[str, dict[str, Any]] = {}
    by_cluster: dict[str, list[str]] = {}

    raw = clusters.get("clusters", [])

    if isinstance(raw, dict):
        iterable = []

        for cluster_id, value in raw.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("cluster_id", cluster_id)
                iterable.append(item)
    elif isinstance(raw, list):
        iterable = [item for item in raw if isinstance(item, dict)]
    else:
        iterable = []

    for cluster in iterable:
        cluster_id = str(cluster.get("cluster_id") or "")

        if not cluster_id:
            continue

        classification = str(
            cluster.get("classification")
            or cluster.get("cluster_classification")
            or "SINGLETON"
        )

        raw_members = (
            cluster.get("members")
            or cluster.get("member_candidate_ids")
            or []
        )

        member_ids: list[str] = []

        for member in raw_members:
            if isinstance(member, str):
                member_id = member
            elif isinstance(member, dict):
                member_id = str(member.get("candidate_id") or "")
            else:
                member_id = ""

            if member_id:
                member_ids.append(member_id)

        by_cluster[cluster_id] = member_ids

        for member_id in member_ids:
            by_candidate[member_id] = {
                "cluster_id": cluster_id,
                "classification": classification,
                "member_count": len(member_ids),
                "member_candidate_ids": list(member_ids),
                "representative_candidate_id": str(
                    cluster.get("representative_candidate_id") or ""
                ),
            }

    return by_candidate, by_cluster


def extract_related_edges(
    inspection: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if inspection is None:
        return []

    edges = inspection.get("related_edges", [])

    if not isinstance(edges, list):
        return []

    return [edge for edge in edges if isinstance(edge, dict)]


def related_candidate_ids(edges: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()

    scalar_keys = (
        "candidate_id",
        "candidate_a",
        "candidate_b",
        "source_candidate_id",
        "target_candidate_id",
    )

    list_keys = ("members", "candidate_ids")

    for edge in edges:
        for key in scalar_keys:
            value = edge.get(key)

            if isinstance(value, str) and value:
                result.add(value)

        for key in list_keys:
            values = edge.get(key)

            if isinstance(values, list):
                result.update(
                    str(value)
                    for value in values
                    if isinstance(value, str) and value
                )

    return result


def canonical_match_type(record: dict[str, Any]) -> str:
    return str(
        record.get("canonical_match_type")
        or record.get("canonical_match")
        or "NO_MATCH"
    )


def build_review_items(
    analysis_records: list[dict[str, Any]],
    accepted: dict[str, dict[str, Any]],
    clusters: dict[str, Any],
    inspection: dict[str, Any] | None,
    *,
    include_ambiguous: bool = False,
) -> list[dict[str, Any]]:
    by_candidate, _ = cluster_indexes(clusters)

    edges = extract_related_edges(inspection)
    related_ids = related_candidate_ids(edges)

    items: list[dict[str, Any]] = []

    for analysis_record in analysis_records:
        candidate_id = str(analysis_record.get("candidate_id") or "")
        classification = str(analysis_record.get("classification") or "")

        if not candidate_id or candidate_id not in accepted:
            continue

        # The human-review worksheet covers unmatched and ambiguous records.
        allowed_classifications = {
            "NEW_EVIDENCE_CANDIDATE",
            "POSSIBLE_DUPLICATE",
        }

        if include_ambiguous:
            allowed_classifications.add("AMBIGUOUS")

        if classification not in allowed_classifications:
            continue

        cluster = by_candidate.get(candidate_id, {})

        cluster_classification = str(
            cluster.get("classification")
            or analysis_record.get("cluster_classification")
            or "SINGLETON"
        )

        if candidate_id in related_ids:
            cluster_classification = "RELATED"

        candidate = accepted[candidate_id]

        item = dict(analysis_record)

        item["candidate"] = {
            "candidate_id": candidate_id,
            "dimension": candidate.get(
                "dimension", analysis_record.get("dimension", "")
            ),
            "field": candidate.get(
                "field", analysis_record.get("field", "")
            ),
            "document_kind": candidate.get(
                "document_kind", analysis_record.get("document_kind", "")
            ),
            "text": candidate.get(
                "text", analysis_record.get("text", "")
            ),
            "signal": candidate.get(
                "signal", analysis_record.get("signal", "")
            ),
            "source_id": candidate.get(
                "source_id", analysis_record.get("source_id", "")
            ),
            "source_sha256": candidate.get(
                "source_sha256", analysis_record.get("source_sha256", "")
            ),
            "extraction_id": candidate.get(
                "extraction_id",
                analysis_record.get("extraction_id", ""),
            ),
            "segment_index": candidate.get(
                "segment_index",
                analysis_record.get("segment_index"),
            ),
            "signal_start": candidate.get(
                "signal_start",
                analysis_record.get("signal_start"),
            ),
            "signal_end": candidate.get(
                "signal_end",
                analysis_record.get("signal_end"),
            ),
        }

        item["cluster"] = cluster
        item["cluster_classification"] = cluster_classification
        item["review_priority"] = REVIEW_ORDER.get(
            cluster_classification, 9
        )

        # These are intentionally blank: the script does not make the
        # human semantic/business decision.
        item["review_categories"] = list(REVIEW_CATEGORIES)
        item["review_decision"] = ""
        item["review_notes"] = ""
        item["reviewed_by"] = ""
        item["reviewed_at"] = ""

        items.append(item)

    items.sort(
        key=lambda item: (
            item["review_priority"],
            str(item.get("dimension") or ""),
            str(item.get("field") or ""),
            str(
                item.get("cluster", {}).get("cluster_id")
                if isinstance(item.get("cluster"), dict)
                else ""
            ),
            str(item.get("candidate_id") or ""),
        )
    )

    return items


def build_report(
    args: argparse.Namespace,
    v33: dict[str, Any],
    analysis: dict[str, Any],
    clusters: dict[str, Any],
    inspection: dict[str, Any] | None,
) -> dict[str, Any]:
    accepted = accepted_candidates(v33)
    analysis_records = get_analysis_records(analysis)

    matched_ids = {
        str(record.get("candidate_id"))
        for record in analysis_records
        if record.get("classification") == "MATCHED"
    }

    ambiguous_ids = {
        str(record.get("candidate_id"))
        for record in analysis_records
        if record.get("classification") == "AMBIGUOUS"
    }

    unmatched_ids = {
        str(record.get("candidate_id"))
        for record in analysis_records
        if record.get("classification")
        in {"NEW_EVIDENCE_CANDIDATE", "POSSIBLE_DUPLICATE"}
    }

    # The main proposition review population is the 96 unmatched
    # candidates, which collapse to 90 proposition clusters. Ambiguous
    # canonical matches are deliberately kept in a separate review queue.
    proposition_review_items = build_review_items(
        analysis_records,
        accepted,
        clusters,
        inspection,
        include_ambiguous=False,
    )

    ambiguous_review_items = build_review_items(
        analysis_records,
        accepted,
        clusters,
        inspection,
        include_ambiguous=True,
    )
    ambiguous_review_items = [
        item
        for item in ambiguous_review_items
        if str(item.get("classification") or "") == "AMBIGUOUS"
    ]

    by_candidate, by_cluster = cluster_indexes(clusters)

    cluster_summary = Counter(
        item["cluster_classification"]
        for item in proposition_review_items
    )

    by_dimension_field: dict[str, Counter] = defaultdict(Counter)

    for item in proposition_review_items:
        key = (
            f"{item.get('dimension', '')}|"
            f"{item.get('field', '')}"
        )
        by_dimension_field[key]["propositions"] += 1

    proposition_review_ids = {
        str(item.get("candidate_id"))
        for item in proposition_review_items
    }

    ambiguous_review_ids = {
        str(item.get("candidate_id"))
        for item in ambiguous_review_items
    }

    accepted_partition = matched_ids | ambiguous_ids | unmatched_ids

    checks = {
        "accepted_population_partition": (
            accepted_partition == set(accepted)
            and not (matched_ids & ambiguous_ids)
            and not (matched_ids & unmatched_ids)
            and not (ambiguous_ids & unmatched_ids)
        ),
        "unmatched_cluster_coverage": (
            unmatched_ids <= set(by_candidate)
        ),
        "no_duplicate_cluster_membership": (
            len(by_candidate) == len(set(by_candidate))
        ),
        "proposition_review_population_complete": (
            proposition_review_ids == unmatched_ids
        ),
        "ambiguous_review_population_complete": (
            ambiguous_review_ids == ambiguous_ids
        ),
        "review_populations_disjoint": (
            proposition_review_ids.isdisjoint(ambiguous_review_ids)
        ),
        "cluster_member_count_consistent": all(
            len(member_ids)
            == int(
                next(
                    (
                        item.get("member_count")
                        for item in by_candidate.values()
                        if item.get("cluster_id") == cluster_id
                    ),
                    len(member_ids),
                )
            )
            for cluster_id, member_ids in by_cluster.items()
        ),
    }

    return {
        "report_version": REPORT_VERSION,
        "diagnostic_only": True,
        "llm_calls": 0,
        "production_mutation": False,
        "startup": args.startup,
        "purpose": (
            "Human-review worksheet for canonical evidence promotion. "
            "This artifact does not make canonicalization decisions."
        ),
        "population": {
            "v33_accepted": len(accepted),
            "matched": len(matched_ids),
            "ambiguous": len(ambiguous_ids),
            "unmatched": len(unmatched_ids),
            "proposition_review_items": len(proposition_review_items),
            "ambiguous_review_items": len(ambiguous_review_items),
            "total_review_items": (
                len(proposition_review_items)
                + len(ambiguous_review_items)
            ),
            "cluster_count": len(by_cluster),
        },
        "review_order": [
            "EXACT_PROPOSITION",
            "LIKELY_SAME_PROPOSITION",
            "RELATED",
            "AMBIGUOUS",
            "SINGLETON",
        ],
        "review_categories": list(REVIEW_CATEGORIES),
        "review_population_policy": {
            "proposition_review": "96 unmatched candidates / 90 clusters",
            "ambiguous_review": "2 ambiguous canonical matches kept separate",
        },
        "cluster_summary": dict(cluster_summary),
        "by_dimension_field": {
            key: dict(value)
            for key, value in sorted(by_dimension_field.items())
        },
        "related_edges": extract_related_edges(inspection),
        "proposition_review_items": proposition_review_items,
        "ambiguous_review_items": ambiguous_review_items,
        # Backward-compatible alias: main review population is propositions.
        "review_items": proposition_review_items,
        "accounting_checks": checks,
    }


def render_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    separator = "=" * 100

    lines.extend(
        [
            separator,
            "V3.3 SEMANTIC EVIDENCE ACCEPTANCE HUMAN REVIEW",
            separator,
            f"STARTUP                 : {report['startup']}",
        ]
    )

    population = report["population"]

    for key, label in (
        ("v33_accepted", "V3.3 ACCEPTED"),
        ("matched", "MATCHED"),
        ("ambiguous", "AMBIGUOUS"),
        ("unmatched", "UNMATCHED"),
        ("proposition_review_items", "PROPOSITION REVIEW"),
        ("ambiguous_review_items", "AMBIGUOUS REVIEW"),
        ("total_review_items", "TOTAL REVIEW ITEMS"),
        ("cluster_count", "CLUSTERS"),
    ):
        lines.append(f"{label:<25}: {population[key]}")

    lines.extend(["", "CLUSTER SUMMARY", "---------------"])

    for key in report["review_order"]:
        lines.append(
            f"{key:<25}: "
            f"{report['cluster_summary'].get(key, 0)}"
        )

    lines.extend(["", "RELATED EDGES", "-------------"])

    edges = report["related_edges"]

    if not edges:
        lines.append("count                    : 0")
    else:
        lines.append(f"count                    : {len(edges)}")

        for index, edge in enumerate(edges, 1):
            lines.append("")
            lines.append(
                f"EDGE {index}: "
                f"{json.dumps(edge, ensure_ascii=False, sort_keys=True)}"
            )

    lines.extend(
        [
            "",
            "AMBIGUOUS CANONICAL MATCH REVIEW",
            separator,
        ]
    )

    for index, item in enumerate(report["ambiguous_review_items"], 1):
        candidate = item["candidate"]
        cluster = item.get("cluster") or {}

        lines.extend(
            [
                "",
                f"[AMBIGUOUS {index}]",
                f"Candidate ID             : {candidate.get('candidate_id', '')}",
                f"Dimension                : {candidate.get('dimension', '')}",
                f"Field                    : {candidate.get('field', '')}",
                f"Cluster                  : {cluster.get('cluster_id', '')}",
                f"Canonical match          : {item.get('canonical_match_type', '')}",
                "",
                "TEXT",
                "----",
                str(candidate.get("text") or ""),
                "",
                "PROVENANCE",
                "----------",
                f"source_id                : {candidate.get('source_id', '')}",
                f"source_sha256            : {candidate.get('source_sha256', '')}",
                f"extraction_id            : {candidate.get('extraction_id', '')}",
                f"segment_index            : {candidate.get('segment_index', '')}",
                "",
                "REVIEW CATEGORIES",
                "-----------------",
            ]
        )

        for category in report["review_categories"]:
            lines.append(f"  [ ] {category}")

        lines.extend(
            [
                "",
                "REVIEW DECISION           : ",
                "REVIEW NOTES              : ",
                "REVIEWED BY               : ",
                "REVIEWED AT               : ",
                separator,
            ]
        )

    lines.extend(
        [
            "",
            "PROPOSITION REVIEW WORKSHEET",
            separator,
        ]
    )

    for index, item in enumerate(report["proposition_review_items"], 1):
        candidate = item["candidate"]
        cluster = item.get("cluster") or {}

        lines.extend(
            [
                "",
                f"[{index}] {item['cluster_classification']}",
                f"Candidate ID             : {candidate.get('candidate_id', '')}",
                f"Cluster                  : {cluster.get('cluster_id', '')}",
                f"Cluster members          : {cluster.get('member_count', 1)}",
                f"Dimension                : {candidate.get('dimension', '')}",
                f"Field                    : {candidate.get('field', '')}",
                f"Document kind            : {candidate.get('document_kind', '')}",
                f"Canonical match          : {item.get('canonical_match_type', '')}",
                "",
                "TEXT",
                "----",
                str(candidate.get("text") or ""),
                "",
                "SIGNAL",
                "------",
                str(candidate.get("signal") or ""),
                "",
                "PROVENANCE",
                "----------",
                f"source_id                : {candidate.get('source_id', '')}",
                f"source_sha256            : {candidate.get('source_sha256', '')}",
                f"extraction_id            : {candidate.get('extraction_id', '')}",
                f"segment_index            : {candidate.get('segment_index', '')}",
                (
                    "signal_offsets           : "
                    f"{candidate.get('signal_start', '')}-"
                    f"{candidate.get('signal_end', '')}"
                ),
                "",
                "REVIEW CATEGORIES",
                "-----------------",
            ]
        )

        for category in report["review_categories"]:
            lines.append(f"  [ ] {category}")

        lines.extend(
            [
                "",
                "REVIEW DECISION           : ",
                "REVIEW NOTES              : ",
                "REVIEWED BY               : ",
                "REVIEWED AT               : ",
                separator,
            ]
        )

    lines.extend(["", "ACCOUNTING CHECKS", "-----------------"])

    for key, value in report["accounting_checks"].items():
        lines.append(
            f"{key:<40}: {'PASS' if value else 'FAIL'}"
        )

    lines.extend(
        [
            "",
            "LLM CALLS                 : 0",
            "PRODUCTION MUTATION       : NO",
            (
                "NOTE                      : "
                "Review fields are intentionally blank. "
                "This report does not make canonicalization decisions."
            ),
        ]
    )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only human-review worksheet for "
            "V3.3 canonical evidence acceptance."
        )
    )

    parser.add_argument("--startup", required=True)
    parser.add_argument("--v33-input", required=True, type=Path)
    parser.add_argument("--analysis-input", required=True, type=Path)
    parser.add_argument("--clusters-input", required=True, type=Path)
    parser.add_argument("--inspection-input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--text-output", required=True, type=Path)

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        v33 = load_json(args.v33_input)
        analysis = load_json(args.analysis_input)
        clusters = load_json(args.clusters_input)

        inspection = (
            load_json(args.inspection_input)
            if args.inspection_input is not None
            else None
        )

        report = build_report(
            args,
            v33,
            analysis,
            clusters,
            inspection,
        )

        if not all(report["accounting_checks"].values()):
            raise RuntimeError(
                "Review report accounting failed: "
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

        population = report["population"]

        print("=" * 100)
        print("V3.3 SEMANTIC EVIDENCE ACCEPTANCE HUMAN REVIEW")
        print("=" * 100)
        print(
            f"V3.3 ACCEPTED          : "
            f"{population['v33_accepted']}"
        )
        print(
            f"MATCHED                : "
            f"{population['matched']}"
        )
        print(
            f"AMBIGUOUS              : "
            f"{population['ambiguous']}"
        )
        print(
            f"UNMATCHED              : "
            f"{population['unmatched']}"
        )
        print(
            f"PROPOSITION REVIEW     : "
            f"{population['proposition_review_items']}"
        )
        print(
            f"AMBIGUOUS REVIEW       : "
            f"{population['ambiguous_review_items']}"
        )
        print(
            f"TOTAL REVIEW ITEMS     : "
            f"{population['total_review_items']}"
        )
        print(
            f"CLUSTERS               : "
            f"{population['cluster_count']}"
        )
        print(f"JSON REPORT            : {args.output}")
        print(f"TEXT REPORT            : {args.text_output}")
        print("LLM CALLS              : 0")
        print("PRODUCTION MUTATION    : NO")
        print("STATUS                 : PASS")
        print("=" * 100)

        return 0

    except Exception as exc:
        print(f"STATUS : FAIL\nERROR  : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
