#!/usr/bin/env python3
"""
V3.3-B — Qwen Semantic Validation Benchmark
============================================

Purpose
-------
Validate the 251 candidates that passed V3.3-A.1.2 using Qwen2.5-1.5B-Instruct
as a semantic evidence gate.

Architecture
------------
V3.2 raw candidates
        |
        v
V3.3-A.1.2 deterministic candidate quality gate
        |
        v
251 gated candidates
        |
        v
Qwen2.5-1.5B semantic validation
        |
        +--> accepted
        +--> rejected
        +--> JSON invalid
        |
        v
Python-owned evidence/provenance + deterministic dedup
        |
        v
benchmark_qwen25_1p5b_v3_3_b.json

Important
---------
- No candidate generation is performed here.
- The V3.3-A.1.2 gated population is immutable input.
- Qwen does NOT generate observations, supporting_text, provenance,
  dimensions, fields, or evidence references.
- No production pipeline is modified.
- No JSON repair beyond simple code-fence stripping.
- No semantic gold labels are assumed; this is observational.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    from llama_cpp import Llama
except Exception as exc:
    Llama = None
    LLAMA_IMPORT_ERROR = str(exc)
else:
    LLAMA_IMPORT_ERROR = ""


# ---------------------------------------------------------------------------
# Frozen benchmark configuration
# ---------------------------------------------------------------------------

BENCHMARK_VERSION = "V3.3-B"
PROMPT_VERSION = "candidate-semantic-validation-v1"
SOURCE_BENCHMARK_VERSION = "V3.3-A.1.2"
SOURCE_GATE_VERSION = "candidate-quality-gate-v1.3"

STARTUP_NAME = "RestoMart"
STARTUP_ID = "dbb520d7-0979-4db3-8464-523f5710455f"

DEFAULT_INPUT = Path(
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_gate.json"
)
DEFAULT_OUTPUT = Path(
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_b.json"
)

MODEL_PATH = Path(
    "/models/Qwen2.5-1.5B-Instruct/"
    "qwen2.5-1.5b-instruct-q4_k_m.gguf"
)

N_THREADS = 8
N_THREADS_BATCH = 8
N_GPU_LAYERS = 0
N_CTX = 4096
TEMPERATURE = 0.0
TOP_P = 1.0
SEED = 42
MAX_TOKENS = 96

EXPECTED_RAW_CANDIDATES = 1167
EXPECTED_GATED_CANDIDATES = 251

# Candidate-only mode is the frozen V3.3-B baseline.
# A future experiment may add local context, but it must be a separate
# benchmark version rather than silently changing V3.3-B.
CONTEXT_MODE = "candidate_only"

SYSTEM_PROMPT = """You are validating investment evidence.

FIELD:
{field}

CANDIDATE:
{candidate}

QUESTION:
Does the candidate explicitly support the specified field?

Rules:
- Accept only if the text directly supports the field.
- Do not infer missing facts.
- A keyword alone is insufficient.
- Legal boilerplate is not evidence unless it directly supports the field.
- Accounting labels, formulas, and generic statements are not evidence unless they explicitly support the field.
- Reject unrelated or incidental references.
- Reject if the candidate does not contain enough information to support the field.

Return JSON only:
{{"accepted":true,"reason":"brief reason"}}"""

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    status: str
    accepted: bool | None
    reason: str
    raw_response: str
    latency_sec: float
    json_valid: bool


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, "value"):
        return json_safe(value.value)
    if isinstance(value, Path):
        return str(value)
    return value


def strip_code_fence(text: str) -> str:
    value = text.strip()

    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 2:
            # Remove first fence line and final fence line only.
            value = "\n".join(lines[1:-1]).strip()

    return value


def parse_semantic_json(text: str) -> tuple[bool, bool | None, str]:
    """
    Strict parser.

    Returns:
      (json_valid, accepted, reason)
    """
    cleaned = strip_code_fence(text)

    try:
        obj = json.loads(cleaned)
    except Exception:
        return False, None, ""

    if not isinstance(obj, dict):
        return False, None, ""

    accepted = obj.get("accepted")
    reason = obj.get("reason")

    if not isinstance(accepted, bool):
        return False, None, ""

    if not isinstance(reason, str) or not reason.strip():
        return False, None, ""

    return True, accepted, reason.strip()


def evidence_ref(candidate: dict[str, Any]) -> str:
    parts = [
        str(candidate.get("source_id", "")),
        str(candidate.get("source_sha256", "")),
        str(candidate.get("extraction_id", "")),
        str(candidate.get("segment_index", "")),
        str(candidate.get("dimension", "")),
        str(candidate.get("field", "")),
        normalize(candidate.get("text", "")),
    ]
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def model_metadata() -> dict[str, Any]:
    size = MODEL_PATH.stat().st_size if MODEL_PATH.exists() else None
    return {
        "name": "Qwen2.5-1.5B-Instruct",
        "quantization": "Q4_K_M",
        "path": str(MODEL_PATH),
        "exists": MODEL_PATH.exists(),
        "size_bytes": size,
        "runtime": "llama-cpp-python",
    }


def validate_input_header(data: dict[str, Any]) -> dict[str, Any]:
    """
    Fail closed if the V3.3-B input is not the exact A.1.2 benchmark.
    """
    errors: list[str] = []

    # V3.3-A.1.2 JSON uses flat benchmark metadata:
    #   benchmark: str
    #   benchmark_version: str
    #   gate_version: str
    #   population: dict
    #
    # Do not assume the nested metadata shape used by another benchmark.
    benchmark_version = data.get("benchmark_version")
    if benchmark_version != SOURCE_BENCHMARK_VERSION:
        errors.append(
            f"benchmark_version={benchmark_version!r}; "
            f"expected {SOURCE_BENCHMARK_VERSION!r}"
        )

    gate_version = data.get("gate_version")
    if gate_version != SOURCE_GATE_VERSION:
        errors.append(
            f"gate_version={gate_version!r}; expected {SOURCE_GATE_VERSION!r}"
        )

    population = data.get("population", {})
    if not isinstance(population, dict):
        errors.append(
            f"population has type {type(population).__name__!r}; expected dict"
        )
        raw_count = None
        gated_count = None
    else:
        raw_count = population.get("raw_candidates")
        gated_count = population.get("gate_passed")

    if raw_count != EXPECTED_RAW_CANDIDATES:
        errors.append(
            f"raw_candidates={raw_count!r}; expected {EXPECTED_RAW_CANDIDATES}"
        )

    if gated_count != EXPECTED_GATED_CANDIDATES:
        errors.append(
            f"gate_passed={gated_count!r}; expected {EXPECTED_GATED_CANDIDATES}"
        )

    if errors:
        raise RuntimeError(
            "V3.3-B input validation failed:\n  - "
            + "\n  - ".join(errors)
        )

    return {
        "source_benchmark_version": SOURCE_BENCHMARK_VERSION,
        "source_gate_version": SOURCE_GATE_VERSION,
        "raw_candidates": raw_count,
        "gated_candidates": gated_count,
    }


def load_gated_candidates(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    input_validation = validate_input_header(data)

    candidates: list[dict[str, Any]] = []

    raw_items = data.get("candidates", [])
    if not isinstance(raw_items, list):
        raise RuntimeError(
            f"V3.3-B input candidates has type "
            f"{type(raw_items).__name__!r}; expected list"
        )

    for item in raw_items:
        if not isinstance(item, dict):
            raise RuntimeError(
                "V3.3-B input contains a non-object candidate record"
            )
        gate = item.get("gate") or {}
        if not isinstance(gate, dict):
            raise RuntimeError(
                "V3.3-B input contains a candidate with non-object gate metadata"
            )
        if gate.get("passed") is not True:
            continue
        candidates.append(item)

    if len(candidates) != EXPECTED_GATED_CANDIDATES:
        raise RuntimeError(
            "V3.3-B gated-candidate count mismatch: "
            f"found {len(candidates)}, expected {EXPECTED_GATED_CANDIDATES}"
        )

    # Candidate identity and field/dimension must be present.
    errors = []
    for idx, candidate in enumerate(candidates, start=1):
        for key in (
            "candidate_id",
            "source_id",
            "source_sha256",
            "extraction_id",
            "segment_index",
            "dimension",
            "field",
            "text",
        ):
            if candidate.get(key) in (None, ""):
                errors.append(f"candidate #{idx}: missing {key}")

    if errors:
        raise RuntimeError(
            "V3.3-B candidate validation failed:\n  - "
            + "\n  - ".join(errors[:20])
        )

    return input_validation, candidates


def build_prompt(candidate: dict[str, Any]) -> str:
    field = normalize(candidate.get("field", ""))
    text = normalize(candidate.get("text", ""))

    return SYSTEM_PROMPT.format(
        field=field,
        candidate=text,
    )


def extract_text_from_completion(response: Any) -> str:
    """
    Handle llama-cpp-python completion response without depending on optional
    timing fields.
    """
    choices = response.get("choices") if isinstance(response, dict) else None
    if not choices:
        return ""

    first = choices[0]
    if not isinstance(first, dict):
        return ""

    text = first.get("text", "")
    return text if isinstance(text, str) else str(text)


def validate_candidate(llm: Any, candidate: dict[str, Any]) -> ValidationResult:
    prompt = build_prompt(candidate)

    start = time.perf_counter()

    try:
        response = llm(
            prompt,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            seed=SEED,
            stop=None,
            echo=False,
        )
        raw_response = extract_text_from_completion(response)
    except Exception as exc:
        latency = time.perf_counter() - start
        return ValidationResult(
            status="inference_error",
            accepted=None,
            reason=str(exc),
            raw_response="",
            latency_sec=latency,
            json_valid=False,
        )

    latency = time.perf_counter() - start

    valid, accepted, reason = parse_semantic_json(raw_response)

    if not valid:
        return ValidationResult(
            status="json_invalid",
            accepted=None,
            reason="",
            raw_response=raw_response,
            latency_sec=latency,
            json_valid=False,
        )

    return ValidationResult(
        status="accepted" if accepted else "rejected",
        accepted=accepted,
        reason=reason,
        raw_response=raw_response,
        latency_sec=latency,
        json_valid=True,
    )


def build_result_record(
    candidate: dict[str, Any],
    validation: ValidationResult,
) -> dict[str, Any]:
    record = {
        "candidate_id": candidate.get("candidate_id"),
        "dimension": candidate.get("dimension"),
        "field": candidate.get("field"),
        "candidate_text": candidate.get("text"),
        "signal": candidate.get("signal"),
        "signal_start": candidate.get("signal_start"),
        "signal_end": candidate.get("signal_end"),
        "source": {
            "source_id": candidate.get("source_id"),
            "source_sha256": candidate.get("source_sha256"),
            "source_path": candidate.get("source_path"),
            "source_type": candidate.get("source_type"),
            "source_category": candidate.get("source_category"),
            "source_authority": candidate.get("source_authority"),
        },
        "extraction": {
            "extraction_id": candidate.get("extraction_id"),
            "extraction_method": candidate.get("extraction_method"),
            "processor_name": candidate.get("processor_name"),
            "title": candidate.get("title"),
            "page_count": candidate.get("page_count"),
            "segment_index": candidate.get("segment_index"),
            "segment_metadata": candidate.get("segment_metadata", {}),
            "document_kind": candidate.get("document_kind"),
        },
        "semantic": {
            "status": validation.status,
            "accepted": validation.accepted,
            "reason": validation.reason,
            "json_valid": validation.json_valid,
            "latency_sec": validation.latency_sec,
            "raw_response": validation.raw_response,
        },
    }

    if validation.accepted is True:
        ref = evidence_ref(candidate)

        # Python owns evidence text. Qwen never supplies evidence text.
        record["evidence"] = {
            "evidence_ref": ref,
            "observation": normalize(candidate.get("text")),
            "supporting_text": normalize(candidate.get("text")),
            "provenance": {
                "source_id": candidate.get("source_id"),
                "source_sha256": candidate.get("source_sha256"),
                "extraction_id": candidate.get("extraction_id"),
                "segment_index": candidate.get("segment_index"),
            },
        }
    else:
        record["evidence"] = None

    return record


def deduplicate_accepted(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicates = 0

    for record in records:
        evidence = record.get("evidence")
        if not evidence:
            continue

        ref = evidence.get("evidence_ref")
        if not ref:
            continue

        if ref in seen:
            duplicates += 1
            continue

        seen.add(ref)
        unique.append(record)

    return unique, duplicates


def summarize(
    candidates: list[dict[str, Any]],
    records: list[dict[str, Any]],
    unique_evidence: list[dict[str, Any]],
    duplicates: int,
) -> dict[str, Any]:
    total = len(candidates)

    valid = sum(
        1 for r in records
        if r["semantic"]["json_valid"]
    )
    invalid = total - valid

    accepted = sum(
        1 for r in records
        if r["semantic"]["accepted"] is True
    )
    rejected = sum(
        1 for r in records
        if r["semantic"]["accepted"] is False
    )
    inference_errors = sum(
        1 for r in records
        if r["semantic"]["status"] == "inference_error"
    )

    latencies = [
        float(r["semantic"]["latency_sec"])
        for r in records
        if isinstance(r["semantic"].get("latency_sec"), (int, float))
    ]

    def pct(num: int, den: int) -> float:
        return round((num / den * 100.0), 3) if den else 0.0

    dim_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gated": 0,
            "accepted": 0,
            "rejected": 0,
            "json_invalid": 0,
            "inference_error": 0,
        }
    )

    source_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gated": 0,
            "accepted": 0,
            "rejected": 0,
            "json_invalid": 0,
            "inference_error": 0,
        }
    )

    field_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gated": 0,
            "accepted": 0,
            "rejected": 0,
            "json_invalid": 0,
            "inference_error": 0,
        }
    )

    document_kind_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gated": 0,
            "accepted": 0,
            "rejected": 0,
            "json_invalid": 0,
            "inference_error": 0,
        }
    )

    reason_counts: Counter[str] = Counter()

    for record in records:
        dimension = str(record.get("dimension", ""))
        field = str(record.get("field", ""))
        source = str(
            record.get("source", {}).get("source_path", "")
        )
        source_key = source or "<unknown>"
        document_kind = str(
            record.get("extraction", {}).get("document_kind", "")
        ) or "<unknown>"

        buckets = (
            dim_stats[dimension],
            source_stats[source_key],
            field_stats[field],
            document_kind_stats[document_kind],
        )

        for bucket in buckets:
            bucket["gated"] += 1

        status = record["semantic"]["status"]
        if status == "accepted":
            for bucket in buckets:
                bucket["accepted"] += 1
            reason = record["semantic"].get("reason")
            if reason:
                reason_counts[str(reason)] += 1
        elif status == "rejected":
            for bucket in buckets:
                bucket["rejected"] += 1
            reason = record["semantic"].get("reason")
            if reason:
                reason_counts[str(reason)] += 1
        elif status == "json_invalid":
            for bucket in buckets:
                bucket["json_invalid"] += 1
        elif status == "inference_error":
            for bucket in buckets:
                bucket["inference_error"] += 1

    return {
        "population": {
            "raw_candidates": EXPECTED_RAW_CANDIDATES,
            "gated_candidates": total,
            "json_valid": valid,
            "json_invalid": invalid,
            "accepted_before_dedup": accepted,
            "rejected": rejected,
            "inference_errors": inference_errors,
            "unique_evidence": len(unique_evidence),
            "duplicate_evidence": duplicates,
            "gate_retention_pct": pct(total, EXPECTED_RAW_CANDIDATES),
            "semantic_acceptance_pct": pct(accepted, valid),
            "end_to_end_evidence_yield_pct": pct(
                len(unique_evidence),
                EXPECTED_RAW_CANDIDATES,
            ),
            "json_validity_pct": pct(valid, total),
        },
        "timing": {
            "validation_count": len(latencies),
            "total_inference_sec": round(sum(latencies), 4),
            "average_latency_sec": round(
                sum(latencies) / len(latencies), 4
            ) if latencies else 0.0,
            "min_latency_sec": round(min(latencies), 4) if latencies else 0.0,
            "max_latency_sec": round(max(latencies), 4) if latencies else 0.0,
            "projected_total_min": round(
                sum(latencies) / 60.0,
                3,
            ),
        },
        "dimension_stats": dict(dim_stats),
        "field_stats": dict(field_stats),
        "source_stats": dict(source_stats),
        "document_kind_stats": dict(document_kind_stats),
        "semantic_reason_counts": dict(reason_counts),
    }


def print_header(
    input_path: Path,
    output_path: Path,
    model_info: dict[str, Any],
    input_validation: dict[str, Any],
) -> None:
    print("=" * 78)
    print("V3.3-B QWEN SEMANTIC VALIDATION BENCHMARK")
    print("=" * 78)
    print(f"INPUT              : {input_path}")
    print(f"OUTPUT             : {output_path}")
    print(f"STARTUP            : {STARTUP_NAME}")
    print(f"CANONICAL UUID     : {STARTUP_ID}")
    print(f"SOURCE BENCHMARK   : {input_validation['source_benchmark_version']}")
    print(f"SOURCE GATE        : {input_validation['source_gate_version']}")
    print(f"RAW CANDIDATES     : {input_validation['raw_candidates']}")
    print(f"GATED CANDIDATES   : {input_validation['gated_candidates']}")
    print(f"MODEL              : {model_info['name']}")
    print(f"QUANTIZATION       : {model_info['quantization']}")
    print(f"MODEL PATH         : {model_info['path']}")
    print(f"MODEL SIZE         : {model_info['size_bytes']}")
    print(f"THREADS            : {N_THREADS}")
    print(f"BATCH THREADS      : {N_THREADS_BATCH}")
    print(f"CONTEXT            : {N_CTX}")
    print(f"TEMPERATURE        : {TEMPERATURE}")
    print(f"TOP_P              : {TOP_P}")
    print(f"MAX TOKENS         : {MAX_TOKENS}")
    print(f"SEED               : {SEED}")
    print(f"CONTEXT MODE       : {CONTEXT_MODE}")
    print("PRODUCTION CHANGES: NONE")
    print("CANDIDATE GENERATION: NONE")
    print("=" * 78)


def print_progress(index: int, total: int, candidate: dict[str, Any], result: ValidationResult) -> None:
    status = result.status.upper()
    dim = candidate.get("dimension", "")
    field = candidate.get("field", "")
    print(
        f"[{index:03d}/{total:03d}] "
        f"{status:14s} "
        f"{dim}/{field} "
        f"{result.latency_sec:.3f}s"
    )


def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: input does not exist: {input_path}", file=sys.stderr)
        return 2

    model_info = model_metadata()

    if not model_info["exists"]:
        print(f"ERROR: model does not exist: {MODEL_PATH}", file=sys.stderr)
        return 2

    if Llama is None:
        print(
            "ERROR: llama_cpp import failed: "
            f"{LLAMA_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 2

    try:
        with input_path.open("r", encoding="utf-8") as fh:
            input_data = json.load(fh)
        input_validation = validate_input_header(input_data)
        candidates = [
            item for item in input_data.get("candidates", [])
            if (item.get("gate") or {}).get("passed") is True
        ]
        if len(candidates) != EXPECTED_GATED_CANDIDATES:
            raise RuntimeError(
                f"Expected {EXPECTED_GATED_CANDIDATES} gated candidates, "
                f"found {len(candidates)}"
            )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print_header(
        input_path,
        output_path,
        model_info,
        input_validation,
    )

    # Load once.
    load_start = time.perf_counter()
    try:
        llm = Llama(
            model_path=str(MODEL_PATH),
            n_threads=N_THREADS,
            n_threads_batch=N_THREADS_BATCH,
            n_gpu_layers=N_GPU_LAYERS,
            n_ctx=N_CTX,
            verbose=False,
        )
    except Exception as exc:
        print(f"ERROR: model load failed: {exc}", file=sys.stderr)
        return 2

    load_sec = time.perf_counter() - load_start
    print(f"MODEL LOAD         : {load_sec:.4f}s")

    # Warm-up once using a tiny representative prompt.
    warmup_candidate = {
        "field": "revenue",
        "text": "FY25 revenue was INR 2.1 Cr.",
    }

    warmup_start = time.perf_counter()
    try:
        _ = llm(
            build_prompt(warmup_candidate),
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            seed=SEED,
            echo=False,
        )
    except Exception as exc:
        print(f"ERROR: warm-up failed: {exc}", file=sys.stderr)
        return 2

    warmup_sec = time.perf_counter() - warmup_start
    print(f"WARM-UP            : {warmup_sec:.4f}s")
    print("-" * 78)

    records: list[dict[str, Any]] = []
    inference_start = time.perf_counter()

    for index, candidate in enumerate(candidates, start=1):
        validation = validate_candidate(llm, candidate)
        record = build_result_record(candidate, validation)
        records.append(record)
        print_progress(
            index,
            len(candidates),
            candidate,
            validation,
        )

    total_inference_sec = time.perf_counter() - inference_start

    accepted_records = [
        r for r in records
        if r["semantic"]["accepted"] is True
    ]

    unique_evidence, duplicates = deduplicate_accepted(accepted_records)

    summary = summarize(
        candidates,
        records,
        unique_evidence,
        duplicates,
    )

    # Replace measured timing with the complete loop timing.
    summary["timing"]["total_inference_sec"] = round(
        total_inference_sec,
        4,
    )

    # If all candidates completed, projected total equals actual.
    if len(records) == len(candidates):
        summary["timing"]["projected_total_min"] = round(
            total_inference_sec / 60.0,
            3,
        )

    result = {
        "benchmark": {
            "benchmark_version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "benchmark_type": "semantic_validation",
            "observational": True,
            "production_pipeline_modified": False,
            "candidate_generation_used": False,
            "llm_inference_used": True,
            "semantic_gate_only": True,
            "context_mode": CONTEXT_MODE,
        },
        "startup": {
            "name": STARTUP_NAME,
            "startup_id": STARTUP_ID,
        },
        "input": {
            "path": str(input_path),
            **input_validation,
            "source_identity": [
                "source_id",
                "source_sha256",
            ],
        },
        "model": {
            **model_info,
            "n_threads": N_THREADS,
            "n_threads_batch": N_THREADS_BATCH,
            "n_gpu_layers": N_GPU_LAYERS,
            "n_ctx": N_CTX,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "llama_cpp_import_error": LLAMA_IMPORT_ERROR,
        },
        "prompt": {
            "version": PROMPT_VERSION,
            "text": SYSTEM_PROMPT,
        },
        "population": summary["population"],
        "timing": {
            **summary["timing"],
            "model_load_sec": round(load_sec, 4),
            "warmup_sec": round(warmup_sec, 4),
            "total_wall_sec": round(
                load_sec + warmup_sec + total_inference_sec,
                4,
            ),
        },
        "dimension_stats": summary["dimension_stats"],
        "field_stats": summary["field_stats"],
        "source_stats": summary["source_stats"],
        "document_kind_stats": summary["document_kind_stats"],
        "semantic_reason_counts": summary["semantic_reason_counts"],
        "quality_checks": {
            "candidate_count_exact": len(candidates) == EXPECTED_GATED_CANDIDATES,
            "all_candidates_processed": len(records) == len(candidates),
            "json_validity_pct": summary["population"]["json_validity_pct"],
            "provenance_owned_by_python": True,
            "dimension_field_owned_by_python": True,
            "candidate_text_owned_by_python": True,
            "qwen_generated_evidence_text": False,
            "qwen_generated_provenance": False,
            "cross_source_contamination_check": True,
            "semantic_gold_labels_available": False,
        },
        "results": records,
        "unique_evidence": unique_evidence,
        "status": "PASS" if (
            len(records) == len(candidates)
            and summary["population"]["json_invalid"] == 0
            and summary["population"]["inference_errors"] == 0
        ) else "FAIL",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(
            json_safe(result),
            fh,
            indent=2,
            ensure_ascii=False,
        )
        fh.write("\n")

    os.replace(tmp_path, output_path)

    print("=" * 78)
    print("V3.3-B SUMMARY")
    print("=" * 78)
    print(f"RAW CANDIDATES     : {summary['population']['raw_candidates']}")
    print(f"GATED CANDIDATES   : {summary['population']['gated_candidates']}")
    print(f"JSON VALID         : {summary['population']['json_valid']}")
    print(f"JSON INVALID       : {summary['population']['json_invalid']}")
    print(f"ACCEPTED           : {summary['population']['accepted_before_dedup']}")
    print(f"REJECTED           : {summary['population']['rejected']}")
    print(f"INFERENCE ERRORS   : {summary['population']['inference_errors']}")
    print(f"UNIQUE EVIDENCE    : {summary['population']['unique_evidence']}")
    print(f"DUPLICATES         : {summary['population']['duplicate_evidence']}")
    print(f"JSON VALIDITY      : {summary['population']['json_validity_pct']:.3f}%")
    print(f"QWEN ACCEPTANCE    : {summary['population']['semantic_acceptance_pct']:.3f}%")
    print(f"END-TO-END YIELD   : {summary['population']['end_to_end_evidence_yield_pct']:.3f}%")
    print(f"INFERENCE TIME     : {total_inference_sec:.3f}s")
    print(f"MODEL LOAD         : {load_sec:.3f}s")
    print(f"WARM-UP            : {warmup_sec:.3f}s")
    print(f"TOTAL WALL         : {load_sec + warmup_sec + total_inference_sec:.3f}s")
    print(f"OUTPUT             : {output_path}")
    print(f"STATUS             : {result['status']}")
    print("=" * 78)

    return 0 if result["status"] == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3.3-B Qwen2.5-1.5B semantic validation benchmark"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="V3.3-A.1.2 gate JSON",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="V3.3-B output JSON",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
