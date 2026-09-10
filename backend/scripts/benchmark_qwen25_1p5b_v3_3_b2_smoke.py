#!/usr/bin/env python3
"""
V3.3-B.2 SMOKE — Qwen2.5-1.5B Semantic Validation Contract Check
================================================================

Purpose
-------
Validate the LLM output contract on 10 representative candidates before
running the full 251-candidate V3.3-B.2 benchmark.

This is a CONTRACT SMOKE ONLY.

Architecture
------------
V3.3-A.1.2 deterministic candidate quality gate
        |
        v
251 gated candidates
        |
        v
10 deterministic smoke candidates
        |
        v
Qwen2.5-1.5B semantic validation
        |
        +--> accepted
        +--> rejected
        +--> JSON invalid
        +--> inference error

Important
---------
- The 251-candidate V3.3-A.1.2 population is immutable input.
- No candidate generation is performed.
- No production pipeline is modified.
- Qwen does NOT generate evidence, provenance, dimensions, fields, or
  supporting text.
- Python owns provenance and evidence construction.
- No semantic gold labels are assumed.
- The smoke gate is primarily intended to validate the output contract.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from llama_cpp import Llama, LlamaGrammar
except Exception as exc:
    Llama = None
    LlamaGrammar = None
    LLAMA_IMPORT_ERROR = str(exc)
else:
    LLAMA_IMPORT_ERROR = ""


# ---------------------------------------------------------------------------
# Frozen benchmark configuration
# ---------------------------------------------------------------------------

BENCHMARK_VERSION = "V3.3-B.2-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v3-binary"

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
    "benchmark_qwen25_1p5b_v3_3_b2_smoke.json"
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
MAX_TOKENS = 4

EXPECTED_RAW_CANDIDATES = 1167
EXPECTED_GATED_CANDIDATES = 251
SMOKE_COUNT = 10

CONTEXT_MODE = "candidate_only"

BINARY_GRAMMAR_TEXT = 'root ::= "A" | "R"'


SYSTEM_PROMPT = """You are validating investment evidence.

FIELD:
{field}

CANDIDATE:
{candidate}

QUESTION:
Does the candidate explicitly support the specified field?

Rules:
- Accept only if the candidate directly supports the field.
- Do not infer missing facts.
- A keyword alone is insufficient.
- Legal boilerplate is not evidence unless it directly supports the field.
- Accounting labels, formulas, and generic statements are not evidence unless they explicitly support the field.
- Reject unrelated or incidental references.
- Reject when the candidate does not contain enough information to support the field.

Output contract:
- Return exactly one character.
- Output A if the candidate explicitly supports the field.
- Output R if the candidate does not explicitly support the field.
- Do not output any other character, word, explanation, punctuation, or formatting.
- Do not repeat the question or candidate.
"""


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
    binary_valid: bool
    invalid_reason: str


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


def parse_semantic_binary(text: str) -> tuple[bool, bool | None, str, str]:
    """Strict one-character binary semantic-output parser.

    Returns: (valid, accepted, reason, invalid_reason)
    """
    cleaned = text.strip()

    if not cleaned:
        return False, None, "", "empty"

    if cleaned == "A":
        return True, True, "accepted_by_binary_semantic_gate", ""

    if cleaned == "R":
        return True, False, "rejected_by_binary_semantic_gate", ""

    if cleaned[0:1] in {"A", "R"}:
        return False, None, "", "extra_output"

    return False, None, "", "invalid_label"

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


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_input_header(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    benchmark_version = data.get("benchmark_version")
    if benchmark_version != SOURCE_BENCHMARK_VERSION:
        errors.append(
            f"benchmark_version={benchmark_version!r}; "
            f"expected {SOURCE_BENCHMARK_VERSION!r}"
        )

    gate_version = data.get("gate_version")
    if gate_version != SOURCE_GATE_VERSION:
        errors.append(
            f"gate_version={gate_version!r}; "
            f"expected {SOURCE_GATE_VERSION!r}"
        )

    population = data.get("population", {})
    if not isinstance(population, dict):
        errors.append(
            f"population has type {type(population).__name__!r}; "
            f"expected dict"
        )
        raw_count = None
        gated_count = None
    else:
        raw_count = population.get("raw_candidates")
        gated_count = population.get("gate_passed")

    if raw_count != EXPECTED_RAW_CANDIDATES:
        errors.append(
            f"raw_candidates={raw_count!r}; "
            f"expected {EXPECTED_RAW_CANDIDATES}"
        )

    if gated_count != EXPECTED_GATED_CANDIDATES:
        errors.append(
            f"gate_passed={gated_count!r}; "
            f"expected {EXPECTED_GATED_CANDIDATES}"
        )

    if errors:
        raise RuntimeError(
            "V3.3-B.2 smoke input validation failed:\n  - "
            + "\n  - ".join(errors)
        )

    return {
        "source_benchmark_version": SOURCE_BENCHMARK_VERSION,
        "source_gate_version": SOURCE_GATE_VERSION,
        "raw_candidates": raw_count,
        "gated_candidates": gated_count,
    }


def load_gated_candidates(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    input_validation = validate_input_header(data)

    raw_items = data.get("candidates", [])
    if not isinstance(raw_items, list):
        raise RuntimeError(
            f"input candidates has type "
            f"{type(raw_items).__name__!r}; expected list"
        )

    candidates: list[dict[str, Any]] = []

    for item in raw_items:
        if not isinstance(item, dict):
            raise RuntimeError("input contains a non-object candidate record")

        gate = item.get("gate") or {}
        if not isinstance(gate, dict):
            raise RuntimeError(
                "input contains a candidate with non-object gate metadata"
            )

        if gate.get("passed") is not True:
            continue

        candidates.append(item)

    if len(candidates) != EXPECTED_GATED_CANDIDATES:
        raise RuntimeError(
            "gated-candidate count mismatch: "
            f"found {len(candidates)}, expected {EXPECTED_GATED_CANDIDATES}"
        )

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
            "candidate validation failed:\n  - "
            + "\n  - ".join(errors[:20])
        )

    return input_validation, candidates


# ---------------------------------------------------------------------------
# Deterministic smoke selection
# ---------------------------------------------------------------------------

def smoke_selection_key(candidate: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(candidate.get("dimension", "")),
        str(candidate.get("field", "")),
        str(candidate.get("source_path", "")),
        str(candidate.get("candidate_id", "")),
    )


def select_smoke_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Select exactly 10 deterministic candidates.

    Selection strategy:
      1. Prefer distinct dimensions.
      2. Then prefer distinct fields.
      3. Then fill remaining slots deterministically.

    This is intentionally NOT a semantic gold-label selection.
    """

    ordered = sorted(candidates, key=smoke_selection_key)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    dimensions: set[str] = set()
    fields: set[str] = set()

    # Pass 1: maximize dimension diversity.
    for candidate in ordered:
        cid = str(candidate.get("candidate_id"))
        dim = str(candidate.get("dimension", ""))
        if cid in selected_ids:
            continue
        if dim and dim not in dimensions:
            selected.append(candidate)
            selected_ids.add(cid)
            dimensions.add(dim)
            fields.add(str(candidate.get("field", "")))
        if len(selected) >= SMOKE_COUNT:
            return selected

    # Pass 2: maximize field diversity.
    for candidate in ordered:
        cid = str(candidate.get("candidate_id"))
        field = str(candidate.get("field", ""))
        if cid in selected_ids:
            continue
        if field and field not in fields:
            selected.append(candidate)
            selected_ids.add(cid)
            fields.add(field)
        if len(selected) >= SMOKE_COUNT:
            return selected

    # Pass 3: deterministic fill.
    for candidate in ordered:
        cid = str(candidate.get("candidate_id"))
        if cid in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(cid)
        if len(selected) >= SMOKE_COUNT:
            return selected

    if len(selected) != SMOKE_COUNT:
        raise RuntimeError(
            f"Unable to select {SMOKE_COUNT} smoke candidates; "
            f"only {len(selected)} available"
        )

    return selected


# ---------------------------------------------------------------------------
# Prompt / inference
# ---------------------------------------------------------------------------

def build_binary_grammar() -> Any:
    if LlamaGrammar is None:
        raise RuntimeError("llama_cpp.LlamaGrammar is unavailable")
    return LlamaGrammar.from_string(BINARY_GRAMMAR_TEXT)


def build_prompt(candidate: dict[str, Any]) -> str:
    return SYSTEM_PROMPT.format(
        field=normalize(candidate.get("field", "")),
        candidate=normalize(candidate.get("text", "")),
    )


def extract_text_from_completion(response: Any) -> str:
    choices = response.get("choices") if isinstance(response, dict) else None

    if not choices:
        return ""

    first = choices[0]

    if not isinstance(first, dict):
        return ""

    text = first.get("text", "")
    return text if isinstance(text, str) else str(text)


def validate_candidate(
    llm: Any,
    grammar: Any,
    candidate: dict[str, Any],
) -> ValidationResult:
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
            grammar=binary_grammar,
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
            binary_valid=False,
            invalid_reason="",
        )

    latency = time.perf_counter() - start

    valid, accepted, reason, invalid_reason = parse_semantic_binary(
        raw_response
    )

    if not valid:
        return ValidationResult(
            status="binary_invalid",
            accepted=None,
            reason="",
            raw_response=raw_response,
            latency_sec=latency,
            binary_valid=False,
            invalid_reason=invalid_reason,
        )

    return ValidationResult(
        status="accepted" if accepted else "rejected",
        accepted=accepted,
        reason=reason,
        raw_response=raw_response,
        latency_sec=latency,
        binary_valid=True,
        invalid_reason="",
    )


# ---------------------------------------------------------------------------
# Result construction
# ---------------------------------------------------------------------------

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
            "binary_valid": validation.binary_valid,
            "invalid_reason": validation.invalid_reason,
            "latency_sec": validation.latency_sec,
            "raw_response": validation.raw_response,
        },
    }

    if validation.accepted is True:
        ref = evidence_ref(candidate)

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


# ---------------------------------------------------------------------------
# Summary / diagnostics
# ---------------------------------------------------------------------------

def summarize(
    candidates: list[dict[str, Any]],
    records: list[dict[str, Any]],
    unique_evidence: list[dict[str, Any]],
    duplicates: int,
) -> dict[str, Any]:

    total = len(candidates)

    valid = sum(
        1
        for r in records
        if r["semantic"]["binary_valid"]
    )

    invalid = total - valid

    accepted = sum(
        1
        for r in records
        if r["semantic"]["accepted"] is True
    )

    rejected = sum(
        1
        for r in records
        if r["semantic"]["accepted"] is False
    )

    inference_errors = sum(
        1
        for r in records
        if r["semantic"]["status"] == "inference_error"
    )

    latencies = [
        float(r["semantic"]["latency_sec"])
        for r in records
        if isinstance(r["semantic"].get("latency_sec"), (int, float))
    ]

    invalid_reason_counts: Counter[str] = Counter(
        str(r["semantic"].get("invalid_reason"))
        for r in records
        if r["semantic"]["status"] == "binary_invalid"
        and r["semantic"].get("invalid_reason")
    )

    reason_counts: Counter[str] = Counter(
        str(r["semantic"].get("reason"))
        for r in records
        if r["semantic"].get("reason")
    )

    dimension_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "gated": 0,
            "accepted": 0,
            "rejected": 0,
            "binary_invalid": 0,
            "inference_error": 0,
        }
    )

    for record in records:
        dimension = str(record.get("dimension", ""))

        bucket = dimension_stats[dimension]
        bucket["gated"] += 1

        status = record["semantic"]["status"]

        if status == "accepted":
            bucket["accepted"] += 1
        elif status == "rejected":
            bucket["rejected"] += 1
        elif status == "binary_invalid":
            bucket["binary_invalid"] += 1
        elif status == "inference_error":
            bucket["inference_error"] += 1

    def pct(num: int, den: int) -> float:
        return round((num / den * 100.0), 3) if den else 0.0

    return {
        "population": {
            "source_raw_candidates": EXPECTED_RAW_CANDIDATES,
            "source_gated_candidates": EXPECTED_GATED_CANDIDATES,
            "smoke_candidates": total,
            "binary_valid": valid,
            "binary_invalid": invalid,
            "accepted": accepted,
            "rejected": rejected,
            "inference_errors": inference_errors,
            "unique_evidence": len(unique_evidence),
            "duplicate_evidence": duplicates,
            "binary_validity_pct": pct(valid, total),
            "semantic_acceptance_pct": pct(accepted, valid),
        },
        "timing": {
            "validation_count": len(latencies),
            "total_inference_sec": round(sum(latencies), 4),
            "average_latency_sec": round(
                sum(latencies) / len(latencies), 4
            ) if latencies else 0.0,
            "min_latency_sec": round(min(latencies), 4)
            if latencies else 0.0,
            "max_latency_sec": round(max(latencies), 4)
            if latencies else 0.0,
            "projected_251_min": round(
                (sum(latencies) / len(latencies) * EXPECTED_GATED_CANDIDATES)
                / 60.0,
                3,
            ) if latencies else 0.0,
        },
        "invalid_reason_counts": dict(invalid_reason_counts),
        "semantic_reason_counts": dict(reason_counts),
        "dimension_stats": dict(dimension_stats),
    }


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_header(
    input_path: Path,
    output_path: Path,
    model_info: dict[str, Any],
    input_validation: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> None:

    print("=" * 78)
    print("V3.3-B.2 SMOKE — QWEN BINARY SEMANTIC CLASSIFICATION")
    print("=" * 78)
    print(f"INPUT              : {input_path}")
    print(f"OUTPUT             : {output_path}")
    print(f"STARTUP            : {STARTUP_NAME}")
    print(f"CANONICAL UUID     : {STARTUP_ID}")
    print(f"SOURCE BENCHMARK   : {input_validation['source_benchmark_version']}")
    print(f"SOURCE GATE        : {input_validation['source_gate_version']}")
    print(f"RAW CANDIDATES     : {input_validation['raw_candidates']}")
    print(f"GATED CANDIDATES   : {input_validation['gated_candidates']}")
    print(f"SMOKE CANDIDATES   : {len(candidates)}")
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
    print(f"OUTPUT GRAMMAR     : {BINARY_GRAMMAR_TEXT}")
    print(f"SEED               : {SEED}")
    print(f"CONTEXT MODE       : {CONTEXT_MODE}")
    print("PRODUCTION CHANGES: NONE")
    print("CANDIDATE GENERATION: NONE")
    print("=" * 78)


def print_progress(
    index: int,
    total: int,
    candidate: dict[str, Any],
    result: ValidationResult,
) -> None:

    status = result.status.upper()
    dim = candidate.get("dimension", "")
    field = candidate.get("field", "")

    extra = (
        f" [{result.invalid_reason}]"
        if result.invalid_reason
        else ""
    )

    print(
        f"[{index:02d}/{total:02d}] "
        f"{status:14s} "
        f"{dim}/{field} "
        f"{result.latency_sec:.3f}s"
        f"{extra}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(
            f"ERROR: input does not exist: {input_path}",
            file=sys.stderr,
        )
        return 2

    model_info = model_metadata()

    if not model_info["exists"]:
        print(
            f"ERROR: model does not exist: {MODEL_PATH}",
            file=sys.stderr,
        )
        return 2

    if Llama is None:
        print(
            "ERROR: llama_cpp import failed: "
            f"{LLAMA_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 2

    try:
        input_validation, all_candidates = load_gated_candidates(
            input_path
        )
        candidates = select_smoke_candidates(all_candidates)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print_header(
        input_path,
        output_path,
        model_info,
        input_validation,
        candidates,
    )

    print("-" * 78)
    print("SMOKE SELECTION")
    print("-" * 78)

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"[{index:02d}] "
            f"{candidate.get('dimension')}/"
            f"{candidate.get('field')} "
            f"| {candidate.get('source_path')}"
        )

    print("-" * 78)

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

    try:
        binary_grammar = build_binary_grammar()
    except Exception as exc:
        print(f"ERROR: binary grammar initialization failed: {exc}", file=sys.stderr)
        return 2

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
            stop=None,
            echo=False,
            grammar=binary_grammar,
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
        validation = validate_candidate(llm, binary_grammar, candidate)
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
        r
        for r in records
        if r["semantic"]["accepted"] is True
    ]

    unique_evidence, duplicates = deduplicate_accepted(
        accepted_records
    )

    summary = summarize(
        candidates,
        records,
        unique_evidence,
        duplicates,
    )

    summary["timing"]["total_inference_sec"] = round(
        total_inference_sec,
        4,
    )

    if len(records) == len(candidates):
        summary["timing"]["projected_251_min"] = round(
            (
                total_inference_sec / len(records)
                * EXPECTED_GATED_CANDIDATES
            ) / 60.0,
            3,
        )

    contract_pass = (
        len(records) == SMOKE_COUNT
        and summary["population"]["binary_invalid"] == 0
        and summary["population"]["inference_errors"] == 0
    )

    result = {
        "benchmark": {
            "benchmark_version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "benchmark_type": "semantic_validation_contract_smoke",
            "observational": True,
            "production_pipeline_modified": False,
            "candidate_generation_used": False,
            "llm_inference_used": True,
            "semantic_gate_only": True,
        "classification_mode": "binary_A_R",
            "grammar_constrained": True,
            "context_mode": CONTEXT_MODE,
            "purpose": "validate_output_contract_before_full_251_run",
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
        "smoke_selection": [
            {
                "index": index,
                "candidate_id": candidate.get("candidate_id"),
                "dimension": candidate.get("dimension"),
                "field": candidate.get("field"),
                "source_path": candidate.get("source_path"),
            }
            for index, candidate in enumerate(candidates, start=1)
        ],
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
        "invalid_reason_counts": summary["invalid_reason_counts"],
        "semantic_reason_counts": summary["semantic_reason_counts"],
        "dimension_stats": summary["dimension_stats"],
        "quality_checks": {
            "candidate_count_exact": len(candidates) == SMOKE_COUNT,
            "all_candidates_processed": len(records) == len(candidates),
            "binary_validity_pct": summary["population"]["binary_validity_pct"],
            "contract_gate_pass": contract_pass,
            "provenance_owned_by_python": True,
            "dimension_field_owned_by_python": True,
            "candidate_text_owned_by_python": True,
            "qwen_generated_evidence_text": False,
            "qwen_generated_provenance": False,
            "semantic_gold_labels_available": False,
        },
        "results": records,
        "unique_evidence": unique_evidence,
        "status": "PASS" if contract_pass else "FAIL",
        "full_benchmark_authorized": contract_pass,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

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
    print("V3.3-B.2 SMOKE SUMMARY")
    print("=" * 78)
    print(f"SMOKE CANDIDATES   : {summary['population']['smoke_candidates']}")
    print(f"BINARY VALID         : {summary['population']['binary_valid']}")
    print(f"BINARY INVALID       : {summary['population']['binary_invalid']}")
    print(f"ACCEPTED           : {summary['population']['accepted']}")
    print(f"REJECTED           : {summary['population']['rejected']}")
    print(f"INFERENCE ERRORS   : {summary['population']['inference_errors']}")
    print(f"BINARY VALIDITY      : {summary['population']['binary_validity_pct']:.3f}%")
    print(f"INFERENCE TIME     : {total_inference_sec:.3f}s")
    print(f"PROJECTED 251 MIN  : {summary['timing']['projected_251_min']:.3f}")
    print(f"OUTPUT             : {output_path}")
    print(f"CONTRACT PASS      : {contract_pass}")
    print(f"STATUS             : {result['status']}")
    print("=" * 78)

    if summary["invalid_reason_counts"]:
        print("INVALID RESPONSE REASONS")
        for reason, count in sorted(
            summary["invalid_reason_counts"].items()
        ):
            print(f"  {reason:24s}: {count}")

    return 0 if contract_pass else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "V3.3-B.2 10-candidate Qwen semantic output-contract smoke"
        )
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="V3.3-A.1.2 gate JSON",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="V3.3-B.2 smoke output JSON",
    )

    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
