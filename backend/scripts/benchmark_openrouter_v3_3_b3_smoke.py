#!/usr/bin/env python3
"""
V3.3-B.3 OpenRouter semantic-boundary smoke benchmark.

Purpose
-------
Evaluate an external OpenRouter model on the frozen 16-case B.2.2 smoke
population. This benchmark does NOT generate candidates and does NOT modify
the production evidence pipeline.

Frozen input schema
-------------------
The B.2.2 artifact contains:
  smoke_selection[] -> candidate_id
  results[]         -> candidate_text, smoke_expected_label, provenance, ...

The two arrays are joined by candidate_id.

Pass gates
----------
  * 16/16 structured responses valid
  * overall semantic accuracy >= 80%
  * negative/trap accuracy >= 87.5%
  * no production pipeline modification

Exit codes
----------
  0 = smoke PASS
  1 = semantic/contract smoke FAIL
  2 = configuration/input error

Environment
-----------
  OPENROUTER_API_KEY   required
  OPENROUTER_MODEL     default: openai/gpt-oss-20b:free
  INPUT_JSON            default: /opt/investment-os/generated/restomart/
                         benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json
  OUTPUT_JSON           optional; otherwise generated next to INPUT_JSON
  OPENROUTER_CONCURRENCY default: 2
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BENCHMARK_VERSION = "V3.3-B.3-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v5-openrouter"
SOURCE_BENCHMARK_VERSION = "V3.3-B.2.2-SMOKE"
SOURCE_GATE_VERSION = "candidate-quality-gate-v1.3"

DEFAULT_INPUT = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json"
)

#MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
CONCURRENCY = int(os.getenv("OPENROUTER_CONCURRENCY", "2"))
TIMEOUT_SEC = int(os.getenv("OPENROUTER_TIMEOUT_SEC", "120"))
MAX_RETRIES = int(os.getenv("OPENROUTER_MAX_RETRIES", "3"))
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 128

EXPECTED_CASES = 16
EXPECTED_ACCEPTED = 8
EXPECTED_REJECTED = 8
MIN_ACCURACY_PCT = 80.0
MIN_NEGATIVE_ACCURACY_PCT = 87.5

FIELD_DEFINITIONS = {
    "cash_burn": (
        "Explicit evidence of company cash consumption, cash burn rate, "
        "cash depletion, or cash runway over a stated period."
    ),
    "customers": (
        "Explicit evidence of actual customers, customer count, named "
        "customers, customer relationships, customer deployments, or "
        "customer acquisition. A target customer segment description alone "
        "is not sufficient."
    ),
    "adoption_usage": (
        "Explicit evidence of actual product/service usage or adoption, "
        "such as active users, orders, transactions, deployments, usage "
        "volume, or similar observed usage."
    ),
    "board_rights": (
        "Explicit evidence of a shareholder/investor right to appoint, "
        "nominate, designate, or otherwise have board representation. "
        "Incidental references to the Board or generic board powers are "
        "not sufficient."
    ),
    "market_size": (
        "Explicit evidence of TAM, SAM, SOM, addressable market size, or "
        "a quantified market opportunity."
    ),
    "instrument": (
        "Explicit identification of a financing/security instrument, such "
        "as CCPS, equity shares, debt, SAFE, or another stated instrument."
    ),
    "valuation": (
        "Explicit company valuation, including pre-money, post-money, "
        "enterprise valuation, or another clearly stated valuation."
    ),
    "gmv": (
        "Explicit Gross Merchandise Value (GMV), including a stated GMV "
        "amount, period, or growth."
    ),
    "growth": (
        "Explicit historical or projected growth rate, growth trajectory, "
        "or comparable direct growth statement for the company."
    ),
    "founder_background": (
        "Explicit founder identity, experience, education, prior company, "
        "career history, or relevant professional background."
    ),
    "revenue": (
        "Explicit actual or projected company revenue, including a stated "
        "revenue amount, period, or revenue growth where the revenue itself "
        "is directly established."
    ),
    "generic": (
        "Direct substantive evidence for the requested investment-analysis "
        "field."
    ),
}


def build_prompt(field: str, candidate_text: str) -> list[dict[str, str]]:
    definition = FIELD_DEFINITIONS.get(field, FIELD_DEFINITIONS["generic"])

    system = """You are a strict investment evidence classifier.

Determine whether the candidate text provides DIRECT, EXPLICIT evidence
for the requested investment-analysis field.

Rules:
1. Accept only if the text directly supports the requested field.
2. Do not infer information that is not stated.
3. A keyword or phrase alone is insufficient.
4. Reject incidental mentions of the field.
5. Reject legal, administrative, accounting, or boilerplate text unless it
   directly provides evidence for the requested field.
6. Reject formulas, ratios, headings, labels, or related metrics when they
   do not directly establish the requested field.
7. Related business information is not necessarily evidence for the field.
8. Be conservative: when uncertain, reject.

Return only the requested structured JSON object."""
    user = (
        f"Requested field: {field}\n\n"
        f"Field definition: {definition}\n\n"
        f"Candidate text:\n{candidate_text}\n\n"
        "Classify whether this candidate is direct evidence for the field."
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def load_cases(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data.get("smoke_selection"), list):
        raise ValueError("B.2.2 artifact has no smoke_selection list.")
    if not isinstance(data.get("results"), list):
        raise ValueError("B.2.2 artifact has no results list.")

    selection = data["smoke_selection"]
    if len(selection) != EXPECTED_CASES:
        raise ValueError(
            f"Expected exactly {EXPECTED_CASES} smoke selections; "
            f"found {len(selection)}."
        )

    by_id: dict[str, dict[str, Any]] = {}
    for result in data["results"]:
        cid = result.get("candidate_id")
        if cid:
            by_id[cid] = result

    cases: list[dict[str, Any]] = []
    for selected in selection:
        cid = selected.get("candidate_id")
        if not cid:
            raise ValueError("Smoke selection contains no candidate_id.")
        result = by_id.get(cid)
        if result is None:
            raise ValueError(f"No results record for candidate_id={cid}.")

        required = ("candidate_id", "field", "candidate_text",
                    "smoke_expected_label", "smoke_challenge_type")
        missing = [k for k in required if k not in result]
        if missing:
            raise ValueError(
                f"Candidate {cid} missing fields: {', '.join(missing)}"
            )

        expected = str(result["smoke_expected_label"]).upper()
        if expected not in {"A", "R"}:
            raise ValueError(
                f"Candidate {cid} has invalid expected label {expected!r}."
            )

        cases.append({
            "candidate_id": cid,
            "dimension": result["dimension"],
            "field": result["field"],
            "candidate_text": result["candidate_text"],
            "expected_label": expected,
            "challenge_type": result["smoke_challenge_type"],
            "source": result.get("source", {}),
            "extraction": result.get("extraction", {}),
        })

    labels = [c["expected_label"] for c in cases]
    if labels.count("A") != EXPECTED_ACCEPTED:
        raise ValueError(
            f"Expected {EXPECTED_ACCEPTED} accepted smoke cases; "
            f"found {labels.count('A')}."
        )
    if labels.count("R") != EXPECTED_REJECTED:
        raise ValueError(
            f"Expected {EXPECTED_REJECTED} rejected smoke cases; "
            f"found {labels.count('R')}."
        )

    return data, cases


def request_openrouter(case: dict[str, Any], api_key: str) -> dict[str, Any]:
    body = {
        "model": MODEL,
        "messages": build_prompt(case["field"], case["candidate_text"]),
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "candidate_semantic_validation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "accepted": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": ["accepted", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "provider": {
            "require_parameters": True,
        },
    }

    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Investment OS V3.3-B.3 Smoke Benchmark",
    }

    last_error = ""
    started = time.perf_counter()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                API_URL, data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8")
                status = resp.status

            elapsed = time.perf_counter() - started
            data = json.loads(raw)

            choices = data.get("choices")
            if not choices:
                raise ValueError("OpenRouter response has no choices.")

            content = choices[0].get("message", {}).get("content", "")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("OpenRouter response has empty content.")

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": content,
                    "latency_sec": elapsed,
                    "error": f"response_not_json: {exc}",
                    "http_status": status,
                    "usage": data.get("usage", {}),
                }

            if (
                not isinstance(parsed, dict)
                or set(parsed.keys()) != {"accepted", "reason"}
                or not isinstance(parsed["accepted"], bool)
                or not isinstance(parsed["reason"], str)
            ):
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": content,
                    "latency_sec": elapsed,
                    "error": "schema_validation_failed",
                    "http_status": status,
                    "usage": data.get("usage", {}),
                }

            return {
                "valid": True,
                "accepted": parsed["accepted"],
                "reason": parsed["reason"],
                "raw_response": content,
                "latency_sec": elapsed,
                "error": "",
                "http_status": status,
                "usage": data.get("usage", {}),
            }

        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            last_error = f"http_{exc.code}: {body_text[:1000]}"
            if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504}:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < MAX_RETRIES:
            time.sleep(min(2 ** (attempt - 1), 8))

    return {
        "valid": False,
        "accepted": None,
        "reason": "",
        "raw_response": "",
        "latency_sec": time.perf_counter() - started,
        "error": last_error or "request_failed",
        "http_status": None,
        "usage": {},
    }


def run() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return 2

    input_path = Path(os.getenv("INPUT_JSON", DEFAULT_INPUT))
    if not input_path.exists():
        print(f"ERROR: input artifact not found: {input_path}", file=sys.stderr)
        return 2

    output_env = os.getenv("OUTPUT_JSON", "").strip()
    output_path = (
        Path(output_env)
        if output_env
        else input_path.with_name("benchmark_openrouter_v3_3_b3_smoke.json")
    )

    try:
        source, cases = load_cases(input_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"B.3 smoke input : {input_path}")
    print(f"Model            : {MODEL}")
    print(f"Cases            : {len(cases)}")
    print(f"Concurrency      : {CONCURRENCY}")
    print("Production path  : NOT MODIFIED")
    print()

    started = time.perf_counter()
    results: list[dict[str, Any] | None] = [None] * len(cases)

    def worker(item: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
        idx, case = item
        response = request_openrouter(case, api_key)
        actual = (
            "A" if response.get("accepted") is True
            else "R" if response.get("accepted") is False
            else None
        )
        result = {
            **case,
            "actual_label": actual,
            "correct": (
                actual is not None and actual == case["expected_label"]
            ),
            "model": response,
        }
        return idx, result

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, CONCURRENCY)
    ) as executor:
        futures = [executor.submit(worker, (i, c))
                   for i, c in enumerate(cases)]
        for future in concurrent.futures.as_completed(futures):
            idx, result = future.result()
            results[idx] = result
            marker = "OK" if result["correct"] else "MISS"
            print(
                f"[{idx + 1:02d}/{len(cases)}] {marker} "
                f"{result['field']} expected={result['expected_label']} "
                f"actual={result['actual_label']} "
                f"{result['model']['latency_sec']:.2f}s"
            )

    elapsed = time.perf_counter() - started
    final_results = [r for r in results if r is not None]

    valid = sum(r["model"]["valid"] for r in final_results)
    invalid = len(final_results) - valid
    correct = sum(r["correct"] for r in final_results)
    accepted = sum(r["actual_label"] == "A" for r in final_results)
    rejected = sum(r["actual_label"] == "R" for r in final_results)

    negative = [r for r in final_results if r["expected_label"] == "R"]
    negative_correct = sum(r["correct"] for r in negative)

    accuracy = 100.0 * correct / len(final_results) if final_results else 0.0
    negative_accuracy = (
        100.0 * negative_correct / len(negative) if negative else 0.0
    )

    contract_pass = valid == EXPECTED_CASES
    semantic_pass = (
        accuracy >= MIN_ACCURACY_PCT
        and negative_accuracy >= MIN_NEGATIVE_ACCURACY_PCT
    )
    smoke_pass = contract_pass and semantic_pass

    output = {
        "benchmark": {
            "benchmark_version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "benchmark_type": "semantic_boundary_smoke",
            "observational": False,
            "production_pipeline_modified": False,
            "candidate_generation_used": False,
            "llm_inference_used": True,
            "semantic_gate_only": True,
            "classification_mode": "structured_binary",
            "context_mode": "candidate_only",
            "full_benchmark_authorized": False,
        },
        "startup": source.get("startup", {}),
        "input": {
            "path": str(input_path),
            "source_benchmark_version": (
                source.get("benchmark", {}).get("benchmark_version",
                SOURCE_BENCHMARK_VERSION)
            ),
            "source_gate_version": (
                source.get("input", {}).get(
                    "source_gate_version", SOURCE_GATE_VERSION
                )
            ),
            "candidate_count": len(cases),
        },
        "model": {
            "provider": "openrouter",
            "name": MODEL,
            "endpoint": API_URL,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "concurrency": CONCURRENCY,
            "timeout_sec": TIMEOUT_SEC,
            "max_retries": MAX_RETRIES,
        },
        "population": {
            "expected": EXPECTED_CASES,
            "processed": len(final_results),
            "valid": valid,
            "invalid": invalid,
            "expected_accepted": EXPECTED_ACCEPTED,
            "expected_rejected": EXPECTED_REJECTED,
            "actual_accepted": accepted,
            "actual_rejected": rejected,
            "correct": correct,
            "accuracy_pct": round(accuracy, 4),
            "negative_expected": len(negative),
            "negative_correct": negative_correct,
            "negative_trap_accuracy_pct": round(negative_accuracy, 4),
        },
        "timing": {
            "total_wall_sec": round(elapsed, 4),
            "average_latency_sec": round(
                sum(r["model"]["latency_sec"] for r in final_results)
                / len(final_results), 4
            ) if final_results else 0.0,
            "min_latency_sec": round(
                min(r["model"]["latency_sec"] for r in final_results), 4
            ) if final_results else 0.0,
            "max_latency_sec": round(
                max(r["model"]["latency_sec"] for r in final_results), 4
            ) if final_results else 0.0,
        },
        "quality_checks": {
            "candidate_count_exact": len(cases) == EXPECTED_CASES,
            "all_candidates_processed": len(final_results) == EXPECTED_CASES,
            "structured_validity_pct": round(
                100.0 * valid / EXPECTED_CASES, 4
            ),
            "contract_gate_pass": contract_pass,
            "semantic_boundary_gate_pass": semantic_pass,
            "smoke_gate_pass": smoke_pass,
            "provenance_owned_by_python": True,
            "dimension_field_owned_by_python": True,
            "candidate_text_owned_by_python": True,
            "expected_labels_hidden_from_model": True,
            "production_pipeline_modified": False,
        },
        "thresholds": {
            "minimum_accuracy_pct": MIN_ACCURACY_PCT,
            "minimum_negative_trap_accuracy_pct": MIN_NEGATIVE_ACCURACY_PCT,
        },
        "results": final_results,
        "status": "PASS" if smoke_pass else "FAIL",
        "full_benchmark_authorized": False,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("B.3 SMOKE RESULT")
    print(f"  structured valid : {valid}/{EXPECTED_CASES}")
    print(f"  accuracy         : {accuracy:.2f}%")
    print(f"  negative accuracy: {negative_accuracy:.2f}%")
    print(f"  total wall       : {elapsed:.2f}s")
    print(f"  status           : {'PASS' if smoke_pass else 'FAIL'}")
    print(f"  output           : {output_path}")

    return 0 if smoke_pass else 1


if __name__ == "__main__":
    raise SystemExit(run())
