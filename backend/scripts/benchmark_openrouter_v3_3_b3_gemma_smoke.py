#!/usr/bin/env python3
"""V3.3-B.3-GEMMA smoke benchmark for the frozen 16-case B.2.2 set."""

from __future__ import annotations

import concurrent.futures
import json
import os
import random
import socket
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BENCHMARK_VERSION = "V3.3-B.3-GEMMA-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v5-openrouter-json-object"

INPUT_PATH = Path(os.getenv(
    "B3_GEMMA_INPUT",
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json",
))
OUTPUT_PATH = Path(os.getenv(
    "B3_GEMMA_OUTPUT",
    "/opt/investment-os/generated/restomart/"
    "benchmark_openrouter_v3_3_b3_gemma_smoke.json",
))

MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
API_KEY_ENV = "OPENROUTER_API_KEY"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

CONCURRENCY = int(os.getenv("B3_GEMMA_CONCURRENCY", "2"))
TIMEOUT_SEC = int(os.getenv("B3_GEMMA_TIMEOUT", "120"))
RETRIES = int(os.getenv("B3_GEMMA_RETRIES", "3"))
MAX_TOKENS = int(os.getenv("B3_GEMMA_MAX_TOKENS", "128"))

EXPECTED_CASES = 16
EXPECTED_POSITIVE = 8
EXPECTED_NEGATIVE = 8
MIN_ACCURACY = 0.80
MIN_NEGATIVE_ACCURACY = 0.875

RETRYABLE_HTTP = {408, 409, 425, 429, 500, 502, 503, 504}
NONRETRYABLE_HTTP = {400, 401, 403, 404}

FIELD_DEFINITIONS = {
    "cash_burn": "Explicit cash consumption, cash burn rate, cash depletion, or cash runway over a stated period.",
    "customers": "Actual customers, customer count, named customers, customer relationships, deployments, or explicit actual customer traction. A target customer segment or business description alone is insufficient.",
    "adoption_usage": "Actual product/service usage or adoption, including users, orders, transactions, deployments, utilization, or usage volume. A target, break-even threshold, or merely described business model is insufficient.",
    "board_rights": "An explicit investor/shareholder right to appoint, nominate, designate, or otherwise have board representation.",
    "market_size": "Explicit TAM, SAM, SOM, addressable market size, market value, or quantified market opportunity.",
    "instrument": "An explicitly stated financing/security instrument such as CCPS, equity, debt, SAFE, convertible instrument, or another named investment security.",
    "valuation": "An explicit company valuation, including pre-money, post-money, valuation cap, or another stated valuation amount.",
    "gmv": "Explicit Gross Merchandise Value or GMV.",
    "growth": "Explicit historical or projected growth rate, growth trajectory, or quantified growth.",
    "founder_background": "Explicit founder identity, experience, education, prior company, professional history, or other substantive founder background.",
    "revenue": "Explicit actual or projected company revenue, sales revenue, or revenue amount/rate.",
    "generic": "Direct, substantive evidence supporting the requested investment-analysis field.",
}

SYSTEM_PROMPT = """You are a strict investment evidence classifier.

Determine whether the candidate text provides DIRECT, EXPLICIT evidence for
the requested investment-analysis field.

Rules:
1. Accept only if the text directly supports the requested field.
2. Do not infer information that is not stated.
3. A keyword or phrase alone is insufficient.
4. Reject incidental mentions of the field.
5. Reject legal, administrative, accounting, or boilerplate text unless it
   directly provides evidence for the requested field.
6. Reject formulas, ratios, headings, labels, or related metrics when they do
   not directly establish the requested field.
7. Related business information is not necessarily evidence for the field.
8. Be conservative: when uncertain, reject.

Return ONLY one JSON object with exactly two keys:
{"accepted": true or false, "reason": "brief explanation"}

Do not use markdown fences. Do not return a list or multiple alternatives."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {str(x["candidate_id"]): x for x in data.get("results", [])}
    cases = []
    for item in data.get("smoke_selection", []):
        cid = str(item["candidate_id"])
        if cid not in by_id:
            raise RuntimeError(f"Candidate missing from results: {cid}")
        r = by_id[cid]
        cases.append({
            "index": item["index"],
            "candidate_id": cid,
            "dimension": r["dimension"],
            "field": r["field"],
            "candidate_text": r["candidate_text"],
            "expected_label": r.get("smoke_expected_label"),
            "challenge_type": r.get("smoke_challenge_type"),
            "source_path": r.get("source_path", item.get("source_path")),
            "extraction_id": r.get("extraction_id"),
        })

    if len(cases) != EXPECTED_CASES:
        raise RuntimeError(f"Expected {EXPECTED_CASES} cases, got {len(cases)}")
    pos = sum(x["expected_label"] == "A" for x in cases)
    neg = sum(x["expected_label"] == "R" for x in cases)
    if (pos, neg) != (EXPECTED_POSITIVE, EXPECTED_NEGATIVE):
        raise RuntimeError(f"Expected 8 A / 8 R, got {pos} A / {neg} R")
    return cases


def user_prompt(field: str, text: str) -> str:
    definition = FIELD_DEFINITIONS.get(field, FIELD_DEFINITIONS["generic"])
    return f"""Requested field: {field}

Field definition:
{definition}

Candidate text:
{text}

Classify only the candidate text against the requested field.
Return only the JSON object with exactly:
accepted (boolean)
reason (string)"""


def call_model(api_key: str, field: str, text: str) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(field, text)},
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": MAX_TOKENS,
        # Gemma free endpoint: JSON object, NOT JSON-schema enforcement.
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Investment OS V3.3-B.3 Gemma Smoke",
    }
    body = json.dumps(payload).encode()
    last = None

    for attempt in range(1, RETRIES + 1):
        start = time.perf_counter()
        req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                latency = time.perf_counter() - start
                data = json.loads(raw)
                choices = data.get("choices") or []
                if not choices:
                    return {"error": "response_empty", "http_status": resp.status,
                            "latency_sec": latency, "raw_response": None,
                            "usage": data.get("usage", {})}
                content = (choices[0].get("message") or {}).get("content")
                if not content:
                    return {"error": "response_empty", "http_status": resp.status,
                            "latency_sec": latency, "raw_response": content,
                            "usage": data.get("usage", {})}
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    return {"error": "response_not_json", "http_status": resp.status,
                            "latency_sec": latency, "raw_response": content,
                            "usage": data.get("usage", {})}
                return {"parsed": parsed, "http_status": resp.status,
                        "latency_sec": latency, "raw_response": content,
                        "usage": data.get("usage", {}), "attempt": attempt}
        except urllib.error.HTTPError as exc:
            latency = time.perf_counter() - start
            try:
                err = exc.read().decode("utf-8", errors="replace")
            except Exception:
                err = str(exc)
            if exc.code == 404:
                return {"error": "provider_routing_error", "http_status": exc.code,
                        "latency_sec": latency, "raw_response": None,
                        "http_error": err[:4000], "attempt": attempt}
            if exc.code not in RETRYABLE_HTTP or attempt == RETRIES:
                return {"error": "http_error", "http_status": exc.code,
                        "latency_sec": latency, "raw_response": None,
                        "http_error": err[:4000], "attempt": attempt}
            time.sleep(min(2 ** (attempt - 1), 8) + random.random() * 0.25)
            last = err
        except (socket.timeout, TimeoutError) as exc:
            latency = time.perf_counter() - start
            if attempt == RETRIES:
                return {"error": "transport_timeout", "http_status": None,
                        "latency_sec": latency, "raw_response": None,
                        "exception": str(exc), "attempt": attempt}
            time.sleep(min(2 ** (attempt - 1), 8))
            last = str(exc)
        except (urllib.error.URLError, ssl.SSLError) as exc:
            latency = time.perf_counter() - start
            if attempt == RETRIES:
                return {"error": "transport_network_error", "http_status": None,
                        "latency_sec": latency, "raw_response": None,
                        "exception": str(exc), "attempt": attempt}
            time.sleep(min(2 ** (attempt - 1), 8))
            last = str(exc)
        except Exception as exc:
            return {"error": "transport_error", "http_status": None,
                    "latency_sec": time.perf_counter() - start,
                    "raw_response": None, "exception": str(exc),
                    "attempt": attempt}

    return {"error": "transport_error", "http_status": None,
            "latency_sec": 0.0, "raw_response": None, "exception": str(last)}


def validate(parsed: Any) -> tuple[bool, bool | None, str | None]:
    if not isinstance(parsed, dict):
        return False, None, "response_schema_invalid"
    if set(parsed) != {"accepted", "reason"}:
        return False, None, "response_schema_invalid"
    if type(parsed["accepted"]) is not bool:
        return False, None, "response_schema_invalid"
    if not isinstance(parsed["reason"], str):
        return False, None, "response_schema_invalid"
    return True, parsed["accepted"], None


def run_case(api_key: str, case: dict[str, Any]) -> dict[str, Any]:
    api = call_model(api_key, case["field"], case["candidate_text"])
    valid, accepted, validation_error = validate(api["parsed"]) if "parsed" in api else (False, None, None)
    if not valid and "parsed" in api:
        api["error"] = validation_error

    actual = ("A" if accepted else "R") if valid else None
    return {
        **case,
        "model": MODEL,
        "valid": valid,
        "accepted": accepted,
        "actual_label": actual,
        "correct": valid and actual == case["expected_label"],
        "reason": api.get("parsed", {}).get("reason") if valid else None,
        "raw_response": api.get("raw_response"),
        "error": api.get("error"),
        "http_status": api.get("http_status"),
        "latency_sec": round(api.get("latency_sec", 0.0), 4),
        "attempt": api.get("attempt"),
        "usage": api.get("usage", {}),
        "http_error": api.get("http_error"),
        "exception": api.get("exception"),
    }


def main() -> int:
    key = os.getenv(API_KEY_ENV)
    if not key:
        raise SystemExit(f"{API_KEY_ENV} is not set")

    data = load_json(INPUT_PATH)
    cases = extract_cases(data)

    print(f"B.3-GEMMA smoke input : {INPUT_PATH}")
    print(f"Model                  : {MODEL}")
    print(f"Cases                  : {len(cases)}")
    print(f"Concurrency            : {CONCURRENCY}")
    print("Response format        : json_object")
    print("Production path        : NOT MODIFIED\n")

    started = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(run_case, key, c): c for c in cases}
        for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
            case = futures[future]
            try:
                r = future.result()
            except Exception as exc:
                r = {**case, "model": MODEL, "valid": False, "accepted": None,
                     "actual_label": None, "correct": False, "reason": None,
                     "raw_response": None, "error": "transport_error",
                     "http_status": None, "latency_sec": 0.0,
                     "exception": str(exc)}
            results.append(r)
            print(f"[{n:02d}/{len(cases):02d}] {r['field']} "
                  f"expected={r['expected_label']} actual={r['actual_label']} "
                  f"{r['latency_sec']:.2f}s"
                  + (f" error={r['error']}" if r["error"] else ""))
    results.sort(key=lambda x: x["index"])

    valid = [r for r in results if r["valid"]]
    correct = [r for r in valid if r["correct"]]
    negatives = [r for r in results if r["expected_label"] == "R"]
    neg_correct = [r for r in negatives if r["valid"] and r["correct"]]
    accuracy = len(correct) / EXPECTED_CASES
    neg_accuracy = len(neg_correct) / EXPECTED_NEGATIVE
    errors = {}
    for r in results:
        if r.get("error"):
            errors[r["error"]] = errors.get(r["error"], 0) + 1

    if not valid:
        status = "BLOCKED"
    elif len(valid) == EXPECTED_CASES and accuracy >= MIN_ACCURACY and neg_accuracy >= MIN_NEGATIVE_ACCURACY:
        status = "PASS"
    else:
        status = "FAIL"

    wall = time.perf_counter() - started
    latencies = [r["latency_sec"] for r in results if r["latency_sec"] > 0]
    summary = {
        "processed": len(results),
        "structured_valid": len(valid),
        "structured_valid_rate": len(valid) / EXPECTED_CASES,
        "expected_accepted": EXPECTED_POSITIVE,
        "expected_rejected": EXPECTED_NEGATIVE,
        "actual_accepted": sum(r["actual_label"] == "A" for r in valid),
        "actual_rejected": sum(r["actual_label"] == "R" for r in valid),
        "correct": len(correct),
        "accuracy": accuracy,
        "negative_correct": len(neg_correct),
        "negative_accuracy": neg_accuracy,
        "average_latency_sec": sum(latencies) / len(latencies) if latencies else None,
        "total_wall_sec": wall,
        "error_counts": errors,
        "contract_gate": len(valid) == EXPECTED_CASES,
        "semantic_accuracy_gate": accuracy >= MIN_ACCURACY,
        "negative_boundary_gate": neg_accuracy >= MIN_NEGATIVE_ACCURACY,
        "status": status,
    }

    output = {
        "benchmark": {
            "version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "observational": True,
            "production_pipeline_modified": False,
            "full_benchmark_authorized": False,
        },
        "input": {
            "path": str(INPUT_PATH),
            "source_benchmark_version": data.get("benchmark"),
            "source_gate_version": data.get("source_gate_version"),
            "source_artifact_id": data.get("id"),
            "cases": len(cases),
        },
        "model": {
            "provider": "openrouter",
            "model": MODEL,
            "endpoint": API_URL,
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "concurrency": CONCURRENCY,
            "timeout_sec": TIMEOUT_SEC,
            "retries": RETRIES,
        },
        "population": {
            "candidate_count": len(cases),
            "expected_accepted": EXPECTED_POSITIVE,
            "expected_rejected": EXPECTED_NEGATIVE,
            "candidate_population_frozen": True,
            "expected_labels_hidden_from_model": True,
        },
        "quality_checks": {
            "provenance_owned_by_python": True,
            "response_schema_enforced_in_python": True,
            "json_schema_provider_enforcement": False,
            "production_unmodified": True,
            "accuracy_threshold": MIN_ACCURACY,
            "negative_accuracy_threshold": MIN_NEGATIVE_ACCURACY,
        },
        "timing": {
            "total_wall_sec": wall,
            "average_latency_sec": summary["average_latency_sec"],
        },
        "summary": summary,
        "results": results,
        "status": status,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\nB.3-GEMMA SMOKE RESULT")
    print(f"  structured valid       : {summary['structured_valid']}/{EXPECTED_CASES}")
    print(f"  expected accepted      : {EXPECTED_POSITIVE}")
    print(f"  expected rejected      : {EXPECTED_NEGATIVE}")
    print(f"  actual accepted        : {summary['actual_accepted']}")
    print(f"  actual rejected        : {summary['actual_rejected']}")
    print(f"  correct                : {summary['correct']}/{EXPECTED_CASES}")
    print(f"  accuracy               : {accuracy:.2%}")
    print(f"  negative accuracy      : {neg_accuracy:.2%}")
    print(f"  average latency        : {summary['average_latency_sec']:.3f}s"
          if summary["average_latency_sec"] is not None else
          "  average latency        : N/A")
    print(f"  total wall             : {wall:.2f}s")
    print(f"  contract gate          : {'PASS' if summary['contract_gate'] else 'FAIL'}")
    print(f"  semantic accuracy gate : {'PASS' if summary['semantic_accuracy_gate'] else 'FAIL'}")
    print(f"  negative boundary gate : {'PASS' if summary['negative_boundary_gate'] else 'FAIL'}")
    print(f"  status                 : {status}")
    print(f"  output                 : {OUTPUT_PATH}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
