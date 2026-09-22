#!/usr/bin/env python3
"""
Deterministic three-run comparison for V3.3 E1 semantic evidence review.

Compares:
  1. E1 GPT-OSS-20B original
  2. E1 GPT-OSS-120B original
  3. E1 GPT-OSS-120B V2 context-aware

Design properties:
  - deterministic
  - read-only
  - standard library only
  - no LLM calls
  - no API calls
  - no production mutation
  - no semantic reclassification
  - no model scoring/ranking
  - stable proposal_id alignment
  - explicit population/integrity validation

Outputs:
  - JSON comparison report
  - human-readable text comparison report

The script does NOT decide whether any AI decision is correct.
It reports observed decisions and deterministic transitions only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCRIPT_VERSION = "v33-e1-three-run-comparison-v1.0"

EXPECTED_TOTAL_ITEMS = 92
EXPECTED_PROPOSITION_ITEMS = 90
EXPECTED_AMBIGUOUS_ITEMS = 2

DECISIONS = (
    "NEW_EVIDENCE",
    "SAME_PROPOSITION",
    "DUPLICATE_OR_OVERLAP",
    "INSUFFICIENT_EVIDENCE",
    "WRONG_DIMENSION_OR_FIELD",
    "UNCERTAIN",
)

RECOMMENDATIONS = (
    "PROMOTE",
    "RETAIN_EXISTING",
    "DO_NOT_PROMOTE",
    "REVIEW_REQUIRED",
)

CONTEXT_STATUSES = (
    "CANONICAL_CONTEXT_AVAILABLE",
    "CANONICAL_CONTEXT_EMPTY",
    "CANONICAL_CONTEXT_RETRIEVAL_FAILURE",
    "CONTEXT_STATUS_UNKNOWN",
)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def die(message: str, code: int = 2) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(code)


def load_json(path: Path) -> Any:
    if not path.exists():
        die(f"Input file does not exist: {path}")

    if not path.is_file():
        die(f"Input path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        die(f"Invalid JSON in {path}: {exc}")
    except OSError as exc:
        die(f"Unable to read {path}: {exc}")


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(
            payload,
            fh,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def first_nonempty(
    mapping: Mapping[str, Any],
    keys: Sequence[str],
    default: Any = None,
) -> Any:
    for key in keys:
        if key not in mapping:
            continue

        value = mapping[key]

        if value is None:
            continue

        if isinstance(value, str):
            if value.strip():
                return value

        elif value != "":
            return value

    return default


def as_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def normalize_text(value: Any) -> str:
    return " ".join(as_text(value).split())


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def nested_get(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping

    for key in keys:
        if not isinstance(current, Mapping):
            return None

        current = current.get(key)

    return current


# ---------------------------------------------------------------------------
# Report structure discovery
# ---------------------------------------------------------------------------

def find_record_list(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """
    Find the review record list.

    Current E1 reports are expected to use "records", but a few compatible
    aliases are accepted to make the diagnostic script robust to harmless
    report-wrapper changes.
    """

    preferred_keys = (
        "records",
        "review_records",
        "review_results",
        "results",
        "items",
    )

    for key in preferred_keys:
        value = payload.get(key)

        if isinstance(value, list):
            records = [x for x in value if isinstance(x, Mapping)]

            if records:
                return [dict(x) for x in records]

    # Some report formats may wrap the records.
    for wrapper_key in (
        "report",
        "data",
        "review",
        "result",
    ):
        wrapper = payload.get(wrapper_key)

        if not isinstance(wrapper, Mapping):
            continue

        for key in preferred_keys:
            value = wrapper.get(key)

            if isinstance(value, list):
                records = [x for x in value if isinstance(x, Mapping)]

                if records:
                    return [dict(x) for x in records]

    die(
        "Could not locate review records. "
        "Expected one of: records, review_records, "
        "review_results, results, items."
    )


# ---------------------------------------------------------------------------
# Record normalization
# ---------------------------------------------------------------------------

def extract_proposal_id(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "proposal_id",
            "proposalId",
            "item_id",
            "review_item_id",
            "id",
        ),
    )

    if value:
        return str(value)

    for nested_key in ("item", "candidate", "review_item", "proposal"):
        nested = record.get(nested_key)

        if isinstance(nested, Mapping):
            value = first_nonempty(
                nested,
                (
                    "proposal_id",
                    "proposalId",
                    "item_id",
                    "review_item_id",
                    "id",
                ),
            )

            if value:
                return str(value)

    return ""


def extract_item_type(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "item_type",
            "review_item_type",
            "type",
            "proposal_type",
        ),
    )

    if value:
        return str(value)

    proposal_id = extract_proposal_id(record)

    if proposal_id.startswith("singleton:"):
        return "singleton"

    if proposal_id.startswith("PROP-"):
        return "proposition"

    return "unknown"


def extract_dimension(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "dimension",
            "target_dimension",
            "evidence_dimension",
        ),
    )

    if value:
        return str(value)

    for nested_key in ("candidate", "item", "review_item", "proposal"):
        nested = record.get(nested_key)

        if isinstance(nested, Mapping):
            value = first_nonempty(
                nested,
                (
                    "dimension",
                    "target_dimension",
                    "evidence_dimension",
                ),
            )

            if value:
                return str(value)

    return ""


def extract_field(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "field",
            "target_field",
            "evidence_field",
        ),
    )

    if value:
        return str(value)

    for nested_key in ("candidate", "item", "review_item", "proposal"):
        nested = record.get(nested_key)

        if isinstance(nested, Mapping):
            value = first_nonempty(
                nested,
                (
                    "field",
                    "target_field",
                    "evidence_field",
                ),
            )

            if value:
                return str(value)

    return ""


def extract_candidate_text(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "candidate_text",
            "text",
            "observation",
            "candidate",
        ),
    )

    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        nested = first_nonempty(
            value,
            (
                "text",
                "candidate_text",
                "observation",
            ),
        )

        if nested is not None:
            return as_text(nested)

    for nested_key in ("candidate", "item", "review_item", "proposal"):
        nested = record.get(nested_key)

        if isinstance(nested, Mapping):
            value = first_nonempty(
                nested,
                (
                    "text",
                    "candidate_text",
                    "observation",
                ),
            )

            if value is not None:
                return as_text(value)

    return ""


def extract_decision(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "decision",
            "ai_decision",
            "semantic_decision",
        ),
    )

    if value is None:
        return ""

    return str(value)


def extract_confidence(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "confidence",
            "ai_confidence",
            "semantic_confidence",
        ),
    )

    if value is None:
        return ""

    return str(value)


def extract_reason(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "reason",
            "ai_reason",
            "explanation",
        ),
    )

    if value is None:
        return ""

    return str(value)


def extract_recommendation(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "promotion_recommendation",
            "recommendation",
            "promotion",
            "promotion_decision",
        ),
    )

    if value is None:
        return ""

    return str(value)


def extract_context_status(record: Mapping[str, Any]) -> str:
    value = first_nonempty(
        record,
        (
            "canonical_context_status",
            "context_status",
            "canonical_context_state",
        ),
    )

    if value:
        value = str(value)

        if value in CONTEXT_STATUSES:
            return value

        # Compatibility aliases.
        normalized = value.upper().replace("-", "_").replace(" ", "_")

        if normalized in {
            "AVAILABLE",
            "CONTEXT_AVAILABLE",
            "CANONICAL_CONTEXT_AVAILABLE",
        }:
            return "CANONICAL_CONTEXT_AVAILABLE"

        if normalized in {
            "EMPTY",
            "CONTEXT_EMPTY",
            "CANONICAL_CONTEXT_EMPTY",
        }:
            return "CANONICAL_CONTEXT_EMPTY"

        if normalized in {
            "RETRIEVAL_FAILURE",
            "CONTEXT_RETRIEVAL_FAILURE",
            "CANONICAL_CONTEXT_RETRIEVAL_FAILURE",
        }:
            return "CANONICAL_CONTEXT_RETRIEVAL_FAILURE"

    # Infer only from explicit context fields. Do not infer semantic meaning.
    context = first_nonempty(
        record,
        (
            "canonical_context",
            "canonical_evidence_context",
        ),
    )

    if context is None:
        return "CONTEXT_STATUS_UNKNOWN"

    if isinstance(context, str):
        if context.strip():
            return "CANONICAL_CONTEXT_AVAILABLE"

        return "CANONICAL_CONTEXT_EMPTY"

    if isinstance(context, Sequence) and not isinstance(context, (str, bytes)):
        if len(context) > 0:
            return "CANONICAL_CONTEXT_AVAILABLE"

        return "CANONICAL_CONTEXT_EMPTY"

    if isinstance(context, Mapping):
        if context:
            return "CANONICAL_CONTEXT_AVAILABLE"

        return "CANONICAL_CONTEXT_EMPTY"

    return "CONTEXT_STATUS_UNKNOWN"


def extract_context(record: Mapping[str, Any]) -> Any:
    value = first_nonempty(
        record,
        (
            "canonical_context",
            "canonical_evidence_context",
        ),
    )

    return value


def extract_canonical_match(record: Mapping[str, Any]) -> Any:
    return first_nonempty(
        record,
        (
            "canonical_match",
            "canonical_matches",
            "canonical_evidence_match",
        ),
    )


def extract_provenance_complete(record: Mapping[str, Any]) -> Optional[bool]:
    value = first_nonempty(
        record,
        (
            "provenance_complete",
        ),
    )

    if isinstance(value, bool):
        return value

    safety = record.get("safety_checks")

    if isinstance(safety, Mapping):
        value = safety.get("provenance_complete")

        if isinstance(value, bool):
            return value

    return None


def normalize_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "proposal_id": extract_proposal_id(record),
        "item_type": extract_item_type(record),
        "dimension": extract_dimension(record),
        "field": extract_field(record),
        "candidate_text": extract_candidate_text(record),
        "decision": extract_decision(record),
        "confidence": extract_confidence(record),
        "reason": extract_reason(record),
        "recommendation": extract_recommendation(record),
        "context_status": extract_context_status(record),
        "canonical_context": extract_context(record),
        "canonical_match": extract_canonical_match(record),
        "provenance_complete": extract_provenance_complete(record),
        "raw": dict(record),
    }


# ---------------------------------------------------------------------------
# Run validation
# ---------------------------------------------------------------------------

def get_run_metadata(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "status": payload.get("status"),
        "model": payload.get("model"),
        "provider": payload.get("provider"),
        "llm_calls": payload.get("llm_calls"),
        "valid_responses": payload.get("valid_responses"),
        "invalid_responses": payload.get("invalid_responses"),
        "decision_counts": payload.get("decision_counts"),
        "promotion_recommendation_counts": payload.get(
            "promotion_recommendation_counts"
        ),
        "accounting_checks": payload.get("accounting_checks", {}),
    }


def validate_unique_ids(
    records: Sequence[Mapping[str, Any]],
    run_name: str,
) -> List[str]:
    ids = [str(r.get("proposal_id", "")) for r in records]

    missing = [
        f"record_index={index}"
        for index, proposal_id in enumerate(ids)
        if not proposal_id
    ]

    if missing:
        return [
            f"{run_name}: missing proposal_id: {', '.join(missing)}"
        ]

    counts = Counter(ids)

    duplicates = sorted(
        proposal_id
        for proposal_id, count in counts.items()
        if count > 1
    )

    if duplicates:
        return [
            f"{run_name}: duplicate proposal_ids: "
            + ", ".join(duplicates)
        ]

    return []


def validate_run(
    payload: Mapping[str, Any],
    run_name: str,
    expected_model: Optional[str],
    require_92: bool = True,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    errors: List[str] = []

    records_raw = find_record_list(payload)
    records = [normalize_record(record) for record in records_raw]

    errors.extend(validate_unique_ids(records, run_name))

    if require_92 and len(records) != EXPECTED_TOTAL_ITEMS:
        errors.append(
            f"{run_name}: expected {EXPECTED_TOTAL_ITEMS} records, "
            f"found {len(records)}"
        )

    proposition_count = sum(
        1 for record in records
        if record["item_type"] == "proposition"
    )

    ambiguous_count = sum(
        1 for record in records
        if record["item_type"] == "ambiguous"
    )

    singleton_count = sum(
        1 for record in records
        if record["item_type"] == "singleton"
    )

    # Some current reports encode the two ambiguous entries by their review
    # item structure rather than item_type. Therefore only hard-check the
    # proposition population when it can be identified.
    if proposition_count not in (0, EXPECTED_PROPOSITION_ITEMS):
        errors.append(
            f"{run_name}: expected {EXPECTED_PROPOSITION_ITEMS} proposition "
            f"items when typed; found {proposition_count}"
        )

    # Accounting checks from the report are evidence about the run, but this
    # script independently validates the core population.
    if len(records) == EXPECTED_TOTAL_ITEMS:
        if proposition_count == EXPECTED_PROPOSITION_ITEMS:
            pass
        elif proposition_count == 0:
            # Report may not persist item_type.
            pass
        else:
            errors.append(
                f"{run_name}: proposition population is inconsistent"
            )

    if expected_model:
        actual_model = payload.get("model")

        if actual_model != expected_model:
            errors.append(
                f"{run_name}: model mismatch: "
                f"expected={expected_model!r}, actual={actual_model!r}"
            )

    # These are safety expectations for an E1 diagnostic report.
    if payload.get("production_mutation") not in (None, False, "NO"):
        errors.append(
            f"{run_name}: production mutation marker is not clean: "
            f"{payload.get('production_mutation')!r}"
        )

    accounting = payload.get("accounting_checks")

    if isinstance(accounting, Mapping):
        if accounting.get("diagnostic_only") is False:
            errors.append(
                f"{run_name}: diagnostic_only is False"
            )

        if accounting.get("production_mutation_absent") is False:
            errors.append(
                f"{run_name}: production_mutation_absent is False"
            )

    return records, errors


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------

def count_decisions(records: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts = Counter(
        str(record.get("decision", ""))
        for record in records
    )

    return {
        decision: counts.get(decision, 0)
        for decision in DECISIONS
    }


def count_recommendations(
    records: Iterable[Mapping[str, Any]],
) -> Dict[str, int]:
    counts = Counter(
        str(record.get("recommendation", ""))
        for record in records
    )

    return {
        recommendation: counts.get(recommendation, 0)
        for recommendation in RECOMMENDATIONS
    }


def count_context_status(
    records: Iterable[Mapping[str, Any]],
) -> Dict[str, int]:
    counts = Counter(
        str(record.get("context_status", "CONTEXT_STATUS_UNKNOWN"))
        for record in records
    )

    return {
        status: counts.get(status, 0)
        for status in CONTEXT_STATUSES
    }


def percentages(
    counts: Mapping[str, int],
    total: int,
) -> Dict[str, float]:
    if total <= 0:
        return {
            key: 0.0
            for key in counts
        }

    return {
        key: round((value / total) * 100.0, 2)
        for key, value in counts.items()
    }


# ---------------------------------------------------------------------------
# Transition matrices
# ---------------------------------------------------------------------------

def transition_matrix(
    left_records: Mapping[str, Mapping[str, Any]],
    right_records: Mapping[str, Mapping[str, Any]],
    field: str,
) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {
        left_value: {
            right_value: 0
            for right_value in (
                DECISIONS
                if field == "decision"
                else RECOMMENDATIONS
            )
        }
        for left_value in (
            DECISIONS
            if field == "decision"
            else RECOMMENDATIONS
        )
    }

    common_ids = sorted(
        set(left_records.keys()) &
        set(right_records.keys())
    )

    for proposal_id in common_ids:
        left_value = str(left_records[proposal_id].get(field, ""))
        right_value = str(right_records[proposal_id].get(field, ""))

        if left_value not in matrix:
            matrix[left_value] = {}

        if right_value not in matrix[left_value]:
            matrix[left_value][right_value] = 0

        matrix[left_value][right_value] += 1

    return matrix


def transition_changes(
    left_records: Mapping[str, Mapping[str, Any]],
    right_records: Mapping[str, Mapping[str, Any]],
    field: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for proposal_id in sorted(
        set(left_records.keys()) &
        set(right_records.keys())
    ):
        left_value = str(left_records[proposal_id].get(field, ""))
        right_value = str(right_records[proposal_id].get(field, ""))

        if left_value == right_value:
            continue

        rows.append(
            {
                "proposal_id": proposal_id,
                "from": left_value,
                "to": right_value,
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Context analysis
# ---------------------------------------------------------------------------

def context_subset(
    records: Sequence[Mapping[str, Any]],
    status: str,
) -> List[Mapping[str, Any]]:
    return [
        record
        for record in records
        if record.get("context_status") == status
    ]


def context_effect_analysis(
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    for status in CONTEXT_STATUSES:
        subset = context_subset(records, status)

        if not subset:
            continue

        decision_counts = count_decisions(subset)
        recommendation_counts = count_recommendations(subset)

        result[status] = {
            "count": len(subset),
            "decision_counts": decision_counts,
            "decision_percentages": percentages(
                decision_counts,
                len(subset),
            ),
            "recommendation_counts": recommendation_counts,
            "recommendation_percentages": percentages(
                recommendation_counts,
                len(subset),
            ),
        }

    return result


# ---------------------------------------------------------------------------
# Three-way proposition comparison
# ---------------------------------------------------------------------------

def index_records(
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Mapping[str, Any]]:
    return {
        str(record["proposal_id"]): record
        for record in records
        if record.get("proposal_id")
    }


def validate_population_alignment(
    indexes: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> List[str]:
    errors: List[str] = []

    names = list(indexes.keys())

    if not names:
        return ["No run indexes supplied"]

    reference_name = names[0]
    reference_ids = set(indexes[reference_name].keys())

    for name in names[1:]:
        ids = set(indexes[name].keys())

        missing = sorted(reference_ids - ids)
        extra = sorted(ids - reference_ids)

        if missing:
            errors.append(
                f"{name}: missing {len(missing)} proposal IDs relative "
                f"to {reference_name}: {missing}"
            )

        if extra:
            errors.append(
                f"{name}: extra {len(extra)} proposal IDs relative "
                f"to {reference_name}: {extra}"
            )

    return errors


def build_three_way_comparison(
    index_20b: Mapping[str, Mapping[str, Any]],
    index_120b: Mapping[str, Mapping[str, Any]],
    index_v2: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    proposal_ids = sorted(
        set(index_20b.keys())
        & set(index_120b.keys())
        & set(index_v2.keys())
    )

    for proposal_id in proposal_ids:
        a = index_20b[proposal_id]
        b = index_120b[proposal_id]
        c = index_v2[proposal_id]

        rows.append(
            {
                "proposal_id": proposal_id,
                "item_type": c.get("item_type", ""),
                "dimension": c.get("dimension", ""),
                "field": c.get("field", ""),
                "candidate_text": c.get("candidate_text", ""),
                "context_status_v2": c.get("context_status", ""),
                "run_20b": {
                    "decision": a.get("decision", ""),
                    "confidence": a.get("confidence", ""),
                    "recommendation": a.get("recommendation", ""),
                    "reason": a.get("reason", ""),
                },
                "run_120b": {
                    "decision": b.get("decision", ""),
                    "confidence": b.get("confidence", ""),
                    "recommendation": b.get("recommendation", ""),
                    "reason": b.get("reason", ""),
                },
                "run_120b_v2": {
                    "decision": c.get("decision", ""),
                    "confidence": c.get("confidence", ""),
                    "recommendation": c.get("recommendation", ""),
                    "reason": c.get("reason", ""),
                },
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Focused cases
# ---------------------------------------------------------------------------

def build_focus_cases(
    records: Sequence[Mapping[str, Any]],
    decision: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for record in records:
        if record.get("decision") != decision:
            continue

        rows.append(
            {
                "proposal_id": record.get("proposal_id", ""),
                "item_type": record.get("item_type", ""),
                "dimension": record.get("dimension", ""),
                "field": record.get("field", ""),
                "context_status": record.get(
                    "context_status",
                    "CONTEXT_STATUS_UNKNOWN",
                ),
                "confidence": record.get("confidence", ""),
                "recommendation": record.get("recommendation", ""),
                "candidate_text": record.get("candidate_text", ""),
                "canonical_context": record.get(
                    "canonical_context"
                ),
                "canonical_match": record.get(
                    "canonical_match"
                ),
                "reason": record.get("reason", ""),
                "provenance_complete": record.get(
                    "provenance_complete"
                ),
            }
        )

    return rows


def build_ambiguous_cases(
    records: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for record in records:
        item_type = str(record.get("item_type", ""))

        if item_type != "ambiguous":
            continue

        rows.append(
            {
                "proposal_id": record.get("proposal_id", ""),
                "dimension": record.get("dimension", ""),
                "field": record.get("field", ""),
                "context_status": record.get(
                    "context_status",
                    "CONTEXT_STATUS_UNKNOWN",
                ),
                "decision": record.get("decision", ""),
                "confidence": record.get("confidence", ""),
                "recommendation": record.get(
                    "recommendation",
                    "",
                ),
                "candidate_text": record.get(
                    "candidate_text",
                    "",
                ),
                "canonical_context": record.get(
                    "canonical_context"
                ),
                "canonical_match": record.get(
                    "canonical_match"
                ),
                "reason": record.get("reason", ""),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Context-empty special analysis
# ---------------------------------------------------------------------------

def build_context_empty_analysis(
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    subset = context_subset(
        records,
        "CANONICAL_CONTEXT_EMPTY",
    )

    new_without_context = [
        record
        for record in subset
        if record.get("decision") == "NEW_EVIDENCE"
    ]

    same_without_context = [
        record
        for record in subset
        if record.get("decision") == "SAME_PROPOSITION"
    ]

    return {
        "count": len(subset),
        "decision_counts": count_decisions(subset),
        "recommendation_counts": count_recommendations(subset),
        "new_evidence_without_canonical_comparison": [
            {
                "proposal_id": record.get("proposal_id"),
                "dimension": record.get("dimension"),
                "field": record.get("field"),
                "confidence": record.get("confidence"),
                "recommendation": record.get("recommendation"),
            }
            for record in new_without_context
        ],
        "same_proposition_without_canonical_context": [
            {
                "proposal_id": record.get("proposal_id"),
                "dimension": record.get("dimension"),
                "field": record.get("field"),
                "confidence": record.get("confidence"),
                "recommendation": record.get("recommendation"),
            }
            for record in same_without_context
        ],
    }


# ---------------------------------------------------------------------------
# Accounting and integrity
# ---------------------------------------------------------------------------

def sum_counts(counts: Mapping[str, int]) -> int:
    return sum(int(value) for value in counts.values())


def run_integrity(
    payload: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    run_name: str,
) -> Dict[str, Any]:
    decision_counts = count_decisions(records)
    recommendation_counts = count_recommendations(records)

    accounting = payload.get("accounting_checks")

    if not isinstance(accounting, Mapping):
        accounting = {}

    checks: Dict[str, Any] = {
        "population_92": len(records) == EXPECTED_TOTAL_ITEMS,
        "decision_partition": (
            sum_counts(decision_counts) == len(records)
        ),
        "recommendation_partition": (
            sum_counts(recommendation_counts) == len(records)
        ),
        "diagnostic_only": (
            accounting.get("diagnostic_only", True) is True
        ),
        "production_mutation_absent": (
            accounting.get(
                "production_mutation_absent",
                True,
            ) is True
        ),
        "fallback_disabled": (
            accounting.get(
                "fallback_disabled",
                True,
            ) is True
        ),
    }

    # The original 120B run previously had a report-level model_exact failure
    # because that report was configured with expected_model=20B. This
    # comparison intentionally does not treat that historical accounting
    # artifact as a semantic-run failure.
    checks["report_status"] = payload.get("status") == "PASS"

    return {
        "run_name": run_name,
        "checks": checks,
        "all_core_checks_pass": all(
            bool(value)
            for key, value in checks.items()
            if key != "report_status"
        ),
    }


def build_global_integrity(
    indexes: Mapping[str, Mapping[str, Mapping[str, Any]]],
    alignment_errors: Sequence[str],
    run_errors: Mapping[str, Sequence[str]],
    v2_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    context_counts = count_context_status(v2_records)

    checks = {
        "run_20b_population_92": (
            len(indexes["20b"]) == EXPECTED_TOTAL_ITEMS
        ),
        "run_120b_population_92": (
            len(indexes["120b"]) == EXPECTED_TOTAL_ITEMS
        ),
        "run_120b_v2_population_92": (
            len(indexes["120b_v2"]) == EXPECTED_TOTAL_ITEMS
        ),
        "proposal_id_alignment": (
            len(alignment_errors) == 0
        ),
        "run_20b_validation_errors_absent": (
            len(run_errors.get("20b", [])) == 0
        ),
        "run_120b_validation_errors_absent": (
            len(run_errors.get("120b", [])) == 0
        ),
        "run_120b_v2_validation_errors_absent": (
            len(run_errors.get("120b_v2", [])) == 0
        ),
        "v2_context_retrieval_failures_absent": (
            context_counts[
                "CANONICAL_CONTEXT_RETRIEVAL_FAILURE"
            ] == 0
        ),
        "v2_context_partition_known": (
            sum(context_counts.values()) == len(v2_records)
        ),
    }

    return {
        "checks": checks,
        "all_pass": all(checks.values()),
    }


# ---------------------------------------------------------------------------
# Text report helpers
# ---------------------------------------------------------------------------

def pct(value: int, total: int) -> str:
    if total <= 0:
        return "0.0%"

    return f"{(value / total) * 100.0:.1f}%"


def format_counts_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> str:
    if not rows:
        return "(none)"

    string_rows = [
        [str(cell) for cell in row]
        for row in rows
    ]

    widths = [
        len(str(header))
        for header in headers
    ]

    for row in string_rows:
        for index, value in enumerate(row):
            widths[index] = max(
                widths[index],
                len(value),
            )

    header_line = " | ".join(
        str(header).ljust(widths[index])
        for index, header in enumerate(headers)
    )

    separator = "-+-".join(
        "-" * width
        for width in widths
    )

    lines = [
        header_line,
        separator,
    ]

    for row in string_rows:
        lines.append(
            " | ".join(
                value.ljust(widths[index])
                for index, value in enumerate(row)
            )
        )

    return "\n".join(lines)


def format_distribution(
    counts: Mapping[str, int],
    total: int,
) -> str:
    rows = []

    for key, value in counts.items():
        rows.append(
            (
                key,
                value,
                pct(value, total),
            )
        )

    return format_counts_table(
        ("Category", "Count", "Percent"),
        rows,
    )


def format_matrix(
    matrix: Mapping[str, Mapping[str, int]],
    categories: Sequence[str],
) -> str:
    headers = ["FROM \\ TO"] + list(categories)
    rows = []

    for left in categories:
        row = [left]

        for right in categories:
            row.append(
                matrix.get(left, {}).get(right, 0)
            )

        rows.append(row)

    return format_counts_table(headers, rows)


def compact_text(value: Any, max_length: int = 180) -> str:
    text = normalize_text(value)

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def build_text_report(
    report: Mapping[str, Any],
) -> str:
    lines: List[str] = []

    def section(title: str) -> None:
        lines.append("")
        lines.append("=" * 80)
        lines.append(title)
        lines.append("=" * 80)

    lines.append(
        "V3.3 E1 THREE-RUN DETERMINISTIC COMPARISON"
    )
    lines.append(
        f"REPORT VERSION: {report.get('report_version')}"
    )
    lines.append(
        "READ ONLY: YES"
    )
    lines.append(
        "LLM/API CALLS BY COMPARISON SCRIPT: 0"
    )
    lines.append(
        "PRODUCTION MUTATION: NO"
    )

    section("RUN SUMMARY")

    run_rows = []

    for name, run in report["runs"].items():
        metadata = run["metadata"]

        run_rows.append(
            (
                name,
                metadata.get("model", ""),
                metadata.get("provider", ""),
                metadata.get("llm_calls", ""),
                metadata.get("valid_responses", ""),
                metadata.get("invalid_responses", ""),
                len(run["records"]),
            )
        )

    lines.append(
        format_counts_table(
            (
                "Run",
                "Model",
                "Provider",
                "LLM Calls",
                "Valid",
                "Invalid",
                "Records",
            ),
            run_rows,
        )
    )

    section("DECISION DISTRIBUTION")

    decision_rows = []

    for decision in DECISIONS:
        decision_rows.append(
            (
                decision,
                report["runs"]["20b"]["decision_counts"][decision],
                report["runs"]["120b"]["decision_counts"][decision],
                report["runs"]["120b_v2"]["decision_counts"][decision],
            )
        )

    lines.append(
        format_counts_table(
            (
                "Decision",
                "20B",
                "120B",
                "120B V2",
            ),
            decision_rows,
        )
    )

    section("PROMOTION RECOMMENDATION DISTRIBUTION")

    recommendation_rows = []

    for recommendation in RECOMMENDATIONS:
        recommendation_rows.append(
            (
                recommendation,
                report["runs"]["20b"]["recommendation_counts"][
                    recommendation
                ],
                report["runs"]["120b"]["recommendation_counts"][
                    recommendation
                ],
                report["runs"]["120b_v2"]["recommendation_counts"][
                    recommendation
                ],
            )
        )

    lines.append(
        format_counts_table(
            (
                "Recommendation",
                "20B",
                "120B",
                "120B V2",
            ),
            recommendation_rows,
        )
    )

    section("20B → 120B DECISION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["20b_to_120b"]["decision"],
            DECISIONS,
        )
    )

    section("120B → 120B V2 DECISION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["120b_to_120b_v2"]["decision"],
            DECISIONS,
        )
    )

    section("20B → 120B V2 DECISION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["20b_to_120b_v2"]["decision"],
            DECISIONS,
        )
    )

    section("20B → 120B PROMOTION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["20b_to_120b"]["recommendation"],
            RECOMMENDATIONS,
        )
    )

    section("120B → 120B V2 PROMOTION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["120b_to_120b_v2"]["recommendation"],
            RECOMMENDATIONS,
        )
    )

    section("20B → 120B V2 PROMOTION TRANSITIONS")

    lines.append(
        format_matrix(
            report["transitions"]["20b_to_120b_v2"]["recommendation"],
            RECOMMENDATIONS,
        )
    )

    section("V2 CANONICAL CONTEXT DISTRIBUTION")

    context_counts = report["runs"]["120b_v2"]["context_counts"]

    lines.append(
        format_counts_table(
            ("Context Status", "Count", "Percent"),
            [
                (
                    status,
                    context_counts[status],
                    pct(
                        context_counts[status],
                        EXPECTED_TOTAL_ITEMS,
                    ),
                )
                for status in CONTEXT_STATUSES
            ],
        )
    )

    section("V2 DECISIONS BY CONTEXT STATUS")

    context_analysis = report["context_analysis"]

    for status, analysis in context_analysis.items():
        lines.append("")
        lines.append(f"[{status}]")
        lines.append(
            format_counts_table(
                ("Decision", "Count", "Percent"),
                [
                    (
                        decision,
                        analysis["decision_counts"][decision],
                        f"{analysis['decision_percentages'][decision]:.1f}%",
                    )
                    for decision in DECISIONS
                ],
            )
        )

    section("V2 SAME_PROPOSITION CASES")

    same_cases = report["focus_cases"]["same_proposition"]

    if not same_cases:
        lines.append("(none)")
    else:
        for index, case in enumerate(same_cases, 1):
            lines.append("")
            lines.append(
                f"[{index}] {case['proposal_id']}"
            )
            lines.append(
                f"dimension={case['dimension']} "
                f"field={case['field']} "
                f"context={case['context_status']}"
            )
            lines.append(
                f"confidence={case['confidence']} "
                f"recommendation={case['recommendation']}"
            )
            lines.append(
                "candidate="
                + compact_text(
                    case["candidate_text"]
                )
            )
            lines.append(
                "canonical_context="
                + compact_text(
                    case["canonical_context"]
                )
            )
            lines.append(
                "reason="
                + compact_text(
                    case["reason"]
                )
            )

    section("V2 NEW_EVIDENCE CASES")

    new_cases = report["focus_cases"]["new_evidence"]

    lines.append(
        f"COUNT: {len(new_cases)}"
    )

    for index, case in enumerate(new_cases, 1):
        lines.append("")
        lines.append(
            f"[{index}] {case['proposal_id']}"
        )
        lines.append(
            f"dimension={case['dimension']} "
            f"field={case['field']} "
            f"context={case['context_status']}"
        )
        lines.append(
            f"confidence={case['confidence']} "
            f"recommendation={case['recommendation']}"
        )
        lines.append(
            "candidate="
            + compact_text(
                case["candidate_text"]
            )
        )
        lines.append(
            "canonical_context="
            + compact_text(
                case["canonical_context"]
            )
        )
        lines.append(
            "reason="
            + compact_text(
                case["reason"]
            )
        )

    section("V2 AMBIGUOUS ITEMS")

    ambiguous_cases = report["focus_cases"]["ambiguous"]

    if not ambiguous_cases:
        lines.append("(none)")
    else:
        for index, case in enumerate(
            ambiguous_cases,
            1,
        ):
            lines.append("")
            lines.append(
                f"[{index}] {case['proposal_id']}"
            )
            lines.append(
                f"dimension={case['dimension']} "
                f"field={case['field']} "
                f"context={case['context_status']}"
            )
            lines.append(
                f"decision={case['decision']} "
                f"confidence={case['confidence']} "
                f"recommendation={case['recommendation']}"
            )
            lines.append(
                "candidate="
                + compact_text(
                    case["candidate_text"]
                )
            )
            lines.append(
                "canonical_match="
                + compact_text(
                    case["canonical_match"]
                )
            )

    section("V2 CONTEXT-EMPTY ANALYSIS")

    empty_analysis = report[
        "context_empty_analysis"
    ]

    lines.append(
        f"CONTEXT EMPTY COUNT: "
        f"{empty_analysis['count']}"
    )

    lines.append(
        f"NEW_EVIDENCE WITHOUT CANONICAL COMPARISON: "
        f"{len(empty_analysis['new_evidence_without_canonical_comparison'])}"
    )

    lines.append(
        f"SAME_PROPOSITION WITHOUT CANONICAL CONTEXT: "
        f"{len(empty_analysis['same_proposition_without_canonical_context'])}"
    )

    section("IMPORTANT V2 TRANSITION CHANGES")

    changes = report["transitions"]["summary_changes"]

    lines.append(
        format_counts_table(
            (
                "Metric",
                "20B",
                "120B",
                "120B V2",
            ),
            [
                (
                    "NEW_EVIDENCE",
                    changes["NEW_EVIDENCE"]["20b"],
                    changes["NEW_EVIDENCE"]["120b"],
                    changes["NEW_EVIDENCE"]["120b_v2"],
                ),
                (
                    "SAME_PROPOSITION",
                    changes["SAME_PROPOSITION"]["20b"],
                    changes["SAME_PROPOSITION"]["120b"],
                    changes["SAME_PROPOSITION"]["120b_v2"],
                ),
                (
                    "INSUFFICIENT_EVIDENCE",
                    changes["INSUFFICIENT_EVIDENCE"]["20b"],
                    changes["INSUFFICIENT_EVIDENCE"]["120b"],
                    changes["INSUFFICIENT_EVIDENCE"]["120b_v2"],
                ),
                (
                    "WRONG_DIMENSION_OR_FIELD",
                    changes["WRONG_DIMENSION_OR_FIELD"]["20b"],
                    changes["WRONG_DIMENSION_OR_FIELD"]["120b"],
                    changes["WRONG_DIMENSION_OR_FIELD"]["120b_v2"],
                ),
                (
                    "UNCERTAIN",
                    changes["UNCERTAIN"]["20b"],
                    changes["UNCERTAIN"]["120b"],
                    changes["UNCERTAIN"]["120b_v2"],
                ),
            ],
        )
    )

    section("INTEGRITY")

    global_integrity = report["integrity"]

    for key, value in global_integrity["checks"].items():
        lines.append(
            f"{key}: {'PASS' if value else 'FAIL'}"
        )

    lines.append(
        f"ALL GLOBAL CHECKS: "
        f"{'PASS' if global_integrity['all_pass'] else 'FAIL'}"
    )

    section("RUN VALIDATION ERRORS")

    had_errors = False

    for run_name, errors in report[
        "run_validation_errors"
    ].items():
        if errors:
            had_errors = True
            lines.append(
                f"[{run_name}]"
            )
            for error in errors:
                lines.append(
                    f"  - {error}"
                )

    if not had_errors:
        lines.append("(none)")

    section("INTERPRETATION BOUNDARY")

    lines.append(
        "This report is descriptive and deterministic."
    )
    lines.append(
        "It does not determine whether an LLM decision is correct."
    )
    lines.append(
        "NEW_EVIDENCE is not treated as confirmed canonical evidence."
    )
    lines.append(
        "CANONICAL_CONTEXT_EMPTY is not treated as proof that evidence is new."
    )
    lines.append(
        "No ranking, score, winner, or model-quality verdict is generated."
    )
    lines.append(
        "No production evidence artifacts are modified."
    )

    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main report construction
# ---------------------------------------------------------------------------

def build_report(
    payload_20b: Mapping[str, Any],
    payload_120b: Mapping[str, Any],
    payload_v2: Mapping[str, Any],
    records_20b: Sequence[Mapping[str, Any]],
    records_120b: Sequence[Mapping[str, Any]],
    records_v2: Sequence[Mapping[str, Any]],
    validation_errors: Mapping[str, Sequence[str]],
) -> Dict[str, Any]:

    index_20b = index_records(records_20b)
    index_120b = index_records(records_120b)
    index_v2 = index_records(records_v2)

    indexes = {
        "20b": index_20b,
        "120b": index_120b,
        "120b_v2": index_v2,
    }

    alignment_errors = validate_population_alignment(
        indexes
    )

    decisions_20b = count_decisions(records_20b)
    decisions_120b = count_decisions(records_120b)
    decisions_v2 = count_decisions(records_v2)

    recommendations_20b = count_recommendations(
        records_20b
    )
    recommendations_120b = count_recommendations(
        records_120b
    )
    recommendations_v2 = count_recommendations(
        records_v2
    )

    context_counts_v2 = count_context_status(
        records_v2
    )

    transitions = {
        "20b_to_120b": {
            "decision": transition_matrix(
                index_20b,
                index_120b,
                "decision",
            ),
            "recommendation": transition_matrix(
                index_20b,
                index_120b,
                "recommendation",
            ),
            "decision_changes": transition_changes(
                index_20b,
                index_120b,
                "decision",
            ),
            "recommendation_changes": transition_changes(
                index_20b,
                index_120b,
                "recommendation",
            ),
        },
        "120b_to_120b_v2": {
            "decision": transition_matrix(
                index_120b,
                index_v2,
                "decision",
            ),
            "recommendation": transition_matrix(
                index_120b,
                index_v2,
                "recommendation",
            ),
            "decision_changes": transition_changes(
                index_120b,
                index_v2,
                "decision",
            ),
            "recommendation_changes": transition_changes(
                index_120b,
                index_v2,
                "recommendation",
            ),
        },
        "20b_to_120b_v2": {
            "decision": transition_matrix(
                index_20b,
                index_v2,
                "decision",
            ),
            "recommendation": transition_matrix(
                index_20b,
                index_v2,
                "recommendation",
            ),
            "decision_changes": transition_changes(
                index_20b,
                index_v2,
                "decision",
            ),
            "recommendation_changes": transition_changes(
                index_20b,
                index_v2,
                "recommendation",
            ),
        },
    }

    summary_changes = {}

    for decision in DECISIONS:
        summary_changes[decision] = {
            "20b": decisions_20b[decision],
            "120b": decisions_120b[decision],
            "120b_v2": decisions_v2[decision],
            "delta_120b_minus_20b": (
                decisions_120b[decision]
                - decisions_20b[decision]
            ),
            "delta_v2_minus_120b": (
                decisions_v2[decision]
                - decisions_120b[decision]
            ),
            "delta_v2_minus_20b": (
                decisions_v2[decision]
                - decisions_20b[decision]
            ),
        }

    recommendation_changes = {}

    for recommendation in RECOMMENDATIONS:
        recommendation_changes[recommendation] = {
            "20b": recommendations_20b[
                recommendation
            ],
            "120b": recommendations_120b[
                recommendation
            ],
            "120b_v2": recommendations_v2[
                recommendation
            ],
            "delta_120b_minus_20b": (
                recommendations_120b[
                    recommendation
                ]
                - recommendations_20b[
                    recommendation
                ]
            ),
            "delta_v2_minus_120b": (
                recommendations_v2[
                    recommendation
                ]
                - recommendations_120b[
                    recommendation
                ]
            ),
            "delta_v2_minus_20b": (
                recommendations_v2[
                    recommendation
                ]
                - recommendations_20b[
                    recommendation
                ]
            ),
        }

    global_integrity = build_global_integrity(
        indexes,
        alignment_errors,
        validation_errors,
        records_v2,
    )

    report = {
        "report_version": SCRIPT_VERSION,
        "comparison_type": (
            "deterministic_v33_e1_three_run_comparison"
        ),
        "read_only": True,
        "llm_calls_by_comparison_script": 0,
        "production_mutation": False,

        "expected_population": {
            "total": EXPECTED_TOTAL_ITEMS,
            "proposition": EXPECTED_PROPOSITION_ITEMS,
            "ambiguous": EXPECTED_AMBIGUOUS_ITEMS,
        },

        "runs": {
            "20b": {
                "metadata": get_run_metadata(
                    payload_20b
                ),
                "record_count": len(records_20b),
                "decision_counts": decisions_20b,
                "decision_percentages": percentages(
                    decisions_20b,
                    len(records_20b),
                ),
                "recommendation_counts": recommendations_20b,
                "recommendation_percentages": percentages(
                    recommendations_20b,
                    len(records_20b),
                ),
                "context_counts": count_context_status(
                    records_20b
                ),
                "records": records_20b,
                "integrity": run_integrity(
                    payload_20b,
                    records_20b,
                    "20b",
                ),
            },

            "120b": {
                "metadata": get_run_metadata(
                    payload_120b
                ),
                "record_count": len(records_120b),
                "decision_counts": decisions_120b,
                "decision_percentages": percentages(
                    decisions_120b,
                    len(records_120b),
                ),
                "recommendation_counts": recommendations_120b,
                "recommendation_percentages": percentages(
                    recommendations_120b,
                    len(records_120b),
                ),
                "context_counts": count_context_status(
                    records_120b
                ),
                "records": records_120b,
                "integrity": run_integrity(
                    payload_120b,
                    records_120b,
                    "120b",
                ),
            },

            "120b_v2": {
                "metadata": get_run_metadata(
                    payload_v2
                ),
                "record_count": len(records_v2),
                "decision_counts": decisions_v2,
                "decision_percentages": percentages(
                    decisions_v2,
                    len(records_v2),
                ),
                "recommendation_counts": recommendations_v2,
                "recommendation_percentages": percentages(
                    recommendations_v2,
                    len(records_v2),
                ),
                "context_counts": context_counts_v2,
                "records": records_v2,
                "integrity": run_integrity(
                    payload_v2,
                    records_v2,
                    "120b_v2",
                ),
            },
        },

        "alignment": {
            "errors": alignment_errors,
            "all_ids_aligned": len(alignment_errors) == 0,
        },

        "transitions": {
            **transitions,
            "summary_changes": summary_changes,
            "recommendation_summary_changes": (
                recommendation_changes
            ),
        },

        "context_analysis": context_effect_analysis(
            records_v2
        ),

        "context_empty_analysis": (
            build_context_empty_analysis(
                records_v2
            )
        ),

        "focus_cases": {
            "same_proposition": build_focus_cases(
                records_v2,
                "SAME_PROPOSITION",
            ),
            "new_evidence": build_focus_cases(
                records_v2,
                "NEW_EVIDENCE",
            ),
            "ambiguous": build_ambiguous_cases(
                records_v2
            ),
        },

        "three_way_comparison": build_three_way_comparison(
            index_20b,
            index_120b,
            index_v2,
        ),

        "run_validation_errors": {
            key: list(value)
            for key, value in validation_errors.items()
        },

        "integrity": global_integrity,
    }

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically compare the V3.3 E1 20B, "
            "120B, and 120B V2 context-aware review runs."
        )
    )

    parser.add_argument(
        "--run-20b",
        required=True,
        type=Path,
        help="E1 GPT-OSS-20B original JSON report.",
    )

    parser.add_argument(
        "--run-120b",
        required=True,
        type=Path,
        help="E1 GPT-OSS-120B original JSON report.",
    )

    parser.add_argument(
        "--run-120b-v2",
        required=True,
        type=Path,
        help="E1 GPT-OSS-120B V2 context-aware JSON report.",
    )

    parser.add_argument(
        "--review-input",
        type=Path,
        default=None,
        help=(
            "Optional acceptance-review JSON. "
            "Reserved for future deterministic enrichment."
        ),
    )

    parser.add_argument(
        "--v33-input",
        type=Path,
        default=None,
        help=(
            "Optional V3.3 semantic evidence JSON. "
            "Reserved for future deterministic enrichment."
        ),
    )

    parser.add_argument(
        "--json-output",
        required=True,
        type=Path,
        help="Output JSON comparison report.",
    )

    parser.add_argument(
        "--text-output",
        required=True,
        type=Path,
        help="Output text comparison report.",
    )

    parser.add_argument(
        "--allow-validation-errors",
        action="store_true",
        help=(
            "Write the report even when input population/alignment "
            "validation fails. Default is to fail before writing."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 80)
    print("V3.3 E1 THREE-RUN DETERMINISTIC COMPARISON")
    print("=" * 80)
    print(f"REPORT VERSION: {SCRIPT_VERSION}")
    print("LLM CALLS: 0")
    print("PRODUCTION MUTATION: NO")
    print()

    payload_20b = load_json(args.run_20b)
    payload_120b = load_json(args.run_120b)
    payload_v2 = load_json(args.run_120b_v2)

    if not isinstance(payload_20b, Mapping):
        die("20B report root must be a JSON object.")

    if not isinstance(payload_120b, Mapping):
        die("120B report root must be a JSON object.")

    if not isinstance(payload_v2, Mapping):
        die("120B V2 report root must be a JSON object.")

    # Historical 120B original report had model_exact=False because its
    # accounting expected 20B. We therefore validate the actual model identity
    # explicitly but do not require its historical report status to be PASS.
    records_20b, errors_20b = validate_run(
        payload_20b,
        "20b",
        expected_model="openai/gpt-oss-20b",
    )

    records_120b, errors_120b = validate_run(
        payload_120b,
        "120b",
        expected_model="openai/gpt-oss-120b",
    )

    records_v2, errors_v2 = validate_run(
        payload_v2,
        "120b_v2",
        expected_model="openai/gpt-oss-120b",
    )

    validation_errors = {
        "20b": errors_20b,
        "120b": errors_120b,
        "120b_v2": errors_v2,
    }

    # Population/alignment validation is repeated by build_report.
    index_20b = index_records(records_20b)
    index_120b = index_records(records_120b)
    index_v2 = index_records(records_v2)

    alignment_errors = validate_population_alignment(
        {
            "20b": index_20b,
            "120b": index_120b,
            "120b_v2": index_v2,
        }
    )

    all_validation_errors = (
        list(errors_20b)
        + list(errors_120b)
        + list(errors_v2)
        + list(alignment_errors)
    )

    if all_validation_errors and not args.allow_validation_errors:
        print("[ERROR] Input validation failed.")
        print()

        for error in all_validation_errors:
            print(f"  - {error}")

        print()
        print(
            "No comparison report was written. "
            "Use --allow-validation-errors only for diagnostic inspection."
        )

        return 2

    report = build_report(
        payload_20b,
        payload_120b,
        payload_v2,
        records_20b,
        records_120b,
        records_v2,
        validation_errors,
    )

    write_json(
        args.json_output,
        report,
    )

    text_report = build_text_report(report)

    write_text(
        args.text_output,
        text_report,
    )

    print("RUN POPULATIONS")
    print(
        f"  20B     : {len(records_20b)}"
    )
    print(
        f"  120B    : {len(records_120b)}"
    )
    print(
        f"  120B V2 : {len(records_v2)}"
    )

    print()
    print("V2 DECISION COUNTS")

    for decision, count in count_decisions(
        records_v2
    ).items():
        print(
            f"  {decision:<28} : {count}"
        )

    print()
    print("V2 PROMOTION COUNTS")

    for recommendation, count in count_recommendations(
        records_v2
    ).items():
        print(
            f"  {recommendation:<28} : {count}"
        )

    print()
    print("V2 CONTEXT")

    for status, count in count_context_status(
        records_v2
    ).items():
        print(
            f"  {status:<40} : {count}"
        )

    print()
    print(
        "120B ORIGINAL -> 120B V2 DECISION CHANGES:",
        len(
            report["transitions"][
                "120b_to_120b_v2"
            ]["decision_changes"]
        ),
    )

    print(
        "120B ORIGINAL -> 120B V2 RECOMMENDATION CHANGES:",
        len(
            report["transitions"][
                "120b_to_120b_v2"
            ]["recommendation_changes"]
        ),
    )

    print()
    print(
        "SAME_PROPOSITION CASES:",
        len(
            report["focus_cases"][
                "same_proposition"
            ]
        ),
    )

    print(
        "NEW_EVIDENCE CASES:",
        len(
            report["focus_cases"][
                "new_evidence"
            ]
        ),
    )

    print(
        "AMBIGUOUS CASES:",
        len(
            report["focus_cases"][
                "ambiguous"
            ]
        ),
    )

    print()
    print(
        "GLOBAL INTEGRITY:",
        "PASS"
        if report["integrity"]["all_pass"]
        else "FAIL",
    )

    print()
    print(
        "JSON REPORT:",
        args.json_output,
    )

    print(
        "TEXT REPORT:",
        args.text_output,
    )

    print("=" * 80)

    if not report["integrity"]["all_pass"]:
        print(
            "STATUS: FAIL"
        )
        return 1

    print(
        "STATUS: PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
