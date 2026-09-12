#!/usr/bin/env python3
"""
V3.3-B.3 -> 3.7.x teacher-decision parity harness.

Purpose
-------
Prove that the 3.7.x SemanticCandidateValidationService preserves the
frozen V3.3-B.3 semantic-validation contract for the exact 251-candidate
A.1.2 population.

This script is a migration/verification harness. It is NOT a second B.3
implementation.

Frozen boundary
---------------
    V3.3-A.1.2 artifact
            |
            +--> exact 251 gate.passed=true candidates
            |
            v
    frozen V3.3-B.3 teacher result
            |
            |  compare against
            v
    3.7.x SemanticCandidateValidationService

The harness:
  * loads the frozen B.3 benchmark module;
  * validates the frozen B.3 contract and controlled teacher smoke;
  * validates the frozen B.3 result artifact;
  * validates the exact 251-candidate population;
  * compares candidate identity/attributes;
  * compares the frozen prompt with the 3.7.x prompt;
  * validates the 3.7.x service configuration;
  * optionally runs the 3.7.x service live against those exact 251 candidates;
  * compares validity and A/R teacher decisions candidate-by-candidate;
  * reports the A->A/A->R/R->A/R->R transition matrix;
  * checks provider/model drift;
  * checks protected production artifacts remain unchanged;
  * writes only the parity report.

It does NOT:
  * generate candidates;
  * run A.1.2;
  * implement B.4.2;
  * retrieve adjacent context;
  * build AnalysisEvidence;
  * modify dimension_evidence.json;
  * modify investment_scorecard.json;
  * modify startup.yaml;
  * persist application/database state.

Important
---------
The frozen B.3 251-candidate run has no gold labels. Its accepted/rejected
decisions are therefore treated as teacher/reference behavior, not as
objective semantic accuracy.

Exit codes
----------
    0 = PASS, or preflight PASS when --run-live is not supplied
    1 = parity/migration-gate failure
    2 = frozen/service contract failure
    3 = missing/invalid input
    4 = live inference/runtime failure
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Repository defaults
# ---------------------------------------------------------------------------

DEFAULT_ROOT = Path("/opt/investment-os")

DEFAULT_B3_BENCHMARK = (
    DEFAULT_ROOT / "scripts" / "benchmark_openrouter_v3_3_b3.py"
)

DEFAULT_A12_GATE = (
    DEFAULT_ROOT / "generated" / "restomart"
    / "benchmark_qwen25_1p5b_v3_3_gate.json"
)

DEFAULT_B3_REFERENCE = (
    DEFAULT_ROOT / "generated" / "restomart"
    / "benchmark_openrouter_v3_3_b3_gptoss20b_coreweave_251.json"
)

DEFAULT_SMOKE = (
    DEFAULT_ROOT / "generated" / "restomart"
    / "benchmark_openrouter_v3_3_b3_gptoss20b_teacher_v2_smoke.json"
)

DEFAULT_REPORT = (
    DEFAULT_ROOT / "generated" / "restomart"
    / "v33_b3_teacher_decision_parity.json"
)

DEFAULT_STARTUP_DIR = (
    DEFAULT_ROOT / "data" / "real_startups" / "restomart"
)

DEFAULT_SERVICE_MODULE = (
    DEFAULT_ROOT / "app" / "services"
    / "semantic_candidate_validation.py"
)


# ---------------------------------------------------------------------------
# Frozen migration contract
# ---------------------------------------------------------------------------

EXPECTED_BENCHMARK_VERSION = (
    "V3.3-B.3-251-GPTOSS20B-COREWEAVE"
)
EXPECTED_PROMPT_VERSION = (
    "candidate-semantic-validation-v5-openrouter"
)

EXPECTED_SOURCE_BENCHMARK_VERSION = "V3.3-A.1.2"
EXPECTED_SOURCE_GATE_VERSION = "candidate-quality-gate-v1.3"

EXPECTED_MODEL = "openai/gpt-oss-20b"
EXPECTED_PROVIDER = "CoreWeave"

EXPECTED_RAW_CANDIDATES = 1167
EXPECTED_GATED_CANDIDATES = 251

EXPECTED_ACCEPTED = 110
EXPECTED_REJECTED = 141

EXPECTED_CONCURRENCY = 1
EXPECTED_TEMPERATURE = 0.0
EXPECTED_TOP_P = 1.0
EXPECTED_MAX_TOKENS = 1024
EXPECTED_REASONING_EFFORT = "medium"
EXPECTED_TIMEOUT_SEC = 120
EXPECTED_MAX_RETRIES = 3

EXPECTED_CONTEXT_MODE = "candidate_only"
EXPECTED_RESPONSE_FORMAT = "strict_json_schema"

# The frozen B.3 request pins CoreWeave and disables provider fallback.
EXPECTED_PROVIDER_PINNED = True
EXPECTED_ALLOW_FALLBACKS = False
EXPECTED_REQUIRE_PARAMETERS = True

# The frozen benchmark is observational and must not write canonical evidence.
EXPECTED_OBSERVATIONAL = True
EXPECTED_PRODUCTION_MODIFIED = False
EXPECTED_CANDIDATE_GENERATION_USED = False
EXPECTED_SEMANTIC_GATE_ONLY = True
EXPECTED_CLASSIFICATION_MODE = "structured_binary"
EXPECTED_GOLD_LABELS_AVAILABLE = False

# Candidate fields that must remain identical at the B.3 boundary.
CANDIDATE_FIELDS = (
    "candidate_id",
    "dimension",
    "field",
    "candidate_text",
    "signal",
    "source",
    "extraction",
    "document_kind",
    "signal_start",
    "signal_end",
)

# Nested source/extraction fields are compared explicitly as well.
SOURCE_FIELDS = (
    "source_id",
    "source_sha256",
    "source_path",
    "source_type",
    "source_category",
    "source_authority",
    "title",
    "page_count",
)

EXTRACTION_FIELDS = (
    "extraction_id",
    "extraction_method",
    "processor_name",
    "segment_index",
    "segment_metadata",
)

# Result fields whose equality is meaningful for parity.
RESULT_DECISION_FIELDS = (
    "candidate_id",
    "dimension",
    "field",
    "candidate_text",
    "actual_label",
)

# Exit codes.
EXIT_PASS = 0
EXIT_PARITY_FAILURE = 1
EXIT_CONTRACT_FAILURE = 2
EXIT_INPUT_FAILURE = 3
EXIT_EXECUTION_FAILURE = 4


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def load_module_from_path(
    path: Path,
    module_name: str,
) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Module not found: {path}")

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(path),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to create import specification for {path}"
        )

    module = importlib.util.module_from_spec(spec)

    # Required for modules containing dataclasses and other decorators
    # that resolve their defining module through sys.modules.
    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}: {exc}"
        ) from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def json_safe(value: Any) -> Any:
    """Convert common Python values into JSON-safe diagnostics."""
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Mapping):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if hasattr(value, "value"):
        return json_safe(value.value)

    return str(value)


def pct(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 0.0
    return round(
        100.0 * numerator / denominator,
        4,
    )


def normalize_candidate(candidate: Any) -> dict[str, Any]:
    """
    Normalize only representation.

    No semantic cleaning, trimming, lowercasing, ID generation, deduplication,
    or field transformation is performed here.
    """
    if isinstance(candidate, Mapping):
        return dict(candidate)

    def read(name: str, default: Any = None) -> Any:
        return getattr(candidate, name, default)

    return {
        "candidate_id": read("candidate_id"),
        "dimension": read("dimension"),
        "field": read("field"),
        "candidate_text": read(
            "candidate_text",
            read("text", ""),
        ),
        "signal": read("signal", ""),
        "source": read("source", {}),
        "extraction": read("extraction", {}),
        "document_kind": read("document_kind"),
        "signal_start": read("signal_start"),
        "signal_end": read("signal_end"),
    }


def normalize_current_result(result: Any) -> dict[str, Any]:
    """
    Convert SemanticValidationResult into the frozen benchmark comparison
    shape without changing semantic values.
    """
    if hasattr(result, "as_dict"):
        value = result.as_dict()
    elif isinstance(result, Mapping):
        value = dict(result)
    else:
        value = {
            "candidate_id": getattr(
                result,
                "candidate_id",
                None,
            ),
            "dimension": getattr(
                result,
                "dimension",
                None,
            ),
            "field": getattr(
                result,
                "field",
                None,
            ),
            "candidate_text": getattr(
                result,
                "candidate_text",
                None,
            ),
            "accepted": getattr(
                result,
                "accepted",
                None,
            ),
            "reason": getattr(
                result,
                "reason",
                "",
            ),
            "valid": getattr(
                result,
                "valid",
                False,
            ),
            "actual_label": getattr(
                result,
                "actual_label",
                None,
            ),
            "raw_response": getattr(
                result,
                "raw_response",
                "",
            ),
            "latency_sec": getattr(
                result,
                "latency_sec",
                0.0,
            ),
            "error": getattr(
                result,
                "error",
                "",
            ),
            "http_status": getattr(
                result,
                "http_status",
                None,
            ),
            "attempt_count": getattr(
                result,
                "attempt_count",
                0,
            ),
            "retry_count": getattr(
                result,
                "retry_count",
                0,
            ),
            "provider_requested": getattr(
                result,
                "provider_requested",
                None,
            ),
            "provider_actual": getattr(
                result,
                "provider_actual",
                None,
            ),
            "provider_match": getattr(
                result,
                "provider_match",
                False,
            ),
            "model_id": getattr(
                result,
                "model_id",
                None,
            ),
            "finish_reason": getattr(
                result,
                "finish_reason",
                None,
            ),
            "usage": getattr(
                result,
                "usage",
                {},
            ),
        }

    accepted = value.get("accepted")
    if accepted is True:
        actual_label = "A"
    elif accepted is False:
        actual_label = "R"
    else:
        actual_label = None

    if value.get("actual_label") is not None:
        actual_label = value.get("actual_label")

    return {
        "candidate_id": value.get("candidate_id"),
        "dimension": value.get("dimension"),
        "field": value.get("field"),
        "candidate_text": value.get("candidate_text"),
        "accepted": accepted,
        "actual_label": actual_label,
        "reason": value.get("reason", ""),
        "valid": bool(value.get("valid", False)),
        "raw_response": value.get("raw_response", ""),
        "latency_sec": float(
            value.get("latency_sec", 0.0) or 0.0
        ),
        "error": value.get("error", ""),
        "http_status": value.get("http_status"),
        "attempt_count": int(
            value.get("attempt_count", 0) or 0
        ),
        "retry_count": int(
            value.get("retry_count", 0) or 0
        ),
        "provider_requested": value.get(
            "provider_requested"
        ),
        "provider_actual": value.get(
            "provider_actual"
        ),
        "provider_match": value.get(
            "provider_match"
        ),
        "model_id": value.get("model_id"),
        "finish_reason": value.get(
            "finish_reason"
        ),
        "usage": json_safe(
            value.get("usage", {})
        ),
    }


# ---------------------------------------------------------------------------
# Frozen B.3 contract validation
# ---------------------------------------------------------------------------

def validate_frozen_b3_contract(
    benchmark: Any,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(
        name: str,
        expected: Any,
        actual: Any,
    ) -> None:
        checks.append({
            "name": name,
            "expected": json_safe(expected),
            "actual": json_safe(actual),
            "match": actual == expected,
        })

    check(
        "BENCHMARK_VERSION",
        EXPECTED_BENCHMARK_VERSION,
        getattr(benchmark, "BENCHMARK_VERSION", None),
    )
    check(
        "PROMPT_VERSION",
        EXPECTED_PROMPT_VERSION,
        getattr(benchmark, "PROMPT_VERSION", None),
    )
    check(
        "SOURCE_BENCHMARK_VERSION",
        EXPECTED_SOURCE_BENCHMARK_VERSION,
        getattr(
            benchmark,
            "SOURCE_BENCHMARK_VERSION",
            None,
        ),
    )
    check(
        "SOURCE_GATE_VERSION",
        EXPECTED_SOURCE_GATE_VERSION,
        getattr(
            benchmark,
            "SOURCE_GATE_VERSION",
            None,
        ),
    )
    check(
        "SOURCE_RAW_CANDIDATES",
        EXPECTED_RAW_CANDIDATES,
        getattr(
            benchmark,
            "SOURCE_RAW_CANDIDATES",
            None,
        ),
    )
    check(
        "EXPECTED_GATED_CANDIDATES",
        EXPECTED_GATED_CANDIDATES,
        getattr(
            benchmark,
            "EXPECTED_GATED_CANDIDATES",
            None,
        ),
    )
    check(
        "MODEL",
        EXPECTED_MODEL,
        getattr(benchmark, "MODEL", None),
    )
    check(
        "PROVIDER",
        EXPECTED_PROVIDER,
        getattr(benchmark, "PROVIDER", None),
    )
    check(
        "CONCURRENCY",
        EXPECTED_CONCURRENCY,
        getattr(benchmark, "CONCURRENCY", None),
    )
    check(
        "TEMPERATURE",
        EXPECTED_TEMPERATURE,
        getattr(benchmark, "TEMPERATURE", None),
    )
    check(
        "TOP_P",
        EXPECTED_TOP_P,
        getattr(benchmark, "TOP_P", None),
    )
    check(
        "MAX_TOKENS",
        EXPECTED_MAX_TOKENS,
        getattr(benchmark, "MAX_TOKENS", None),
    )
    check(
        "REASONING_EFFORT",
        EXPECTED_REASONING_EFFORT,
        getattr(
            benchmark,
            "REASONING_EFFORT",
            None,
        ),
    )

    # The frozen benchmark reads these from environment variables. Its
    # defaults are part of the frozen contract; the harness rejects overrides
    # that would change the benchmark contract.
    benchmark_timeout = getattr(
        benchmark,
        "TIMEOUT_SEC",
        None,
    )
    benchmark_retries = getattr(
        benchmark,
        "MAX_RETRIES",
        None,
    )
    benchmark_expected = getattr(
        benchmark,
        "EXPECTED_CANDIDATES",
        None,
    )

    check(
        "TIMEOUT_SEC",
        EXPECTED_TIMEOUT_SEC,
        benchmark_timeout,
    )
    check(
        "MAX_RETRIES",
        EXPECTED_MAX_RETRIES,
        benchmark_retries,
    )
    check(
        "EXPECTED_CANDIDATES",
        EXPECTED_GATED_CANDIDATES,
        benchmark_expected,
    )

    passed = all(
        bool(item["match"])
        for item in checks
    )

    return {
        "passed": passed,
        "checks": checks,
        "differences": [
            item
            for item in checks
            if not item["match"]
        ],
    }


# ---------------------------------------------------------------------------
# Smoke validation
# ---------------------------------------------------------------------------

def validate_smoke(
    benchmark: Any,
    smoke_path: Path,
) -> dict[str, Any]:
    """
    Reuse the frozen benchmark's own verify_smoke() implementation.

    This avoids duplicating the smoke contract in this harness.
    """
    try:
        smoke = benchmark.verify_smoke(smoke_path)
        return {
            "passed": True,
            "benchmark_version": smoke.get(
                "benchmark_version"
            ),
            "benchmark_type": smoke.get(
                "benchmark_type"
            ),
            "decision": smoke.get(
                "summary",
                {},
            ).get("decision"),
            "model": smoke.get("model"),
            "provider": smoke.get(
                "provider_requested"
            ),
            "structured_valid": smoke.get(
                "summary",
                {},
            ).get("structured_valid"),
            "correct": smoke.get(
                "summary",
                {},
            ).get("correct"),
            "positive": smoke.get(
                "summary",
                {},
            ).get("positive"),
            "negative": smoke.get(
                "summary",
                {},
            ).get("negative"),
            "provider_drift": smoke.get(
                "summary",
                {},
            ).get("provider_drift"),
            "input": smoke.get("input", {}),
        }
    except Exception as exc:
        return {
            "passed": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# A.1.2 population validation
# ---------------------------------------------------------------------------

def load_frozen_a12_population(
    benchmark: Any,
    a12_path: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    str,
]:
    source, candidates, selected_path = (
        benchmark.load_gate_population(a12_path)
    )

    normalized = [
        normalize_candidate(candidate)
        for candidate in candidates
    ]

    benchmark.validate_candidate_population(
        source,
        normalized,
    )

    return (
        source,
        normalized,
        selected_path,
    )


def validate_a12_population_metadata(
    source: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    raw = source.get("candidates", [])

    checks = {
        "benchmark_version": (
            source.get("benchmark_version")
            == EXPECTED_SOURCE_BENCHMARK_VERSION
        ),
        "gate_version": (
            source.get("gate_version")
            == EXPECTED_SOURCE_GATE_VERSION
        ),
        "raw_count": (
            isinstance(raw, list)
            and len(raw) == EXPECTED_RAW_CANDIDATES
        ),
        "passed_count": (
            len(candidates)
            == EXPECTED_GATED_CANDIDATES
        ),
        "observational": (
            source.get("observational") is True
        ),
        "production_pipeline_modified": (
            source.get("production_pipeline_modified")
            is False
        ),
        "llm_inference_used": (
            source.get("llm_inference_used")
            is False
        ),
    }

    return {
        "passed": all(checks.values()),
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Frozen B.3 result artifact validation
# ---------------------------------------------------------------------------

def load_reference_b3_result(
    path: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    data = load_json(path)

    if not isinstance(data, dict):
        raise ValueError(
            "Frozen B.3 result root must be an object."
        )

    benchmark_meta = data.get("benchmark")
    if not isinstance(benchmark_meta, dict):
        raise ValueError(
            "Frozen B.3 result has no benchmark object."
        )

    expected_benchmark_meta = {
        "benchmark_version":
            EXPECTED_BENCHMARK_VERSION,
        "prompt_version":
            EXPECTED_PROMPT_VERSION,
        "benchmark_type":
            "full_semantic_validation_teacher",
        "observational":
            EXPECTED_OBSERVATIONAL,
        "production_pipeline_modified":
            EXPECTED_PRODUCTION_MODIFIED,
        "candidate_generation_used":
            EXPECTED_CANDIDATE_GENERATION_USED,
        "llm_inference_used":
            True,
        "semantic_gate_only":
            EXPECTED_SEMANTIC_GATE_ONLY,
        "classification_mode":
            EXPECTED_CLASSIFICATION_MODE,
        "context_mode":
            EXPECTED_CONTEXT_MODE,
        "teacher_model":
            True,
        "gold_labels_available":
            EXPECTED_GOLD_LABELS_AVAILABLE,
    }

    metadata_differences = []

    for key, expected in expected_benchmark_meta.items():
        actual = benchmark_meta.get(key)

        if actual != expected:
            metadata_differences.append({
                "field": key,
                "expected": expected,
                "actual": actual,
            })

    if metadata_differences:
        raise ValueError(
            "Frozen B.3 reference artifact contract mismatch: "
            f"{metadata_differences}"
        )

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(
            "Frozen B.3 reference 'results' must be a list."
        )

    if len(results) != EXPECTED_GATED_CANDIDATES:
        raise ValueError(
            "Frozen B.3 reference result count mismatch: "
            f"{len(results)} != {EXPECTED_GATED_CANDIDATES}"
        )

    normalized_results: list[dict[str, Any]] = []

    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError(
                f"Frozen B.3 result {index} is not an object."
            )

        model = result.get("model")
        if not isinstance(model, dict):
            raise ValueError(
                f"Frozen B.3 result {index} has malformed model."
            )

        accepted = model.get("accepted")
        valid = model.get("valid")

        if valid is not True:
            raise ValueError(
                "Frozen B.3 reference contains invalid response "
                f"at index {index}: "
                f"{result.get('candidate_id')}"
            )

        if accepted not in (True, False):
            raise ValueError(
                "Frozen B.3 reference contains non-binary decision "
                f"at index {index}: "
                f"{result.get('candidate_id')}"
            )

        actual_label = result.get("actual_label")

        expected_label = (
            "A" if accepted is True else "R"
        )

        if actual_label != expected_label:
            raise ValueError(
                "Frozen B.3 actual_label mismatch for "
                f"{result.get('candidate_id')}: "
                f"{actual_label!r} != {expected_label!r}"
            )

        normalized_results.append({
            "candidate_id": result.get(
                "candidate_id"
            ),
            "dimension": result.get(
                "dimension"
            ),
            "field": result.get(
                "field"
            ),
            "candidate_text": result.get(
                "candidate_text"
            ),
            "actual_label": actual_label,
            "accepted": accepted,
            "valid": valid,
            "reason": model.get(
                "reason",
                "",
            ),
            "provider_requested": model.get(
                "provider_requested"
            ),
            "provider_actual": model.get(
                "provider_actual"
            ),
            "provider_match": model.get(
                "provider_match"
            ),
            "model_id": model.get(
                "model_id"
            ),
            "finish_reason": model.get(
                "finish_reason"
            ),
            "retry_count": int(
                model.get(
                    "retry_count",
                    0,
                )
                or 0
            ),
            "attempt_count": int(
                model.get(
                    "attempt_count",
                    0,
                )
                or 0
            ),
            "latency_sec": float(
                model.get(
                    "latency_sec",
                    0.0,
                )
                or 0.0
            ),
            "usage": json_safe(
                model.get("usage", {})
            ),
        })

    ids = [
        item["candidate_id"]
        for item in normalized_results
    ]

    if any(not item for item in ids):
        raise ValueError(
            "Frozen B.3 reference contains empty candidate IDs."
        )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Frozen B.3 reference contains duplicate candidate IDs."
        )

    population = data.get("population", {})
    if not isinstance(population, dict):
        raise ValueError(
            "Frozen B.3 reference population is malformed."
        )

    if population.get("expected") != EXPECTED_GATED_CANDIDATES:
        raise ValueError(
            "Frozen B.3 expected population mismatch."
        )

    if population.get("processed") != EXPECTED_GATED_CANDIDATES:
        raise ValueError(
            "Frozen B.3 processed population mismatch."
        )

    if population.get("valid") != EXPECTED_GATED_CANDIDATES:
        raise ValueError(
            "Frozen B.3 valid population mismatch."
        )

    if population.get("invalid") != 0:
        raise ValueError(
            "Frozen B.3 invalid count is not zero."
        )

    if population.get("accepted") != EXPECTED_ACCEPTED:
        raise ValueError(
            "Frozen B.3 accepted count mismatch: "
            f"{population.get('accepted')} != "
            f"{EXPECTED_ACCEPTED}"
        )

    if population.get("rejected") != EXPECTED_REJECTED:
        raise ValueError(
            "Frozen B.3 rejected count mismatch: "
            f"{population.get('rejected')} != "
            f"{EXPECTED_REJECTED}"
        )

    if population.get("provider_matches") != (
        EXPECTED_GATED_CANDIDATES
    ):
        raise ValueError(
            "Frozen B.3 provider match count mismatch."
        )

    if population.get("retry_count") != 0:
        raise ValueError(
            "Frozen B.3 reference is expected to have zero retries."
        )

    return data, normalized_results


# ---------------------------------------------------------------------------
# Candidate parity
# ---------------------------------------------------------------------------

def compare_candidate_population(
    reference_candidates: Sequence[Mapping[str, Any]],
    reference_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Confirm the frozen B.3 result was generated from the exact A.1.2
    candidate population.
    """
    candidate_by_id = {
        str(item["candidate_id"]): item
        for item in reference_candidates
    }

    result_by_id = {
        str(item["candidate_id"]): item
        for item in reference_results
    }

    candidate_ids = set(candidate_by_id)
    result_ids = set(result_by_id)

    missing = sorted(
        candidate_ids - result_ids
    )
    extra = sorted(
        result_ids - candidate_ids
    )

    differences: list[dict[str, Any]] = []

    for candidate_id in sorted(
        candidate_ids & result_ids
    ):
        candidate = candidate_by_id[candidate_id]
        result = result_by_id[candidate_id]

        for field in (
            "candidate_id",
            "dimension",
            "field",
            "candidate_text",
        ):
            expected = candidate.get(field)
            actual = result.get(field)

            if expected != actual:
                differences.append({
                    "candidate_id": candidate_id,
                    "field": field,
                    "expected": json_safe(expected),
                    "actual": json_safe(actual),
                })

    return {
        "reference_population": len(candidate_ids),
        "reference_results": len(result_ids),
        "missing_result_ids": missing,
        "extra_result_ids": extra,
        "attribute_differences": differences,
        "passed": (
            len(candidate_ids)
            == EXPECTED_GATED_CANDIDATES
            and len(result_ids)
            == EXPECTED_GATED_CANDIDATES
            and not missing
            and not extra
            and not differences
        ),
    }


# ---------------------------------------------------------------------------
# Prompt parity
# ---------------------------------------------------------------------------

def compare_prompt_parity(
    benchmark: Any,
    current_module: Any,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    frozen_builder = getattr(
        benchmark,
        "build_prompt",
        None,
    )
    current_builder = getattr(
        current_module,
        "build_prompt",
        None,
    )

    if not callable(frozen_builder):
        raise RuntimeError(
            "Frozen benchmark does not expose build_prompt()."
        )

    if not callable(current_builder):
        raise RuntimeError(
            "3.7.x semantic_candidate_validation module does not "
            "expose build_prompt()."
        )

    differences: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = str(
            candidate["candidate_id"]
        )
        field = str(candidate["field"])
        text = str(candidate["candidate_text"])

        frozen_prompt = frozen_builder(
            field,
            text,
        )
        current_prompt = current_builder(
            field,
            text,
        )

        frozen_json = json.dumps(
            frozen_prompt,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        current_json = json.dumps(
            current_prompt,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if frozen_json != current_json:
            first_difference = None

            limit = min(
                len(frozen_json),
                len(current_json),
            )

            for index in range(limit):
                if frozen_json[index] != current_json[index]:
                    first_difference = index
                    break

            if first_difference is None:
                first_difference = limit

            differences.append({
                "candidate_id": candidate_id,
                "field": field,
                "reference_prompt_sha256":
                    sha256_text(frozen_json),
                "current_prompt_sha256":
                    sha256_text(current_json),
                "first_difference_offset":
                    first_difference,
            })

    return {
        "checked": len(candidates),
        "identical": (
            len(candidates) - len(differences)
        ),
        "different": len(differences),
        "differences": differences,
        "passed": not differences,
    }


# ---------------------------------------------------------------------------
# Service configuration parity
# ---------------------------------------------------------------------------

def instantiate_current_service(
    current_module: Any,
    api_key: str | None,
) -> Any:
    service_class = getattr(
        current_module,
        "SemanticCandidateValidationService",
        None,
    )

    if service_class is None:
        raise RuntimeError(
            "3.7.x SemanticCandidateValidationService was not found."
        )

    return service_class(
        api_key=api_key,
        api_url=EXPECTED_API_URL(current_module),
        model=EXPECTED_MODEL,
        provider=EXPECTED_PROVIDER,
        temperature=EXPECTED_TEMPERATURE,
        top_p=EXPECTED_TOP_P,
        max_tokens=EXPECTED_MAX_TOKENS,
        reasoning_effort=EXPECTED_REASONING_EFFORT,
        timeout_sec=EXPECTED_TIMEOUT_SEC,
        max_retries=EXPECTED_MAX_RETRIES,
        concurrency=EXPECTED_CONCURRENCY,
    )


def EXPECTED_API_URL(
    current_module: Any,
) -> str:
    value = getattr(
        current_module,
        "API_URL",
        "https://openrouter.ai/api/v1/chat/completions",
    )

    if value != (
        "https://openrouter.ai/api/v1/chat/completions"
    ):
        raise RuntimeError(
            "3.7.x B.3 service API_URL differs from the frozen "
            "OpenRouter endpoint: "
            f"{value!r}"
        )

    return value


def compare_service_configuration(
    service: Any,
) -> dict[str, Any]:
    configuration = getattr(
        service,
        "configuration",
        None,
    )

    if not isinstance(configuration, dict):
        raise RuntimeError(
            "SemanticCandidateValidationService.configuration "
            "must be exposed as a dictionary."
        )

    checks = {
        "benchmark_version": (
            configuration.get("benchmark_version")
            == EXPECTED_BENCHMARK_VERSION
        ),
        "prompt_version": (
            configuration.get("prompt_version")
            == EXPECTED_PROMPT_VERSION
        ),
        "model": (
            configuration.get("model")
            == EXPECTED_MODEL
        ),
        "provider": (
            configuration.get("provider")
            == EXPECTED_PROVIDER
        ),
        "temperature": (
            configuration.get("temperature")
            == EXPECTED_TEMPERATURE
        ),
        "top_p": (
            configuration.get("top_p")
            == EXPECTED_TOP_P
        ),
        "max_tokens": (
            configuration.get("max_tokens")
            == EXPECTED_MAX_TOKENS
        ),
        "reasoning_effort": (
            configuration.get("reasoning_effort")
            == EXPECTED_REASONING_EFFORT
        ),
        "timeout_sec": (
            configuration.get("timeout_sec")
            == EXPECTED_TIMEOUT_SEC
        ),
        "max_retries": (
            configuration.get("max_retries")
            == EXPECTED_MAX_RETRIES
        ),
        "concurrency": (
            configuration.get("concurrency")
            == EXPECTED_CONCURRENCY
        ),
        "provider_fallbacks": (
            configuration.get("provider_fallbacks")
            is False
        ),
        "response_format": (
            configuration.get("response_format")
            == EXPECTED_RESPONSE_FORMAT
        ),
        "context_mode": (
            configuration.get("context_mode")
            == EXPECTED_CONTEXT_MODE
        ),
    }

    return {
        "configuration": json_safe(
            configuration
        ),
        "checks": checks,
        "passed": all(checks.values()),
    }


# ---------------------------------------------------------------------------
# Live result execution
# ---------------------------------------------------------------------------

def run_current_service(
    service: Any,
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    started = time.perf_counter()

    try:
        results = service.validate_many(
            list(candidates)
        )
    except Exception as exc:
        raise RuntimeError(
            f"3.7.x B.3 live execution failed: {exc}"
        ) from exc

    elapsed = (
        time.perf_counter()
        - started
    )

    normalized = [
        normalize_current_result(result)
        for result in results
    ]

    return normalized, {
        "wall_sec": round(elapsed, 4),
        "result_count": len(normalized),
    }


# ---------------------------------------------------------------------------
# Decision comparison
# ---------------------------------------------------------------------------

def compare_decisions(
    reference_results: Sequence[Mapping[str, Any]],
    current_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    reference_by_id = {
        str(item["candidate_id"]): item
        for item in reference_results
    }

    current_by_id = {
        str(item["candidate_id"]): item
        for item in current_results
    }

    reference_ids = set(reference_by_id)
    current_ids = set(current_by_id)

    missing = sorted(
        reference_ids - current_ids
    )
    extra = sorted(
        current_ids - reference_ids
    )

    validity_mismatches: list[dict[str, Any]] = []
    decision_mismatches: list[dict[str, Any]] = []
    identity_mismatches: list[dict[str, Any]] = []
    reason_differences: list[dict[str, Any]] = []
    provider_drift: list[dict[str, Any]] = []
    model_drift: list[dict[str, Any]] = []

    transitions = Counter()

    for candidate_id in sorted(
        reference_ids & current_ids
    ):
        reference = reference_by_id[candidate_id]
        current = current_by_id[candidate_id]

        for field in (
            "dimension",
            "field",
            "candidate_text",
        ):
            if reference.get(field) != current.get(field):
                identity_mismatches.append({
                    "candidate_id": candidate_id,
                    "field": field,
                    "reference": json_safe(
                        reference.get(field)
                    ),
                    "current": json_safe(
                        current.get(field)
                    ),
                })

        ref_valid = bool(
            reference.get("valid")
        )
        cur_valid = bool(
            current.get("valid")
        )

        if ref_valid != cur_valid:
            validity_mismatches.append({
                "candidate_id": candidate_id,
                "reference_valid": ref_valid,
                "current_valid": cur_valid,
            })

        ref_label = reference.get(
            "actual_label"
        )
        cur_label = current.get(
            "actual_label"
        )

        transition = (
            f"{ref_label or 'INVALID'}"
            f"_to_"
            f"{cur_label or 'INVALID'}"
        )
        transitions[transition] += 1

        if ref_label != cur_label:
            decision_mismatches.append({
                "candidate_id": candidate_id,
                "dimension": reference.get(
                    "dimension"
                ),
                "field": reference.get(
                    "field"
                ),
                "reference": {
                    "accepted": reference.get(
                        "accepted"
                    ),
                    "valid": reference.get(
                        "valid"
                    ),
                    "actual_label": ref_label,
                    "reason": reference.get(
                        "reason",
                        "",
                    ),
                },
                "current": {
                    "accepted": current.get(
                        "accepted"
                    ),
                    "valid": current.get(
                        "valid"
                    ),
                    "actual_label": cur_label,
                    "reason": current.get(
                        "reason",
                        "",
                    ),
                    "error": current.get(
                        "error",
                        "",
                    ),
                },
            })

        if (
            reference.get("reason", "")
            != current.get("reason", "")
        ):
            reason_differences.append({
                "candidate_id": candidate_id,
                "reference_reason": reference.get(
                    "reason",
                    "",
                ),
                "current_reason": current.get(
                    "reason",
                    "",
                ),
            })

        current_provider = current.get(
            "provider_actual"
        )

        if current_provider != EXPECTED_PROVIDER:
            provider_drift.append({
                "candidate_id": candidate_id,
                "expected": EXPECTED_PROVIDER,
                "actual": current_provider,
            })

        current_model = current.get(
            "model_id"
        )

        if current_model != EXPECTED_MODEL:
            model_drift.append({
                "candidate_id": candidate_id,
                "expected": EXPECTED_MODEL,
                "actual": current_model,
            })

    reference_accepted = sum(
        item.get("actual_label") == "A"
        for item in reference_results
    )
    reference_rejected = sum(
        item.get("actual_label") == "R"
        for item in reference_results
    )
    reference_invalid = sum(
        item.get("actual_label") is None
        for item in reference_results
    )

    current_accepted = sum(
        item.get("actual_label") == "A"
        for item in current_results
    )
    current_rejected = sum(
        item.get("actual_label") == "R"
        for item in current_results
    )
    current_invalid = sum(
        item.get("actual_label") is None
        for item in current_results
    )

    exact_matches = (
        len(reference_ids & current_ids)
        - len(decision_mismatches)
    )

    return {
        "reference_count": len(reference_results),
        "current_count": len(current_results),
        "missing_current_ids": missing,
        "extra_current_ids": extra,
        "identity_mismatches": identity_mismatches,
        "validity_mismatches": validity_mismatches,
        "decision_mismatches": decision_mismatches,
        "reason_differences": reason_differences,
        "provider_drift": provider_drift,
        "model_drift": model_drift,
        "reference": {
            "accepted": reference_accepted,
            "rejected": reference_rejected,
            "invalid": reference_invalid,
        },
        "current": {
            "accepted": current_accepted,
            "rejected": current_rejected,
            "invalid": current_invalid,
        },
        "exact_decision_matches": exact_matches,
        "transition_matrix": {
            "A_to_A": transitions.get(
                "A_to_A",
                0,
            ),
            "A_to_R": transitions.get(
                "A_to_R",
                0,
            ),
            "R_to_A": transitions.get(
                "R_to_A",
                0,
            ),
            "R_to_R": transitions.get(
                "R_to_R",
                0,
            ),
            "A_to_INVALID": transitions.get(
                "A_to_INVALID",
                0,
            ),
            "R_to_INVALID": transitions.get(
                "R_to_INVALID",
                0,
            ),
            "INVALID_to_A": transitions.get(
                "INVALID_to_A",
                0,
            ),
            "INVALID_to_R": transitions.get(
                "INVALID_to_R",
                0,
            ),
            "INVALID_to_INVALID": transitions.get(
                "INVALID_to_INVALID",
                0,
            ),
        },
        "passed": (
            len(reference_results)
            == EXPECTED_GATED_CANDIDATES
            and len(current_results)
            == EXPECTED_GATED_CANDIDATES
            and not missing
            and not extra
            and not identity_mismatches
            and not validity_mismatches
            and not decision_mismatches
            and not provider_drift
            and not model_drift
            and current_accepted == EXPECTED_ACCEPTED
            and current_rejected == EXPECTED_REJECTED
            and current_invalid == 0
        ),
    }


# ---------------------------------------------------------------------------
# Runtime / provider statistics
# ---------------------------------------------------------------------------

def summarize_current_results(
    results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    valid = sum(
        bool(item.get("valid"))
        for item in results
    )
    accepted = sum(
        item.get("actual_label") == "A"
        for item in results
    )
    rejected = sum(
        item.get("actual_label") == "R"
        for item in results
    )
    invalid = sum(
        item.get("actual_label") is None
        for item in results
    )

    provider_matches = sum(
        item.get("provider_actual")
        == EXPECTED_PROVIDER
        for item in results
    )

    model_matches = sum(
        item.get("model_id")
        == EXPECTED_MODEL
        for item in results
    )

    retries = sum(
        int(item.get("retry_count", 0) or 0)
        for item in results
    )

    attempts = sum(
        int(item.get("attempt_count", 0) or 0)
        for item in results
    )

    latencies = [
        float(item.get("latency_sec", 0.0) or 0.0)
        for item in results
    ]

    finish_reasons = Counter(
        item.get("finish_reason")
        or "unknown"
        for item in results
    )

    provider_counts = Counter(
        item.get("provider_actual")
        or "unknown"
        for item in results
    )

    errors = Counter(
        (
            str(item.get("error"))
            .split(":", 1)[0]
            if item.get("error")
            else ""
        )
        for item in results
    )

    errors.pop("", None)

    usage_prompt = 0
    usage_completion = 0
    usage_total = 0
    usage_cost = 0.0
    cost_records = 0

    for item in results:
        usage = item.get("usage") or {}

        usage_prompt += int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or 0
        )
        usage_completion += int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or 0
        )
        usage_total += int(
            usage.get("total_tokens")
            or 0
        )

        cost = usage.get("cost")

        if isinstance(cost, (int, float)):
            usage_cost += float(cost)
            cost_records += 1

    sorted_latencies = sorted(latencies)

    if sorted_latencies:
        p95_index = min(
            len(sorted_latencies) - 1,
            max(
                0,
                int(
                    0.95
                    * len(sorted_latencies)
                ) - 1,
            ),
        )
        p95 = sorted_latencies[p95_index]
    else:
        p95 = 0.0

    return {
        "processed": len(results),
        "valid": valid,
        "invalid": invalid,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_pct": pct(
            accepted,
            len(results),
        ),
        "provider_matches": provider_matches,
        "provider_match_pct": pct(
            provider_matches,
            len(results),
        ),
        "model_matches": model_matches,
        "model_match_pct": pct(
            model_matches,
            len(results),
        ),
        "retry_count": retries,
        "attempt_count": attempts,
        "provider_actual_counts": dict(
            provider_counts
        ),
        "finish_reason_counts": dict(
            finish_reasons
        ),
        "error_counts": dict(errors),
        "latency": {
            "average_sec": round(
                sum(latencies)
                / len(latencies),
                4,
            )
            if latencies
            else 0.0,
            "min_sec": round(
                min(latencies),
                4,
            )
            if latencies
            else 0.0,
            "max_sec": round(
                max(latencies),
                4,
            )
            if latencies
            else 0.0,
            "p95_sec": round(
                p95,
                4,
            ),
        },
        "usage": {
            "prompt_tokens": usage_prompt,
            "completion_tokens": usage_completion,
            "total_tokens": usage_total,
            "reported_cost_usd": round(
                usage_cost,
                8,
            ),
            "cost_records": cost_records,
        },
    }


# ---------------------------------------------------------------------------
# Production safety
# ---------------------------------------------------------------------------

def snapshot_protected_files(
    startup_dir: Path,
) -> dict[str, str | None]:
    paths = {
        "dimension_evidence.json":
            startup_dir / "dimension_evidence.json",
        "investment_scorecard.json":
            startup_dir / "investment_scorecard.json",
        "startup.yaml":
            startup_dir / "startup.yaml",
    }

    return {
        name: sha256_file(path)
        for name, path in paths.items()
    }


def compare_protected_files(
    before: Mapping[str, str | None],
    after: Mapping[str, str | None],
) -> dict[str, Any]:
    changed = []

    for name in sorted(
        set(before) | set(after)
    ):
        if before.get(name) != after.get(name):
            changed.append({
                "file": name,
                "before_sha256": before.get(name),
                "after_sha256": after.get(name),
            })

    return {
        "changed": changed,
        "changed_count": len(changed),
        "passed": not changed,
    }


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_header() -> None:
    print()
    print("=" * 68)
    print("V3.3-B.3 → 3.7.x TEACHER DECISION PARITY")
    print("=" * 68)


def print_summary(
    report: Mapping[str, Any],
) -> None:
    benchmark = report["benchmark"]
    population = report["population"]
    candidate = report["candidate_parity"]
    prompt = report["prompt_parity"]
    config = report["service_configuration"]

    print()
    print("Benchmark")
    print(
        f"  Version              : "
        f"{benchmark['benchmark_version']}"
    )
    print(
        f"  Prompt               : "
        f"{benchmark['prompt_version']}"
    )
    print(
        f"  Model                : "
        f"{benchmark['model']}"
    )
    print(
        f"  Provider             : "
        f"{benchmark['provider']}"
    )

    print()
    print("Population")
    print(
        f"  A.1.2 raw            : "
        f"{population['raw_count']}"
    )
    print(
        f"  A.1.2 PASS           : "
        f"{population['gated_count']}"
    )
    print(
        f"  B.3 reference        : "
        f"{population['reference_result_count']}"
    )
    print(
        f"  3.7.x                : "
        f"{population.get('current_result_count', 'NOT RUN')}"
    )
    print(
        f"  Missing               : "
        f"{len(population['missing_result_ids'])}"
    )
    print(
        f"  Extra                 : "
        f"{len(population['extra_result_ids'])}"
    )

    print()
    print("Candidate Parity")
    print(
        f"  Identical             : "
        f"{candidate['identical']}"
    )
    print(
        f"  Differences           : "
        f"{candidate['different']}"
    )

    print()
    print("Prompt Parity")
    print(
        f"  Identical             : "
        f"{prompt['identical']}"
    )
    print(
        f"  Differences           : "
        f"{prompt['different']}"
    )

    print()
    print("Service Configuration")
    print(
        f"  Contract              : "
        f"{'PASS' if config['passed'] else 'FAIL'}"
    )

    decision = report.get(
        "decision_parity"
    )

    if isinstance(decision, Mapping):
        print()
        print("Validity")
        print(
            f"  Reference valid       : "
            f"{decision['reference']['accepted'] + decision['reference']['rejected']}"
        )
        print(
            f"  3.7.x valid           : "
            f"{decision['current']['accepted'] + decision['current']['rejected']}"
        )
        print(
            f"  3.7.x invalid         : "
            f"{decision['current']['invalid']}"
        )

        print()
        print("Decisions")
        print(
            f"  Reference accepted    : "
            f"{decision['reference']['accepted']}"
        )
        print(
            f"  Reference rejected    : "
            f"{decision['reference']['rejected']}"
        )
        print(
            f"  3.7.x accepted        : "
            f"{decision['current']['accepted']}"
        )
        print(
            f"  3.7.x rejected        : "
            f"{decision['current']['rejected']}"
        )

        print()
        print("Teacher Decision Parity")
        print(
            f"  Exact                 : "
            f"{decision['exact_decision_matches']}/"
            f"{EXPECTED_GATED_CANDIDATES}"
        )
        print(
            f"  Mismatches            : "
            f"{len(decision['decision_mismatches'])}"
        )

        matrix = decision["transition_matrix"]

        print()
        print("Transitions")
        print(
            f"  A → A                 : "
            f"{matrix['A_to_A']}"
        )
        print(
            f"  A → R                 : "
            f"{matrix['A_to_R']}"
        )
        print(
            f"  R → A                 : "
            f"{matrix['R_to_A']}"
        )
        print(
            f"  R → R                 : "
            f"{matrix['R_to_R']}"
        )

    provider = report.get(
        "provider",
    )

    if isinstance(provider, Mapping):
        print()
        print("Provider")
        print(
            f"  CoreWeave             : "
            f"{provider['matches']}/"
            f"{provider['checked']}"
        )
        print(
            f"  Drift                 : "
            f"{provider['drift']}"
        )

    safety = report.get(
        "production_safety",
    )

    if isinstance(safety, Mapping):
        print()
        print("Production Safety")
        print(
            f"  Protected files       : "
            f"{'UNCHANGED' if safety['passed'] else 'CHANGED'}"
        )

    print()
    print("=" * 68)
    print(
        f"STATUS                    : "
        f"{report['status']}"
    )
    print(
        f"REPORT                    : "
        f"{report['report_path']}"
    )
    print("=" * 68)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate V3.3-B.3 teacher-decision parity "
            "against the 3.7.x semantic candidate service."
        )
    )

    parser.add_argument(
        "--benchmark",
        default=str(DEFAULT_B3_BENCHMARK),
        help="Frozen benchmark_openrouter_v3_3_b3.py",
    )

    parser.add_argument(
        "--a12-gate",
        default=str(DEFAULT_A12_GATE),
        help="Frozen V3.3-A.1.2 gate artifact.",
    )

    parser.add_argument(
        "--b3-reference",
        default=str(DEFAULT_B3_REFERENCE),
        help="Frozen 251-candidate B.3 result artifact.",
    )

    parser.add_argument(
        "--smoke",
        default=str(DEFAULT_SMOKE),
        help="Frozen controlled B.3 teacher smoke artifact.",
    )

    parser.add_argument(
        "--service",
        default=str(DEFAULT_SERVICE_MODULE),
        help="3.7.x semantic_candidate_validation.py",
    )

    parser.add_argument(
        "--startup-dir",
        default=str(DEFAULT_STARTUP_DIR),
        help=(
            "Startup directory containing protected production "
            "artifacts."
        ),
    )

    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Output parity report.",
    )

    parser.add_argument(
        "--run-live",
        action="store_true",
        help=(
            "Execute 3.7.x B.3 inference against the exact "
            "251 frozen candidates."
        ),
    )

    parser.add_argument(
        "--authorize",
        action="store_true",
        help=(
            "Explicitly authorize live 251-candidate inference. "
            "Required together with --run-live."
        ),
    )

    return parser


def run() -> int:
    parser = build_parser()
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    a12_path = Path(args.a12_gate)
    b3_reference_path = Path(args.b3_reference)
    smoke_path = Path(args.smoke)
    service_path = Path(args.service)
    startup_dir = Path(args.startup_dir)
    report_path = Path(args.report)

    print_header()

    # ------------------------------------------------------------------
    # Load frozen benchmark.
    # ------------------------------------------------------------------
    try:
        benchmark = load_module_from_path(
            benchmark_path,
            "_frozen_b3_parity_benchmark",
        )

        frozen_contract = (
            validate_frozen_b3_contract(
                benchmark
            )
        )

        if not frozen_contract["passed"]:
            raise ValueError(
                "Frozen B.3 benchmark contract mismatch."
            )
    except Exception as exc:
        print(
            f"ERROR: frozen benchmark validation failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    # ------------------------------------------------------------------
    # Verify controlled smoke exactly as frozen B.3 does.
    # ------------------------------------------------------------------
    smoke = validate_smoke(
        benchmark,
        smoke_path,
    )

    if not smoke["passed"]:
        print(
            "ERROR: controlled B.3 teacher smoke validation failed: "
            f"{smoke.get('error', 'unknown error')}",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    # ------------------------------------------------------------------
    # Load exact frozen A.1.2 -> 251 population.
    # ------------------------------------------------------------------
    try:
        (
            a12_source,
            candidates,
            selected_path,
        ) = load_frozen_a12_population(
            benchmark,
            a12_path,
        )

        a12_metadata = (
            validate_a12_population_metadata(
                a12_source,
                candidates,
            )
        )

        if not a12_metadata["passed"]:
            raise ValueError(
                "A.1.2 population metadata validation failed: "
                f"{a12_metadata['checks']}"
            )
    except Exception as exc:
        print(
            f"ERROR: A.1.2 population validation failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_INPUT_FAILURE

    # ------------------------------------------------------------------
    # Load and validate frozen B.3 reference result.
    # ------------------------------------------------------------------
    try:
        (
            b3_reference,
            reference_results,
        ) = load_reference_b3_result(
            b3_reference_path
        )
    except Exception as exc:
        print(
            f"ERROR: frozen B.3 reference validation failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_INPUT_FAILURE

    # ------------------------------------------------------------------
    # Validate that the frozen B.3 result corresponds to the exact
    # frozen A.1.2 population.
    # ------------------------------------------------------------------
    frozen_candidate_parity = (
        compare_candidate_population(
            candidates,
            reference_results,
        )
    )

    if not frozen_candidate_parity["passed"]:
        print(
            "ERROR: frozen B.3 result does not correspond to the "
            "exact A.1.2 251-candidate population.",
            file=sys.stderr,
        )
        return EXIT_PARITY_FAILURE

    # ------------------------------------------------------------------
    # Load current 3.7.x service module.
    # ------------------------------------------------------------------
    try:
        current_module = load_module_from_path(
            service_path,
            "_current_b3_semantic_validation",
        )

        current_service_contract = (
            getattr(
                current_module,
                "SemanticCandidateValidationService",
                None,
            )
        )

        if current_service_contract is None:
            raise RuntimeError(
                "SemanticCandidateValidationService not found."
            )

        # Prompt parity is deliberately checked without making API calls.
        prompt_parity = compare_prompt_parity(
            benchmark,
            current_module,
            candidates,
        )

        api_url = EXPECTED_API_URL(
            current_module
        )

        service = current_service_contract(
            api_key=os.getenv(
                "OPENROUTER_API_KEY",
                "",
            ).strip(),
            api_url=api_url,
            model=EXPECTED_MODEL,
            provider=EXPECTED_PROVIDER,
            temperature=EXPECTED_TEMPERATURE,
            top_p=EXPECTED_TOP_P,
            max_tokens=EXPECTED_MAX_TOKENS,
            reasoning_effort=EXPECTED_REASONING_EFFORT,
            timeout_sec=EXPECTED_TIMEOUT_SEC,
            max_retries=EXPECTED_MAX_RETRIES,
            concurrency=EXPECTED_CONCURRENCY,
        )

        service_configuration = (
            compare_service_configuration(
                service
            )
        )

    except Exception as exc:
        print(
            f"ERROR: 3.7.x service validation failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    # ------------------------------------------------------------------
    # Protected production artifacts.
    # ------------------------------------------------------------------
    protected_before = (
        snapshot_protected_files(
            startup_dir
        )
    )

    # ------------------------------------------------------------------
    # Build base report before optional live execution.
    # ------------------------------------------------------------------
    report: dict[str, Any] = {
        "report_version": "b3-teacher-decision-parity-v1",
        "benchmark": {
            "benchmark_version":
                EXPECTED_BENCHMARK_VERSION,
            "prompt_version":
                EXPECTED_PROMPT_VERSION,
            "source_benchmark_version":
                EXPECTED_SOURCE_BENCHMARK_VERSION,
            "source_gate_version":
                EXPECTED_SOURCE_GATE_VERSION,
            "model":
                EXPECTED_MODEL,
            "provider":
                EXPECTED_PROVIDER,
            "context_mode":
                EXPECTED_CONTEXT_MODE,
            "observational":
                True,
            "teacher_model":
                True,
            "gold_labels_available":
                False,
        },
        "paths": {
            "benchmark":
                str(benchmark_path),
            "a12_gate":
                str(a12_path),
            "b3_reference":
                str(b3_reference_path),
            "smoke":
                str(smoke_path),
            "service":
                str(service_path),
            "startup_dir":
                str(startup_dir),
        },
        "population": {
            "raw_count":
                len(a12_source.get("candidates", [])),
            "gated_count":
                len(candidates),
            "reference_result_count":
                len(reference_results),
            "current_result_count":
                None,
            "missing_result_ids":
                frozen_candidate_parity[
                    "missing_result_ids"
                ],
            "extra_result_ids":
                frozen_candidate_parity[
                    "extra_result_ids"
                ],
            "candidate_path":
                selected_path,
        },
        "smoke": smoke,
        "frozen_contract": frozen_contract,
        "a12_metadata": a12_metadata,
        "candidate_parity": {
            "checked":
                EXPECTED_GATED_CANDIDATES,
            "identical":
                EXPECTED_GATED_CANDIDATES
                if frozen_candidate_parity[
                    "passed"
                ]
                else (
                    EXPECTED_GATED_CANDIDATES
                    - len(
                        frozen_candidate_parity[
                            "attribute_differences"
                        ]
                    )
                ),
            "different":
                len(
                    frozen_candidate_parity[
                        "attribute_differences"
                    ]
                ),
            "missing":
                len(
                    frozen_candidate_parity[
                        "missing_result_ids"
                    ]
                ),
            "extra":
                len(
                    frozen_candidate_parity[
                        "extra_result_ids"
                    ]
                ),
            "differences":
                frozen_candidate_parity[
                    "attribute_differences"
                ],
            "passed":
                frozen_candidate_parity[
                    "passed"
                ],
        },
        "prompt_parity": prompt_parity,
        "service_configuration": service_configuration,
        "reference": {
            "processed":
                len(reference_results),
            "valid":
                sum(
                    bool(item.get("valid"))
                    for item in reference_results
                ),
            "accepted":
                sum(
                    item.get("actual_label") == "A"
                    for item in reference_results
                ),
            "rejected":
                sum(
                    item.get("actual_label") == "R"
                    for item in reference_results
                ),
            "invalid":
                sum(
                    item.get("actual_label") is None
                    for item in reference_results
                ),
            "provider_matches":
                sum(
                    item.get("provider_actual")
                    == EXPECTED_PROVIDER
                    for item in reference_results
                ),
            "retry_count":
                sum(
                    int(
                        item.get(
                            "retry_count",
                            0,
                        )
                        or 0
                    )
                    for item in reference_results
                ),
        },
        "provider": {
            "checked":
                EXPECTED_GATED_CANDIDATES,
            "matches":
                EXPECTED_GATED_CANDIDATES,
            "drift":
                0,
            "expected":
                EXPECTED_PROVIDER,
        },
        "model": {
            "checked":
                EXPECTED_GATED_CANDIDATES,
            "matches":
                EXPECTED_GATED_CANDIDATES,
            "drift":
                0,
            "expected":
                EXPECTED_MODEL,
        },
        "production_safety": {
            "observational": True,
            "production_pipeline_modified": False,
            "protected_files_changed": [],
            "passed": True,
        },
        "execution": {
            "live": bool(args.run_live),
            "authorized": bool(args.authorize),
            "api_calls": 0,
        },
        "reference_artifact": {
            "benchmark_status":
                b3_reference.get("status"),
            "full_benchmark_authorized":
                b3_reference.get(
                    "full_benchmark_authorized"
                ),
            "usage":
                b3_reference.get(
                    "usage",
                    {},
                ),
            "timing":
                b3_reference.get(
                    "timing",
                    {},
                ),
        },
    }

    # ------------------------------------------------------------------
    # Preflight-only mode.
    # ------------------------------------------------------------------
    if not args.run_live:
        preflight_pass = all([
            frozen_contract["passed"],
            smoke["passed"],
            a12_metadata["passed"],
            frozen_candidate_parity["passed"],
            prompt_parity["passed"],
            service_configuration["passed"],
        ])

        report["status"] = (
            "PREFLIGHT_PASS"
            if preflight_pass
            else "PREFLIGHT_FAIL"
        )
        report["migration_gate"] = {
            "ready_for_live":
                preflight_pass,
            "teacher_decision_parity":
                "NOT_RUN",
        }

        report["report_path"] = str(
            report_path
        )

        write_json(
            report_path,
            report,
        )

        print_summary(report)

        return (
            EXIT_PASS
            if preflight_pass
            else EXIT_PARITY_FAILURE
        )

    # ------------------------------------------------------------------
    # Live mode requires explicit authorization.
    # ------------------------------------------------------------------
    if not args.authorize:
        print(
            "BLOCKED: --run-live requires --authorize.",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    api_key = os.getenv(
        "OPENROUTER_API_KEY",
        "",
    ).strip()

    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY is not set.",
            file=sys.stderr,
        )
        return EXIT_INPUT_FAILURE

    if not frozen_contract["passed"]:
        print(
            "BLOCKED: frozen B.3 contract failed.",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    if not smoke["passed"]:
        print(
            "BLOCKED: controlled teacher smoke failed.",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    if not prompt_parity["passed"]:
        print(
            "BLOCKED: prompt parity failed.",
            file=sys.stderr,
        )
        return EXIT_PARITY_FAILURE

    if not service_configuration["passed"]:
        print(
            "BLOCKED: 3.7.x service configuration parity failed.",
            file=sys.stderr,
        )
        return EXIT_CONTRACT_FAILURE

    print()
    print(
        "B.3 LIVE TEACHER PARITY AUTHORIZED"
    )
    print(
        f"  Candidates            : "
        f"{len(candidates)}"
    )
    print(
        f"  Model                 : "
        f"{EXPECTED_MODEL}"
    )
    print(
        f"  Provider              : "
        f"{EXPECTED_PROVIDER}"
    )
    print(
        "  Fallback              : disabled"
    )
    print(
        "  Context               : candidate_only"
    )
    print()

    # ------------------------------------------------------------------
    # Execute the 3.7.x service against the exact frozen 251 candidates.
    # ------------------------------------------------------------------
    try:
        current_results, execution = (
            run_current_service(
                service,
                candidates,
            )
        )
    except Exception as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return EXIT_EXECUTION_FAILURE

    report["execution"] = {
        "live": True,
        "authorized": True,
        "api_calls":
            len(current_results),
        **execution,
    }

    report["population"][
        "current_result_count"
    ] = len(current_results)

    current_summary = (
        summarize_current_results(
            current_results
        )
    )

    decision_parity = (
        compare_decisions(
            reference_results,
            current_results,
        )
    )

    report["current"] = current_summary
    report["decision_parity"] = decision_parity

    report["provider"] = {
        "checked":
            len(current_results),
        "matches":
            current_summary[
                "provider_matches"
            ],
        "drift":
            len(
                decision_parity[
                    "provider_drift"
                ]
            ),
        "expected":
            EXPECTED_PROVIDER,
        "actual_counts":
            current_summary[
                "provider_actual_counts"
            ],
    }

    report["model"] = {
        "checked":
            len(current_results),
        "matches":
            current_summary[
                "model_matches"
            ],
        "drift":
            len(
                decision_parity[
                    "model_drift"
                ]
            ),
        "expected":
            EXPECTED_MODEL,
    }

    # ------------------------------------------------------------------
    # Production safety after live execution.
    # ------------------------------------------------------------------
    protected_after = (
        snapshot_protected_files(
            startup_dir
        )
    )

    production_safety = (
        compare_protected_files(
            protected_before,
            protected_after,
        )
    )

    report["production_safety"] = {
        "observational": True,
        "production_pipeline_modified":
            False,
        "before_sha256":
            protected_before,
        "after_sha256":
            protected_after,
        "protected_files_changed":
            production_safety["changed"],
        "changed_count":
            production_safety["changed_count"],
        "passed":
            production_safety["passed"],
    }

    # ------------------------------------------------------------------
    # Final migration gate.
    # ------------------------------------------------------------------
    migration_gate = {
        "frozen_contract":
            frozen_contract["passed"],
        "smoke":
            smoke["passed"],
        "a12_population":
            a12_metadata["passed"],
        "frozen_candidate_population":
            frozen_candidate_parity["passed"],
        "candidate_parity":
            prompt_parity["passed"],
        "prompt_parity":
            prompt_parity["passed"],
        "service_configuration":
            service_configuration["passed"],
        "current_all_processed":
            len(current_results)
            == EXPECTED_GATED_CANDIDATES,
        "current_all_valid":
            current_summary["valid"]
            == EXPECTED_GATED_CANDIDATES,
        "decision_parity":
            decision_parity["passed"],
        "provider_parity":
            len(
                decision_parity[
                    "provider_drift"
                ]
            ) == 0,
        "model_parity":
            len(
                decision_parity[
                    "model_drift"
                ]
            ) == 0,
        "production_safety":
            production_safety["passed"],
    }

    report["migration_gate"] = migration_gate

    report["status"] = (
        "PASS"
        if all(migration_gate.values())
        else "FAIL"
    )

    report["mismatch_summary"] = {
        "candidate_identity":
            len(
                decision_parity[
                    "identity_mismatches"
                ]
            ),
        "validity":
            len(
                decision_parity[
                    "validity_mismatches"
                ]
            ),
        "decision":
            len(
                decision_parity[
                    "decision_mismatches"
                ]
            ),
        "reason_diagnostic":
            len(
                decision_parity[
                    "reason_differences"
                ]
            ),
        "provider":
            len(
                decision_parity[
                    "provider_drift"
                ]
            ),
        "model":
            len(
                decision_parity[
                    "model_drift"
                ]
            ),
    }

    report["report_path"] = str(
        report_path
    )

    write_json(
        report_path,
        report,
    )

    print_summary(report)

    return (
        EXIT_PASS
        if report["status"] == "PASS"
        else EXIT_PARITY_FAILURE
    )


if __name__ == "__main__":
    raise SystemExit(run())
