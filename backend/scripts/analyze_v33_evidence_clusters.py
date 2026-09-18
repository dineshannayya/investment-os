#!/usr/bin/env python3
"""
Deterministic V3.3 semantic-evidence proposition clustering.

Purpose
-------
Analyze accepted V3.3 candidates that were not already reconciled to canonical
AnalysisEvidence and determine whether multiple candidates appear to represent
the same underlying evidence proposition.

This is DIAGNOSTIC ONLY:
- no LLM calls
- no candidate regeneration
- no A.1.2/B.3/B.4.2 execution
- no AnalysisEvidence mutation
- no dimension_evidence.json mutation
- no scores, rankings, or investment decisions

The clustering hierarchy is intentionally conservative:
  1. dimension + field compatibility
  2. exact normalized proposition text
  3. normalized numeric/currency tokens
  4. same extraction/source proximity
  5. segment proximity / signal overlap

The script does NOT declare two candidates to be the same fact solely from
numeric similarity or segment proximity. Such cases are classified as
RELATED_CANDIDATE_CLUSTER and require review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPORT_VERSION = "v33-semantic-evidence-proposition-clustering-v1"
CLASSIFICATIONS = (
    "EXACT_PROPOSITION",
    "LIKELY_SAME_PROPOSITION",
    "RELATED_PROPOSITION",
    "DISTINCT_PROPOSITION",
    "UNRESOLVED",
)

_CURRENCY_RE = re.compile(
    r"(?:₹|rs\.?|inr|\$|usd|eur|€|£)\s*[\d,]+(?:\.\d+)?(?:\s*(?:cr|crore|crores|lakh|lakhs|mn|million|bn|billion|k|m|b))?",
    re.I,
)
_NUMBER_RE = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b")
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w₹$€£%.\-]+")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--startup", required=True)
    p.add_argument("--analysis-input", required=True,
                    help="v33_semantic_evidence_reconciliation_analysis.json")
    p.add_argument("--v33-input", required=True,
                    help="v33_semantic_evidence_validation.json")
    p.add_argument("--output", required=True)
    p.add_argument("--text-output")
    return p.parse_args()


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def norm_text(value: Any) -> str:
    text = str(value or "").replace("\u00a0", " ").strip().lower()
    text = _WS_RE.sub(" ", text)
    text = text.strip(" \t\r\n.,;:!?-")
    return text


def norm_proposition_text(value: Any) -> str:
    text = norm_text(value)
    # Preserve numbers and meaningful punctuation; normalize common quotation
    # and dash variants without attempting semantic rewriting.
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )
    return _WS_RE.sub(" ", text).strip()


def numeric_tokens(value: Any) -> tuple[str, ...]:
    text = norm_text(value)
    currencies = []
    for m in _CURRENCY_RE.finditer(text):
        currencies.append(norm_text(m.group(0)).replace(" ", ""))
    numbers = [m.group(0).replace(",", "") for m in _NUMBER_RE.finditer(text)]
    return tuple(sorted(currencies + numbers))


def source_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("source_id") or ""),
        str(candidate.get("source_sha256") or ""),
        str(candidate.get("extraction_id") or ""),
    )


def segment_index(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("segment_index")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def signal_range(candidate: dict[str, Any]) -> tuple[int, int] | None:
    start = candidate.get("signal_start")
    end = candidate.get("signal_end")
    try:
        if start is None or end is None:
            return None
        return int(start), int(end)
    except (TypeError, ValueError):
        return None


def compatible_key(candidate: dict[str, Any]) -> tuple[str, str]:
    return (
        str(candidate.get("dimension") or ""),
        str(candidate.get("field") or ""),
    )


def candidate_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("candidate_id") or "")


def accepted_candidates(v33: Any) -> list[dict[str, Any]]:
    records = v33.get("records", v33 if isinstance(v33, list) else [])
    out: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        final = record.get("final") or {}
        if not isinstance(final, dict) or final.get("accepted") is not True:
            continue
        candidate = record.get("candidate")
        if isinstance(candidate, dict):
            out.append(candidate)
    out.sort(key=candidate_id)
    return out


def analysis_entries(analysis: Any) -> list[dict[str, Any]]:
    entries = analysis.get("records", [])
    if not isinstance(entries, list):
        return []
    return [x for x in entries if isinstance(x, dict)]


def candidate_is_unmatched(entry: dict[str, Any]) -> bool:
    classes = entry.get("classifications") or []
    if "NEW_EVIDENCE_CANDIDATE" in classes:
        return True
    if "POSSIBLE_DUPLICATE" in classes:
        return True
    return False


def make_record(candidate: dict[str, Any]) -> dict[str, Any]:
    text = str(candidate.get("text") or "")
    return {
        "candidate_id": candidate_id(candidate),
        "dimension": str(candidate.get("dimension") or ""),
        "field": str(candidate.get("field") or ""),
        "document_kind": str(candidate.get("document_kind") or ""),
        "text": text,
        "normalized_text": norm_proposition_text(text),
        "numeric_tokens": list(numeric_tokens(text)),
        "source_id": str(candidate.get("source_id") or ""),
        "source_sha256": str(candidate.get("source_sha256") or ""),
        "extraction_id": str(candidate.get("extraction_id") or ""),
        "segment_index": segment_index(candidate),
        "signal_start": candidate.get("signal_start"),
        "signal_end": candidate.get("signal_end"),
        "source_key": list(source_key(candidate)),
        "compatible_key": list(compatible_key(candidate)),
    }


def ranges_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ra = signal_range(a)
    rb = signal_range(b)
    if not ra or not rb:
        return False
    return max(ra[0], rb[0]) < min(ra[1], rb[1])


def segment_close(a: dict[str, Any], b: dict[str, Any], distance: int = 1) -> bool:
    sa, sb = a.get("segment_index"), b.get("segment_index")
    return (
        sa is not None
        and sb is not None
        and abs(int(sa) - int(sb)) <= distance
    )


def exact_proposition(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        tuple(a["compatible_key"]) == tuple(b["compatible_key"])
        and a["normalized_text"] == b["normalized_text"]
        and bool(a["normalized_text"])
    )


def likely_same_proposition(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if tuple(a["compatible_key"]) != tuple(b["compatible_key"]):
        return False
    if not a["normalized_text"] or not b["normalized_text"]:
        return False

    # Deliberately require a strong textual containment relationship plus
    # either identical numeric tokens or explicit source locality.
    na, nb = a["normalized_text"], b["normalized_text"]
    containment = na in nb or nb in na
    if not containment:
        return False

    same_numbers = tuple(a["numeric_tokens"]) == tuple(b["numeric_tokens"])
    local = (
        tuple(a["source_key"]) == tuple(b["source_key"])
        and (segment_close(a, b, 1) or ranges_overlap(a, b))
    )
    return same_numbers or local


def related_proposition(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if tuple(a["compatible_key"]) != tuple(b["compatible_key"]):
        return False
    if not a["numeric_tokens"] or not b["numeric_tokens"]:
        return False
    if tuple(a["numeric_tokens"]) != tuple(b["numeric_tokens"]):
        return False

    # Same field/dimension and same numeric proposition nearby is useful
    # evidence of relation, but is not enough to collapse the facts.
    same_source = tuple(a["source_key"]) == tuple(b["source_key"])
    return same_source and segment_close(a, b, 2)


def pair_relation(a: dict[str, Any], b: dict[str, Any]) -> str | None:
    if exact_proposition(a, b):
        return "EXACT_PROPOSITION"
    if likely_same_proposition(a, b):
        return "LIKELY_SAME_PROPOSITION"
    if related_proposition(a, b):
        return "RELATED_PROPOSITION"
    return None


class UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {x: x for x in ids}
        self.rank = {x: 0 for x in ids}

    def find(self, x: str) -> str:
        parent = self.parent[x]
        if parent != x:
            self.parent[x] = self.find(parent)
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def cluster_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {x["candidate_id"]: x for x in candidates}
    uf = UnionFind(list(by_id))

    pair_edges: list[dict[str, Any]] = []

    # Exact and strong same-proposition links are eligible for clustering.
    # Related links are retained diagnostically but do not merge clusters.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        groups[tuple(item["compatible_key"])].append(item)

    for group in groups.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                relation = pair_relation(a, b)
                if relation is None:
                    continue
                pair_edges.append({
                    "candidate_a": a["candidate_id"],
                    "candidate_b": b["candidate_id"],
                    "relation": relation,
                })
                if relation in {"EXACT_PROPOSITION", "LIKELY_SAME_PROPOSITION"}:
                    uf.union(a["candidate_id"], b["candidate_id"])

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        components[uf.find(item["candidate_id"])].append(item)

    clusters: list[dict[str, Any]] = []
    for members in components.values():
        members.sort(key=lambda x: x["candidate_id"])
        member_ids = [x["candidate_id"] for x in members]
        digest = hashlib.sha256("|".join(member_ids).encode("utf-8")).hexdigest()[:16]
        edge_types = sorted({
            e["relation"]
            for e in pair_edges
            if e["candidate_a"] in member_ids and e["candidate_b"] in member_ids
        })

        if len(members) == 1:
            classification = "DISTINCT_PROPOSITION"
        elif "EXACT_PROPOSITION" in edge_types:
            classification = "EXACT_PROPOSITION"
        else:
            classification = "LIKELY_SAME_PROPOSITION"

        clusters.append({
            "cluster_id": f"PROP-{digest}",
            "classification": classification,
            "member_count": len(members),
            "dimension": members[0]["dimension"],
            "field": members[0]["field"],
            "members": member_ids,
            "member_texts": [x["text"] for x in members],
            "source_count": len({
                tuple(x["source_key"]) for x in members
            }),
            "segment_indexes": sorted({
                x["segment_index"] for x in members
                if x["segment_index"] is not None
            }),
            "edge_types": edge_types,
        })

    # Related edges are attached after clustering so they can be reviewed
    # without collapsing distinct propositions.
    for cluster in clusters:
        member_set = set(cluster["members"])
        related = [
            e for e in pair_edges
            if e["relation"] == "RELATED_PROPOSITION"
            and (e["candidate_a"] in member_set or e["candidate_b"] in member_set)
        ]
        cluster["related_edges"] = related

    clusters.sort(key=lambda x: x["cluster_id"])
    return clusters, pair_edges


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "=" * 88,
        "V3.3 SEMANTIC EVIDENCE PROPOSITION CLUSTERING",
        "=" * 88,
        f"STARTUP                 : {report['startup']}",
        f"REPORT VERSION          : {report['report_version']}",
        "",
        "POPULATION",
        f"ACCEPTED V3.3          : {report['population']['accepted_candidates']}",
        f"UNMATCHED ANALYZED     : {report['population']['unmatched_candidates']}",
        "",
        "CLUSTERS",
        f"TOTAL CLUSTERS          : {report['cluster_summary']['total_clusters']}",
        f"SINGLETONS              : {report['cluster_summary']['singletons']}",
        f"MULTI-MEMBER            : {report['cluster_summary']['multi_member_clusters']}",
        f"LIKELY SAME PROPOSITION : {report['cluster_summary']['likely_same_proposition_clusters']}",
        f"RELATED EDGES           : {report['cluster_summary']['related_edges']}",
        "",
        "DISTINCT PROPOSITION ESTIMATE",
        f"PROVISIONAL DISTINCT    : {report['cluster_summary']['provisional_distinct_propositions']}",
        "",
        "CLUSTERS WITH MULTIPLE MEMBERS",
    ]

    for cluster in report["clusters"]:
        if cluster["member_count"] <= 1:
            continue
        lines.extend([
            "",
            f"{cluster['cluster_id']}",
            f"  classification : {cluster['classification']}",
            f"  dimension      : {cluster['dimension']}",
            f"  field          : {cluster['field']}",
            f"  members        : {cluster['member_count']}",
            f"  sources        : {cluster['source_count']}",
            f"  edge types     : {', '.join(cluster['edge_types']) or '-'}",
        ])
        for cid, text in zip(cluster["members"], cluster["member_texts"]):
            lines.append(f"    - {cid}: {text}")

    lines.extend([
        "",
        "BY DIMENSION / FIELD",
    ])
    for item in report["by_dimension_field"]:
        lines.append(
            f"  {item['dimension']}/{item['field']}: "
            f"candidates={item['candidates']} "
            f"clusters={item['clusters']} "
            f"singleton_clusters={item['singleton_clusters']} "
            f"multi_member_clusters={item['multi_member_clusters']}"
        )

    lines.extend([
        "",
        "DIAGNOSTIC GUARANTEES",
        "LLM CALLS              : 0",
        "PRODUCTION MUTATION    : NO",
        "CANONICAL EVIDENCE     : NOT MODIFIED",
        "DIMENSION EVIDENCE     : NOT MODIFIED",
        "DECISION / SCORING     : NOT PERFORMED",
        "=" * 88,
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    analysis = load_json(args.analysis_input)
    v33 = load_json(args.v33_input)

    accepted = accepted_candidates(v33)
    accepted_ids = {candidate_id(x) for x in accepted}

    entries = analysis_entries(analysis)
    unmatched_ids = {
        str(x.get("candidate_id") or "")
        for x in entries
        if candidate_is_unmatched(x)
    }

    # The V3.3 artifact is authoritative for candidate payload/provenance.
    # The analysis artifact only selects the unmatched population.
    selected = [
        make_record(candidate)
        for candidate in accepted
        if candidate_id(candidate) in unmatched_ids
    ]

    clusters, edges = cluster_candidates(selected)

    dimension_field = defaultdict(list)
    for item in selected:
        dimension_field[tuple(item["compatible_key"])].append(item)

    by_dimension_field = []
    for key, items in sorted(dimension_field.items()):
        cluster_ids = {
            cluster["cluster_id"]
            for cluster in clusters
            if cluster["dimension"] == key[0] and cluster["field"] == key[1]
            and any(cid in {x["candidate_id"] for x in items} for cid in cluster["members"])
        }
        relevant = [
            c for c in clusters
            if c["cluster_id"] in cluster_ids
        ]
        by_dimension_field.append({
            "dimension": key[0],
            "field": key[1],
            "candidates": len(items),
            "clusters": len(relevant),
            "singleton_clusters": sum(c["member_count"] == 1 for c in relevant),
            "multi_member_clusters": sum(c["member_count"] > 1 for c in relevant),
        })

    multi = [c for c in clusters if c["member_count"] > 1]
    provisional_distinct = len(clusters)

    report = {
        "report_version": REPORT_VERSION,
        "startup": args.startup,
        "diagnostic_only": True,
        "llm_calls": 0,
        "production_mutation": False,
        "canonical_evidence_mutation": False,
        "dimension_evidence_mutation": False,
        "decision_or_scoring": False,
        "population": {
            "accepted_candidates": len(accepted),
            "accepted_candidate_ids": sorted(accepted_ids),
            "unmatched_candidates": len(selected),
            "unmatched_candidate_ids": [x["candidate_id"] for x in selected],
        },
        "cluster_summary": {
            "total_clusters": len(clusters),
            "singletons": sum(c["member_count"] == 1 for c in clusters),
            "multi_member_clusters": len(multi),
            "likely_same_proposition_clusters": sum(
                c["classification"] == "LIKELY_SAME_PROPOSITION" for c in clusters
            ),
            "exact_proposition_clusters": sum(
                c["classification"] == "EXACT_PROPOSITION" for c in clusters
            ),
            "related_edges": sum(
                1 for e in edges if e["relation"] == "RELATED_PROPOSITION"
            ),
            "provisional_distinct_propositions": provisional_distinct,
        },
        "method": {
            "compatible_key": "dimension + field",
            "exact_match": "same normalized text within compatible key",
            "likely_same": "text containment plus identical numeric tokens OR same extraction locality",
            "related": "same compatible key + same numeric tokens + same extraction within 2 segments",
            "related_edges_do_not_merge": True,
            "numeric_only_never_merges": True,
        },
        "by_dimension_field": by_dimension_field,
        "clusters": clusters,
        "pair_edges": edges,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if args.text_output:
        Path(args.text_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.text_output).write_text(
            render_text(report), encoding="utf-8"
        )

    print("=" * 88)
    print("V3.3 SEMANTIC EVIDENCE PROPOSITION CLUSTERING")
    print("=" * 88)
    print(f"ACCEPTED V3.3          : {len(accepted)}")
    print(f"UNMATCHED ANALYZED     : {len(selected)}")
    print(f"TOTAL CLUSTERS         : {len(clusters)}")
    print(f"SINGLETONS             : {sum(c['member_count'] == 1 for c in clusters)}")
    print(f"MULTI-MEMBER CLUSTERS  : {len(multi)}")
    print(f"LIKELY SAME PROPOSITION: {sum(c['classification'] == 'LIKELY_SAME_PROPOSITION' for c in clusters)}")
    print(f"EXACT PROPOSITION      : {sum(c['classification'] == 'EXACT_PROPOSITION' for c in clusters)}")
    print(f"RELATED EDGES          : {sum(1 for e in edges if e['relation'] == 'RELATED_PROPOSITION')}")
    print(f"PROVISIONAL DISTINCT   : {provisional_distinct}")
    print(f"JSON REPORT            : {args.output}")
    if args.text_output:
        print(f"TEXT REPORT            : {args.text_output}")
    print("LLM CALLS              : 0")
    print("PRODUCTION MUTATION    : NO")
    print("STATUS                 : PASS")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
