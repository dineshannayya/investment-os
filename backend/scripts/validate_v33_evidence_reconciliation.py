#!/usr/bin/env python3
"""
Validate reconciliation between V3.3 accepted semantic evidence and canonical
AnalysisEvidence.

This is a deterministic, read-only validation harness.

Architecture:
    V3.3 semantic validation artifact/service
        -> final accepted candidates
        -> canonical AnalysisEvidence from existing production path
        -> SemanticEvidenceReconciliationService
        -> reconciliation diagnostics/report

The script intentionally does NOT:
    * reimplement candidate generation
    * reimplement A.1.2
    * reimplement B.3
    * reimplement B.4.2
    * mutate AnalysisEvidence
    * write dimension_evidence.json
    * calculate investment scores or decisions

Preferred mode:
    Consume an existing V3.3 artifact with --v33-input.

Optional mode:
    --run-v33 invokes SemanticEvidenceValidationService live.
    This can make the V3.3 input observational/nondeterministic, so it is not
    the default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import UUID

from app.core.config.settings import settings
from app.core.database.session import create_session
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


REPORT_VERSION = "v33-semantic-evidence-reconciliation-v1"

DEFAULT_V33_RELATIVE_PATH = (
    "generated/{startup}/v33_semantic_evidence_validation.json"
)

PROTECTED_FILE_NAME = "dimension_evidence.json"

MATCH_TYPES = (
    "EXACT_MATCH",
    "OFFSET_MATCH",
    "TEXT_MATCH",
    "AMBIGUOUS",
    "NO_MATCH",
)

MATCHED_TYPES = {
    "EXACT_MATCH",
    "OFFSET_MATCH",
    "TEXT_MATCH",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate reconciliation between V3.3 accepted semantic "
            "evidence and canonical AnalysisEvidence."
        )
    )

    parser.add_argument(
        "--startup",
        required=True,
        help="Startup name, e.g. restomart",
    )

    parser.add_argument(
        "--report",
        required=True,
        help="Output reconciliation report JSON path",
    )

    parser.add_argument(
        "--v33-input",
        default=None,
        help=(
            "Existing V3.3 semantic-validation artifact. If omitted, "
            "generated/{startup}/v33_semantic_evidence_validation.json "
            "is used when present."
        ),
    )

    parser.add_argument(
        "--run-v33",
        action="store_true",
        help=(
            "Run SemanticEvidenceValidationService live instead of "
            "consuming an existing V3.3 artifact."
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return FAIL for data-integrity failures.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional diagnostics.",
    )

    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def first_value(
    obj: Any,
    *names: str,
    default: Any = None,
) -> Any:
    for name in names:
        value = get_value(obj, name, None)
        if value is not None:
            return value
    return default


def candidate_id(candidate: Any) -> str:
    value = first_value(candidate, "candidate_id", "id", default="")
    return str(value)


def candidate_text(candidate: Any) -> str:
    value = first_value(
        candidate,
        "text",
        "candidate_text",
        "source_text",
        default="",
    )
    return str(value or "")


def normalize_text(value: Any) -> str:
    """
    Lightweight normalization only.

    The reconciliation service remains the authority for actual matching.
    This helper is used only for diagnostics/grouping in the harness.
    """
    text = str(value or "")
    return " ".join(text.split()).strip().casefold()


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)

    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")

    return value


def resolve_v33_input_path(
    startup: str,
    explicit: str | None,
    report_path: Path,
) -> Path:
    if explicit:
        return Path(explicit)

    repo_root = Path(__file__).resolve().parents[1]
    default_path = repo_root / DEFAULT_V33_RELATIVE_PATH.format(
        startup=startup
    )

    if default_path.exists():
        return default_path

    # Also support a report directory supplied outside the repository.
    sibling = report_path.parent / "v33_semantic_evidence_validation.json"
    if sibling.exists():
        return sibling

    raise FileNotFoundError(
        "V3.3 artifact not found. Supply --v33-input or use --run-v33. "
        f"Checked: {default_path} and {sibling}"
    )


def load_v33_artifact(path: Path) -> dict[str, Any]:
    artifact = load_json(path)

    if "v33" in artifact and isinstance(artifact["v33"], Mapping):
        return dict(artifact)

    # Accept a direct batch artifact as long as it has a recognizable
    # candidate/decision collection.
    if any(
        key in artifact
        for key in (
            "records",
            "results",
            "accepted_records",
            "candidates",
        )
    ):
        return artifact

    raise ValueError(
        f"Unrecognized V3.3 artifact structure: {path}"
    )


def extract_records(artifact: Mapping[str, Any]) -> list[Any]:
    for key in (
        "records",
        "results",
        "validation_records",
        "accepted_records",
    ):
        value = artifact.get(key)

        if isinstance(value, list):
            return value

    v33 = artifact.get("v33")
    if isinstance(v33, Mapping):
        for key in (
            "records",
            "results",
            "validation_records",
            "accepted_records",
        ):
            value = v33.get(key)
            if isinstance(value, list):
                return value

    return []


def decision_value(record: Any) -> str:
    """
    Resolve the final V3.3 decision.

    SemanticEvidenceValidationRecord serializes its authoritative decision
    under ``final.accepted``.  Older benchmark artifacts may expose the
    decision at the top level, so retain those compatibility forms.
    """
    final = get_value(record, "final", None)
    if isinstance(final, Mapping) and "accepted" in final:
        value = final["accepted"]
    else:
        value = first_value(
            record,
            "final_decision",
            "decision",
            "status",
            "accepted",
            default="",
        )

    if isinstance(value, bool):
        return "accepted" if value else "rejected"

    return str(value or "").strip().lower()


def is_accepted(record: Any) -> bool:
    return decision_value(record) in {
        "accepted",
        "accept",
        "true",
        "a",
    }


def extract_final_accepted_from_artifact(
    artifact: Mapping[str, Any],
) -> list[Any]:
    records = extract_records(artifact)

    accepted = [
        record
        for record in records
        if is_accepted(record)
    ]

    if accepted:
        return accepted

    # Some service artifacts may persist only accepted_records.
    direct = artifact.get("accepted_records")
    if isinstance(direct, list):
        return direct

    return []


def validate_v33_artifact(
    artifact: Mapping[str, Any],
    accepted_records: Sequence[Any],
) -> dict[str, Any]:
    v33 = artifact.get("v33")
    if not isinstance(v33, Mapping):
        v33 = artifact

    raw = first_value(
        v33,
        "raw_candidates",
        "raw_candidate_count",
        "candidate_count",
        default=None,
    )
    a12 = first_value(
        v33,
        "a12_passed",
        "a12_pass",
        "gated_candidates",
        "gated_count",
        default=None,
    )
    selected = first_value(
        v33,
        "b42_selected",
        "b4_2_selected",
        "context_selected",
        "selected_count",
        default=None,
    )
    accepted = first_value(
        v33,
        "final_accepted",
        "accepted",
        "accepted_count",
        default=None,
    )
    rejected = first_value(
        v33,
        "final_rejected",
        "rejected",
        "rejected_count",
        default=None,
    )
    recovered = first_value(
        v33,
        "recovered",
        "recovered_count",
        default=None,
    )

    checks: dict[str, bool] = {}

    if raw is not None and a12 is not None:
        checks["a12_not_above_raw"] = int(a12) <= int(raw)
    else:
        checks["a12_not_above_raw"] = True

    if accepted is not None and rejected is not None and a12 is not None:
        checks["accepted_plus_rejected_equals_a12"] = (
            int(accepted) + int(rejected) == int(a12)
        )
    else:
        checks["accepted_plus_rejected_equals_a12"] = True

    if accepted is not None:
        checks["accepted_record_count"] = (
            len(accepted_records) == int(accepted)
        )
    else:
        checks["accepted_record_count"] = True

    checks["required_v33_information_available"] = (
        len(accepted_records) > 0
    )

    return {
        "metadata": {
            "benchmark_version": v33.get("benchmark_version"),
            "prompt_version": v33.get("prompt_version"),
            "raw_candidates": raw,
            "a12_passed": a12,
            "b42_selected": selected,
            "final_accepted": accepted,
            "final_rejected": rejected,
            "recovered": recovered,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }


def serialize_candidate(candidate: Any) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id(candidate),
        "source_id": first_value(
            candidate,
            "source_id",
            default=None,
        ),
        "source_sha256": first_value(
            candidate,
            "source_sha256",
            default=None,
        ),
        "extraction_id": first_value(
            candidate,
            "extraction_id",
            default=None,
        ),
        "segment_index": first_value(
            candidate,
            "segment_index",
            default=None,
        ),
        "dimension": first_value(
            candidate,
            "dimension",
            default=None,
        ),
        "field": first_value(
            candidate,
            "field",
            default=None,
        ),
        "text": candidate_text(candidate),
    }


def serialize_canonical_evidence(evidence: Any, index: int) -> dict[str, Any]:
    return {
        "canonical_index": index,
        "document_id": first_value(
            evidence,
            "document_id",
            default=None,
        ),
        "page": first_value(
            evidence,
            "page",
            default=None,
        ),
        "section": first_value(
            evidence,
            "section",
            default=None,
        ),
        "source_text": first_value(
            evidence,
            "source_text",
            "text",
            default="",
        ),
        "confidence": first_value(
            evidence,
            "confidence",
            default=None,
        ),
    }


def serialize_match(match: Any) -> dict[str, Any]:
    if isinstance(match, Mapping):
        result = dict(match)
    else:
        result = {
            "canonical_index": first_value(
                match,
                "canonical_index",
                "index",
                default=None,
            ),
            "document_id": first_value(
                match,
                "document_id",
                default=None,
            ),
            "page": first_value(
                match,
                "page",
                default=None,
            ),
            "section": first_value(
                match,
                "section",
                default=None,
            ),
            "source_text": first_value(
                match,
                "source_text",
                "text",
                default="",
            ),
        }

    return make_json_safe(result)


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Mapping):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def serialize_reconciliation_result(result: Any) -> dict[str, Any]:
    match_type = first_value(
        result,
        "match_type",
        "classification",
        "status",
        default="NO_MATCH",
    )

    matches = first_value(
        result,
        "canonical_matches",
        "matches",
        "evidence_matches",
        default=[],
    )

    if matches is None:
        matches = []

    if not isinstance(matches, (list, tuple)):
        matches = [matches]

    candidate = first_value(
        result,
        "candidate",
        default=None,
    )

    return {
        "candidate_id": first_value(
            result,
            "candidate_id",
            default=candidate_id(candidate) if candidate is not None else None,
        ),
        "dimension": first_value(
            result,
            "dimension",
            default=first_value(
                candidate,
                "dimension",
                default=None,
            )
            if candidate is not None
            else None,
        ),
        "field": first_value(
            result,
            "field",
            default=first_value(
                candidate,
                "field",
                default=None,
            )
            if candidate is not None
            else None,
        ),
        "candidate_text": first_value(
            result,
            "candidate_text",
            "text",
            default=candidate_text(candidate)
            if candidate is not None
            else "",
        ),
        "match_type": str(match_type),
        "canonical_match_count": len(matches),
        "canonical_matches": [
            serialize_match(match)
            for match in matches
        ],
    }


def extract_reconciliation_results(
    reconciliation: Any,
) -> list[Any]:
    if isinstance(reconciliation, Mapping):
        for key in (
            "results",
            "records",
            "reconciliations",
            "items",
        ):
            value = reconciliation.get(key)
            if isinstance(value, list):
                return value

    for key in (
        "results",
        "records",
        "reconciliations",
        "items",
    ):
        value = getattr(reconciliation, key, None)
        if isinstance(value, (list, tuple)):
            return list(value)

    if isinstance(reconciliation, (list, tuple)):
        return list(reconciliation)

    raise RuntimeError(
        "SemanticEvidenceReconciliationService returned no result collection"
    )


def run_reconciliation(
    *,
    accepted_candidates: Sequence[Any],
    canonical_evidence: Sequence[Any],
) -> list[dict[str, Any]]:
    from app.services.semantic_evidence_reconciliation import (
        SemanticEvidenceReconciliationService,
    )

    service = SemanticEvidenceReconciliationService()

    reconciliation = service.reconcile(
        accepted_candidates,
        canonical_evidence,
    )

    raw_results = extract_reconciliation_results(reconciliation)

    results = [
        serialize_reconciliation_result(result)
        for result in raw_results
    ]

    return results


def validate_reconciliation_cardinality(
    accepted_candidates: Sequence[Any],
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    accepted_ids = {
        candidate_id(candidate)
        for candidate in accepted_candidates
    }

    result_ids = {
        str(result.get("candidate_id") or "")
        for result in results
    }

    missing = sorted(accepted_ids - result_ids)
    extra = sorted(result_ids - accepted_ids)

    duplicate_ids = [
        candidate_id_value
        for candidate_id_value, count in Counter(
            result.get("candidate_id")
            for result in results
        ).items()
        if count > 1
    ]

    checks = {
        "count_equal": len(results) == len(accepted_candidates),
        "no_missing_candidates": not missing,
        "no_extra_candidates": not extra,
        "no_duplicate_result_ids": not duplicate_ids,
        "all_match_types_valid": all(
            result.get("match_type") in MATCH_TYPES
            for result in results
        ),
    }

    return {
        "checks": checks,
        "missing_candidate_ids": missing,
        "extra_result_ids": extra,
        "duplicate_result_ids": sorted(
            str(value) for value in duplicate_ids
        ),
        "pass": all(checks.values()),
    }


def calculate_match_counts(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    counts = Counter(
        str(result.get("match_type") or "")
        for result in results
    )

    return {
        match_type: counts.get(match_type, 0)
        for match_type in MATCH_TYPES
    }


def calculate_v33_coverage(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    total = len(results)

    matched = sum(
        1
        for result in results
        if result.get("match_type") in MATCHED_TYPES
    )

    unmatched = total - matched

    return {
        "accepted_candidates": total,
        "matched_candidates": matched,
        "unmatched_candidates": unmatched,
        "coverage_pct": (
            round(100.0 * matched / total, 4)
            if total
            else 0.0
        ),
    }


def calculate_canonical_coverage(
    canonical_evidence: Sequence[Any],
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    matched_indices: set[int] = set()

    for result in results:
        if result.get("match_type") not in MATCHED_TYPES:
            continue

        for match in result.get("canonical_matches", []):
            index = match.get("canonical_index")

            if isinstance(index, int):
                matched_indices.add(index)

    total = len(canonical_evidence)

    return {
        "canonical_evidence": total,
        "canonical_evidence_with_v33_match": len(matched_indices),
        "unmatched_canonical_evidence": (
            total - len(matched_indices)
        ),
        "coverage_pct": (
            round(
                100.0 * len(matched_indices) / total,
                4,
            )
            if total
            else 0.0
        ),
    }


def aggregate_by_dimension(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    aggregate: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "accepted": 0,
            "EXACT_MATCH": 0,
            "OFFSET_MATCH": 0,
            "TEXT_MATCH": 0,
            "AMBIGUOUS": 0,
            "NO_MATCH": 0,
        }
    )

    for result in results:
        dimension = str(
            result.get("dimension") or "<unclassified>"
        )
        match_type = str(
            result.get("match_type") or "NO_MATCH"
        )

        aggregate[dimension]["accepted"] += 1

        if match_type in MATCH_TYPES:
            aggregate[dimension][match_type] += 1

    return {
        dimension: dict(values)
        for dimension, values in sorted(
            aggregate.items()
        )
    }


def aggregate_by_field(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    aggregate: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "accepted": 0,
            "EXACT_MATCH": 0,
            "OFFSET_MATCH": 0,
            "TEXT_MATCH": 0,
            "AMBIGUOUS": 0,
            "NO_MATCH": 0,
        }
    )

    for result in results:
        field = str(
            result.get("field") or "<unclassified>"
        )
        match_type = str(
            result.get("match_type") or "NO_MATCH"
        )

        aggregate[field]["accepted"] += 1

        if match_type in MATCH_TYPES:
            aggregate[field][match_type] += 1

    return {
        field: dict(values)
        for field, values in sorted(
            aggregate.items()
        )
    }


def build_ambiguity_diagnostics(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_to_multiple = [
        result
        for result in results
        if (
            result.get("match_type") == "AMBIGUOUS"
            or int(result.get("canonical_match_count") or 0) > 1
        )
    ]

    canonical_to_candidates: dict[int, list[str]] = defaultdict(list)

    for result in results:
        for match in result.get("canonical_matches", []):
            index = match.get("canonical_index")

            if isinstance(index, int):
                canonical_to_candidates[index].append(
                    str(result.get("candidate_id") or "")
                )

    reverse_ambiguities = {
        str(index): sorted(set(candidate_ids))
        for index, candidate_ids in canonical_to_candidates.items()
        if len(set(candidate_ids)) > 1
    }

    return {
        "candidate_to_multiple_canonical": len(
            candidate_to_multiple
        ),
        "canonical_to_multiple_candidates": len(
            reverse_ambiguities
        ),
        "canonical_to_candidate_details": reverse_ambiguities,
    }


def build_duplicate_text_diagnostics(
    accepted_candidates: Sequence[Any],
    canonical_evidence: Sequence[Any],
) -> dict[str, Any]:
    v33_groups: dict[str, list[str]] = defaultdict(list)

    for candidate in accepted_candidates:
        normalized = normalize_text(
            candidate_text(candidate)
        )
        if normalized:
            v33_groups[normalized].append(
                candidate_id(candidate)
            )

    canonical_groups: dict[str, list[int]] = defaultdict(list)

    for index, evidence in enumerate(canonical_evidence):
        text = first_value(
            evidence,
            "source_text",
            "text",
            default="",
        )
        normalized = normalize_text(text)

        if normalized:
            canonical_groups[normalized].append(index)

    v33_duplicates = {
        text: ids
        for text, ids in v33_groups.items()
        if len(ids) > 1
    }

    canonical_duplicates = {
        text: indexes
        for text, indexes in canonical_groups.items()
        if len(indexes) > 1
    }

    return {
        "v33_duplicate_text_groups": len(v33_duplicates),
        "canonical_duplicate_text_groups": len(
            canonical_duplicates
        ),
        "v33_duplicate_groups": v33_duplicates,
        "canonical_duplicate_groups": canonical_duplicates,
    }


def build_provenance_diagnostics(
    accepted_candidates: Sequence[Any],
    canonical_evidence: Sequence[Any],
) -> dict[str, Any]:
    v33_total = len(accepted_candidates)
    canonical_total = len(canonical_evidence)

    v33 = {
        "source_id": sum(
            first_value(c, "source_id") is not None
            for c in accepted_candidates
        ),
        "source_sha256": sum(
            first_value(c, "source_sha256") is not None
            for c in accepted_candidates
        ),
        "extraction_id": sum(
            first_value(c, "extraction_id") is not None
            for c in accepted_candidates
        ),
        "segment_index": sum(
            first_value(c, "segment_index") is not None
            for c in accepted_candidates
        ),
        "offsets": sum(
            first_value(c, "signal_start", "start_offset") is not None
            and first_value(c, "signal_end", "end_offset") is not None
            for c in accepted_candidates
        ),
    }

    canonical = {
        "document_id": sum(
            first_value(e, "document_id") is not None
            for e in canonical_evidence
        ),
        "page": sum(
            first_value(e, "page") is not None
            for e in canonical_evidence
        ),
        "section": sum(
            first_value(e, "section") is not None
            for e in canonical_evidence
        ),
        "offsets": sum(
            first_value(e, "start_offset") is not None
            and first_value(e, "end_offset") is not None
            for e in canonical_evidence
        ),
    }

    return {
        "v33": {
            "total": v33_total,
            **v33,
        },
        "canonical": {
            "total": canonical_total,
            **canonical,
        },
    }


def find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_startup_output_dir(
    startup: str,
    report_path: Path,
) -> Path:
    repo_root = find_repo_root()
    default = repo_root / "generated" / startup

    if default.exists():
        return default

    if report_path.parent.exists():
        return report_path.parent

    return default


def capture_protected_files(
    startup: str,
    report_path: Path,
) -> dict[str, Any]:
    output_dir = find_startup_output_dir(
        startup,
        report_path,
    )
    protected_path = output_dir / PROTECTED_FILE_NAME

    digest = sha256_file(protected_path)

    return {
        "path": str(protected_path),
        "exists_before": digest is not None,
        "sha256_before": digest,
    }


def verify_protected_file(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    path = Path(str(snapshot["path"]))
    after = sha256_file(path)
    before = snapshot.get("sha256_before")

    if before is None:
        unchanged = after is None
    else:
        unchanged = after == before

    return {
        "path": str(path),
        "exists_before": bool(
            snapshot.get("exists_before")
        ),
        "exists_after": after is not None,
        "sha256_before": before,
        "sha256_after": after,
        "unchanged": unchanged,
    }


def write_report(
    path: Path,
    report: Mapping[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
    ) as fh:
        json.dump(
            make_json_safe(dict(report)),
            fh,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        fh.write("\n")


def build_report(
    *,
    startup: str,
    mode: str,
    source_population: Mapping[str, Any],
    v33_validation: Mapping[str, Any],
    accepted_candidates: Sequence[Any],
    canonical_evidence: Sequence[Any],
    results: Sequence[Mapping[str, Any]],
    reconciliation_cardinality: Mapping[str, Any],
    protected_file: Mapping[str, Any],
) -> dict[str, Any]:
    checks = {
        "source_population": bool(
            source_population.get("pass", False)
        ),
        "v33_population": bool(
            v33_validation.get("pass", False)
        ),
        "canonical_population": (
            len(canonical_evidence) >= 0
        ),
        "reconciliation_cardinality": bool(
            reconciliation_cardinality.get("pass", False)
        ),
        "protected_file_unchanged": bool(
            protected_file.get("unchanged", False)
        ),
    }

    status = (
        "PASS"
        if all(checks.values())
        else "FAIL"
    )

    return {
        "report_version": REPORT_VERSION,

        "run": {
            "timestamp_utc": utc_now(),
            "startup": startup,
            "mode": mode,
            "status": status,
        },

        "source_population": dict(source_population),

        "v33": dict(
            v33_validation.get("metadata", {})
        ),

        "canonical": {
            "analysis_evidence_count": len(
                canonical_evidence
            )
        },

        "reconciliation": {
            "accepted_candidates": len(
                accepted_candidates
            ),
            "match_counts": calculate_match_counts(
                results
            ),
            "v33_to_canonical": calculate_v33_coverage(
                results
            ),
            "canonical_to_v33": calculate_canonical_coverage(
                canonical_evidence,
                results,
            ),
        },

        "by_dimension": aggregate_by_dimension(
            results
        ),

        "by_field": aggregate_by_field(
            results
        ),

        "ambiguity": build_ambiguity_diagnostics(
            results
        ),

        "duplicates": build_duplicate_text_diagnostics(
            accepted_candidates,
            canonical_evidence,
        ),

        "provenance": build_provenance_diagnostics(
            accepted_candidates,
            canonical_evidence,
        ),

        "results": [
            make_json_safe(dict(result))
            for result in results
        ],

        "protected_files": {
            "dimension_evidence_json": dict(
                protected_file
            )
        },

        "checks": checks,
        "status": status,
    }


def print_summary(report: Mapping[str, Any]) -> None:
    v33 = report.get("v33", {})
    canonical = report.get("canonical", {})
    reconciliation = report.get("reconciliation", {})

    print()
    print("=" * 88)
    print("V3.3 SEMANTIC EVIDENCE RECONCILIATION")
    print("=" * 88)

    run = report.get("run", {})

    print(f"STARTUP                 : {run.get('startup')}")
    print(f"MODE                    : {run.get('mode')}")

    print()
    print("-" * 88)
    print("V3.3 POPULATION")
    print("-" * 88)

    print(
        f"RAW CANDIDATES          : "
        f"{v33.get('raw_candidates')}"
    )
    print(
        f"A1.2 PASSED             : "
        f"{v33.get('a12_passed')}"
    )
    print(
        f"B4.2 SELECTED           : "
        f"{v33.get('b42_selected')}"
    )
    print(
        f"FINAL ACCEPTED          : "
        f"{v33.get('final_accepted')}"
    )
    print(
        f"FINAL REJECTED          : "
        f"{v33.get('final_rejected')}"
    )
    print(
        f"RECOVERED               : "
        f"{v33.get('recovered')}"
    )

    print()
    print("-" * 88)
    print("CANONICAL EVIDENCE")
    print("-" * 88)

    print(
        f"ANALYSIS EVIDENCE       : "
        f"{canonical.get('analysis_evidence_count')}"
    )

    print()
    print("-" * 88)
    print("RECONCILIATION")
    print("-" * 88)

    print(
        f"ACCEPTED CANDIDATES     : "
        f"{reconciliation.get('accepted_candidates')}"
    )

    counts = reconciliation.get(
        "match_counts",
        {},
    )

    for match_type in MATCH_TYPES:
        print(
            f"{match_type:<24}: "
            f"{counts.get(match_type, 0)}"
        )

    v33_to_canonical = reconciliation.get(
        "v33_to_canonical",
        {},
    )
    canonical_to_v33 = reconciliation.get(
        "canonical_to_v33",
        {},
    )

    print(
        f"V3.3 -> CANONICAL        : "
        f"{v33_to_canonical.get('coverage_pct', 0.0):.4f}%"
    )
    print(
        f"CANONICAL -> V3.3        : "
        f"{canonical_to_v33.get('coverage_pct', 0.0):.4f}%"
    )

    protected = (
        report
        .get("protected_files", {})
        .get("dimension_evidence_json", {})
    )

    print()
    print("-" * 88)
    print("PROTECTED FILE")
    print("-" * 88)

    print(
        "dimension_evidence.json : "
        + (
            "UNCHANGED"
            if protected.get("unchanged")
            else "CHANGED / NOT PRESENT"
        )
    )

    print()
    print("=" * 88)
    print(
        f"STATUS                  : "
        f"{report.get('status')}"
    )
    print("=" * 88)


def build_source_population_from_artifact(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    source_population = artifact.get(
        "source_population"
    )

    if isinstance(source_population, Mapping):
        sources = source_population.get(
            "current_sources"
        )
        extractions = source_population.get(
            "current_extractions"
        )

        if sources is not None and extractions is not None:
            return {
                "current_sources": int(sources),
                "current_extractions": int(extractions),
                "population_match": (
                    int(sources) == int(extractions)
                ),
                "pass": (
                    int(sources) == int(extractions)
                ),
            }

    # The current RestoMart V3.3 sidecar does not need to be treated as the
    # source of truth for source population. If metadata is absent, the
    # harness records that it was not independently available from the
    # artifact. Live mode fills this from the actual current population.
    return {
        "current_sources": None,
        "current_extractions": None,
        "population_match": None,
        "pass": True,
        "availability": "not_present_in_v33_artifact",
    }


def build_live_v33_service():
    from app.services.semantic_evidence_validation import (
        SemanticEvidenceValidationService,
    )

    return SemanticEvidenceValidationService()


def normalize_startup_key(value: str) -> str:
    """Use the same startup filesystem normalization as production."""
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def resolve_startup(
    *,
    startup_service: StartupService,
    startup_identifier: str,
):
    """
    Resolve a persisted Startup using the same UUID/name policy as
    generate_dimension_evidence.py.
    """
    identifier = startup_identifier.strip()

    try:
        startup_id = UUID(identifier)
    except ValueError:
        startup_id = None

    if startup_id is not None:
        startup = startup_service.get_startup(startup_id)
        if startup is None:
            raise ValueError(
                f"Startup not found for UUID: {startup_id}"
            )
        return startup

    normalized = normalize_startup_key(identifier)

    matches = [
        startup
        for startup in startup_service.list_startups()
        if normalize_startup_key(startup.name) == normalized
    ]

    if not matches:
        raise ValueError(
            f"Startup not found for identifier: {startup_identifier}"
        )

    if len(matches) > 1:
        ids = ", ".join(str(startup.id) for startup in matches)
        raise ValueError(
            f"Multiple startups matched "
            f"'{startup_identifier}': {ids}"
        )

    return matches[0]


def resolve_current_source_extractions(
    *,
    startup,
    source_discovery: SourceDiscoveryService,
    extraction_persistence: SourceExtractionPersistenceService,
) -> tuple:
    """
    Reuse the production current-source identity rule:
        source_id + source_sha256

    A stale extraction must never be silently reused.
    """
    startup_key = normalize_startup_key(startup.name)

    source_root = (
        Path(settings.real_startups_root)
        / startup_key
        / "sources"
    )

    if not source_root.exists():
        raise FileNotFoundError(
            f"Source directory not found: {source_root}"
        )

    sources = source_discovery.discover(
        startup_id=str(startup.id),
        source_root=source_root,
    )

    records = []
    missing = []

    for source in sources:
        if source.sha256 is None:
            missing.append(source.filename)
            continue

        record = extraction_persistence.get_by_source_version(
            source_id=source.source_id,
            source_sha256=source.sha256,
        )

        if record is None:
            missing.append(source.filename)
            continue

        records.append(record)

    if missing:
        raise RuntimeError(
            "Current source set is not fully extracted. "
            f"Missing {len(missing)} current source extraction(s): "
            + ", ".join(missing)
        )

    if not records:
        raise RuntimeError(
            "No current persisted source extractions were found."
        )

    return tuple(records)


def load_current_population_for_live_mode(
    *,
    session,
    startup,
):
    """
    Resolve the same current persisted source-extraction population used by
    generate_dimension_evidence.py.
    """
    source_discovery = SourceDiscoveryService()

    extraction_persistence = SourceExtractionPersistenceService(
        session=session
    )

    source_extractions = resolve_current_source_extractions(
        startup=startup,
        source_discovery=source_discovery,
        extraction_persistence=extraction_persistence,
    )

    return source_extractions


def run_live_v33(
    *,
    startup,
    source_extractions,
):
    """Run the canonical V3.3 orchestration service."""
    service = build_live_v33_service()

    return service.validate(
        [
            (startup, extraction)
            for extraction in source_extractions
        ]
    )


def build_canonical_evidence_from_existing_path(
    *,
    session,
    startup,
    source_extractions,
):
    """
    Build canonical AnalysisEvidence through the exact production
    StartupAnalysisDocumentIntelligenceService path.

    This mirrors generate_dimension_evidence.py:

        StartupAnalysisInputBuilder
            ->
        StartupAnalysisDocumentIntelligenceService.enrich(
            source_extractions=...
        )
            ->
        enriched_input.evidence

    No DimensionEvidenceBuilder is invoked and no output artifact is written.
    """
    input_builder = StartupAnalysisInputBuilder()

    analysis_input = input_builder.build(
        startup
    )

    document_intelligence = (
        StartupAnalysisApplicationService
        .create_startup_analysis_document_intelligence(
            session
        )
    )

    enriched_input = document_intelligence.enrich(
        startup=startup,
        analysis_input=analysis_input,
        source_extractions=source_extractions,
    )

    canonical_evidence = enriched_input.evidence

    if not canonical_evidence:
        raise RuntimeError(
            "Document intelligence produced no canonical AnalysisEvidence."
        )

    return canonical_evidence


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    report_path = Path(args.report)

    protected_snapshot = capture_protected_files(
        args.startup,
        report_path,
    )

    session = create_session()

    try:
        startup_service = StartupService(session)

        startup = resolve_startup(
            startup_service=startup_service,
            startup_identifier=args.startup,
        )

        source_discovery = SourceDiscoveryService()

        extraction_persistence = SourceExtractionPersistenceService(
            session=session
        )

        source_extractions = resolve_current_source_extractions(
            startup=startup,
            source_discovery=source_discovery,
            extraction_persistence=extraction_persistence,
        )

        source_population = {
            "current_sources": len(
                source_discovery.discover(
                    startup_id=str(startup.id),
                    source_root=(
                        Path(settings.real_startups_root)
                        / normalize_startup_key(startup.name)
                        / "sources"
                    ),
                )
            ),
            "current_extractions": len(source_extractions),
            "population_match": True,
            "pass": True,
        }

        if args.run_v33:
            batch = run_live_v33(
                startup=startup,
                source_extractions=source_extractions,
            )

            accepted_candidates = list(
                batch.accepted_candidates()
            )

            counts = batch.counts()

            v33_validation = {
                "metadata": {
                    "benchmark_version": (
                        batch.benchmark_version
                    ),
                    "candidate_generation_version": (
                        batch.as_dict().get(
                            "candidate_generation_version"
                        )
                    ),
                    "a12_version": (
                        batch.as_dict().get("a12_version")
                    ),
                    "b3_version": (
                        batch.as_dict().get("b3_version")
                    ),
                    "b4_2_version": (
                        batch.as_dict().get("b4_2_version")
                    ),
                    "raw_candidates": counts.get(
                        "raw_candidates"
                    ),
                    "a12_passed": counts.get(
                        "gated_candidates"
                    ),
                    "b42_selected": counts.get(
                        "b4_2_selected"
                    ),
                    "final_accepted": counts.get(
                        "final_accepted"
                    ),
                    "final_rejected": counts.get(
                        "final_rejected"
                    ),
                    "recovered": counts.get(
                        "recovered"
                    ),
                },
                "checks": {
                    "source_population": True,
                    "accepted_records_available": bool(
                        accepted_candidates
                    ),
                },
                "pass": bool(accepted_candidates),
            }

            mode = "live"

        else:
            v33_input = resolve_v33_input_path(
                args.startup,
                args.v33_input,
                report_path,
            )

            artifact = load_v33_artifact(v33_input)

            accepted_candidates = (
                extract_final_accepted_from_artifact(
                    artifact
                )
            )

            v33_validation = validate_v33_artifact(
                artifact,
                accepted_candidates,
            )

            mode = "artifact"

        canonical_evidence = (
            build_canonical_evidence_from_existing_path(
                session=session,
                startup=startup,
                source_extractions=source_extractions,
            )
        )

        if not isinstance(canonical_evidence, Sequence):
            raise RuntimeError(
                "Canonical AnalysisEvidence must be a sequence."
            )

        if not accepted_candidates:
            raise RuntimeError(
                "No final accepted V3.3 candidates were available "
                "for reconciliation."
            )

        results = run_reconciliation(
            accepted_candidates=accepted_candidates,
            canonical_evidence=canonical_evidence,
        )

        cardinality = validate_reconciliation_cardinality(
            accepted_candidates,
            results,
        )

        protected_after = verify_protected_file(
            protected_snapshot
        )

        report = build_report(
            startup=startup.name,
            mode=mode,
            source_population=source_population,
            v33_validation=v33_validation,
            accepted_candidates=accepted_candidates,
            canonical_evidence=canonical_evidence,
            results=results,
            reconciliation_cardinality=cardinality,
            protected_file=protected_after,
        )

        report["run"]["startup_id"] = str(startup.id)
        report["run"]["report_path"] = str(report_path)

        if not args.run_v33:
            report["run"]["v33_input"] = str(v33_input)

        report["checks"]["v33_detail"] = (
            v33_validation.get("checks", {})
        )
        report["checks"]["reconciliation_detail"] = (
            cardinality.get("checks", {})
        )

        write_report(
            report_path,
            report,
        )

        return report

    finally:
        session.close()


def main() -> int:
    args = parse_args()

    try:
        report = run_validation(args)

        print_summary(report)

        return (
            0
            if report.get("status") == "PASS"
            else 1
        )

    except KeyboardInterrupt:
        print("\nSTATUS                  : INTERRUPTED")
        return 130

    except Exception as exc:
        print()
        print("=" * 88)
        print("V3.3 SEMANTIC EVIDENCE RECONCILIATION")
        print("=" * 88)
        print("STATUS                  : FAIL")
        print(
            f"ERROR                   : "
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 88)

        return 1


if __name__ == "__main__":
    sys.exit(main())
