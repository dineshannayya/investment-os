#!/usr/bin/env python3
"""
V3.3-B.3-NEMOTRON-SMOKE

Standalone 16-case semantic smoke benchmark for
nvidia/nemotron-3-ultra-550b-a55b:free through OpenRouter.

Flow:
    frozen B.2.2 smoke set
        -> OpenRouter / Nemotron
        -> deterministic JSON recovery
        -> strict Python response validation
        -> A/R classification
        -> contract + semantic scoring

Expected labels are used only by Python for scoring and are never sent to
the model. No production evidence artifact is modified.
"""

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


BENCHMARK_VERSION = "V3.3-B.3-NEMOTRON-V2-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v6-nemotron-binary-ar"

INPUT_PATH = Path(os.getenv(
    "B3_NEMOTRON_INPUT",
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json",
))

OUTPUT_PATH = Path(os.getenv(
    "B3_NEMOTRON_OUTPUT",
    "/opt/investment-os/generated/restomart/"
    "benchmark_openrouter_v3_3_b3_nemotron_v2_smoke.json",
))

MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

CONCURRENCY = int(os.getenv("B3_NEMOTRON_CONCURRENCY", "1"))
TIMEOUT_SEC = int(os.getenv("B3_NEMOTRON_TIMEOUT", "120"))
RETRIES = int(os.getenv("B3_NEMOTRON_RETRIES", "2"))
MAX_TOKENS = int(os.getenv("B3_NEMOTRON_MAX_TOKENS", "128"))

BACKOFF_INITIAL_SEC = float(
    os.getenv("B3_NEMOTRON_BACKOFF_INITIAL", "10")
)
BACKOFF_MAX_SEC = float(
    os.getenv("B3_NEMOTRON_BACKOFF_MAX", "30")
)

EXPECTED_CASES = 16
EXPECTED_POSITIVE = 8
EXPECTED_NEGATIVE = 8

MIN_ACCURACY = 0.80
MIN_NEGATIVE_ACCURACY = 0.875


FIELD_DEFINITIONS = {
    "cash_burn": (
        "Explicit cash consumption, cash burn rate, cash depletion, "
        "or cash runway over a stated period."
    ),
    "customers": (
        "Actual customers, customer count, named customers, customer "
        "relationships, deployments, or explicit actual customer traction. "
        "A target customer segment or business description alone is "
        "insufficient."
    ),
    "adoption_usage": (
        "Actual product/service usage or adoption, including users, orders, "
        "transactions, deployments, utilization, or usage volume. A target, "
        "break-even threshold, or merely described business model is "
        "insufficient."
    ),
    "board_rights": (
        "An explicit investor/shareholder right to appoint, nominate, "
        "designate, or otherwise have board representation."
    ),
    "market_size": (
        "Explicit TAM, SAM, SOM, addressable market size, market value, "
        "or quantified market opportunity."
    ),
    "instrument": (
        "An explicitly stated financing/security instrument such as CCPS, "
        "equity, debt, SAFE, convertible instrument, or another named "
        "investment security."
    ),
    "valuation": (
        "An explicit company valuation, including pre-money, post-money, "
        "valuation cap, or another stated valuation amount."
    ),
    "gmv": "Explicit Gross Merchandise Value or GMV.",
    "growth": (
        "Explicit historical or projected growth rate, growth trajectory, "
        "or quantified growth."
    ),
    "founder_background": (
        "Explicit founder identity, experience, education, prior company, "
        "professional history, or other substantive founder background."
    ),
    "revenue": (
        "Explicit actual or projected company revenue, sales revenue, "
        "or revenue amount/rate."
    ),
    "generic": (
        "Direct, substantive evidence supporting the requested "
        "investment-analysis field."
    ),
}


SYSTEM_PROMPT = """You are a strict investment evidence classifier.

Determine whether the candidate text provides DIRECT, EXPLICIT evidence
for the requested investment-analysis field.

Rules:
1. Accept only if the candidate directly supports the requested field.
2. Do not infer information that is not stated.
3. A keyword or phrase alone is insufficient.
4. Reject incidental mentions of the field.
5. Reject legal, administrative, accounting, or boilerplate text unless it
   directly provides evidence for the requested field.
6. Reject formulas, ratios, headings, labels, or related metrics when they
   do not directly establish the requested field.
7. Related business information is not necessarily evidence for the field.
8. Be conservative: when uncertain, reject.

OUTPUT CONTRACT:
Your entire response must be exactly one character.

Output exactly A for accepted/direct evidence.
Output exactly R for rejected/insufficient evidence.

Do not output JSON.
Do not output a reason.
Do not output analysis.
Do not output markdown or code fences.
Do not output any other characters."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    results = data.get("results", [])
    by_id = {str(r["candidate_id"]): r for r in results}

    cases: list[dict[str, Any]] = []

    for item in data.get("smoke_selection", []):
        candidate_id = str(item["candidate_id"])

        if candidate_id not in by_id:
            raise RuntimeError(
                f"Candidate {candidate_id} from smoke_selection "
                "was not found in results[]"
            )

        r = by_id[candidate_id]

        cases.append({
            "index": item["index"],
            "candidate_id": candidate_id,
            "dimension": r["dimension"],
            "field": r["field"],
            "candidate_text": r["candidate_text"],
            "expected_label": r.get("smoke_expected_label"),
            "challenge_type": r.get("smoke_challenge_type"),
            "source_path": r.get(
                "source_path",
                item.get("source_path"),
            ),
            "extraction_id": r.get("extraction_id"),
        })

    if len(cases) != EXPECTED_CASES:
        raise RuntimeError(
            f"Frozen smoke population mismatch: expected "
            f"{EXPECTED_CASES}, got {len(cases)}"
        )

    accepted = sum(
        c["expected_label"] == "A" for c in cases
    )
    rejected = sum(
        c["expected_label"] == "R" for c in cases
    )

    if accepted != EXPECTED_POSITIVE or rejected != EXPECTED_NEGATIVE:
        raise RuntimeError(
            "Frozen smoke label distribution mismatch: "
            f"expected {EXPECTED_POSITIVE} A / "
            f"{EXPECTED_NEGATIVE} R, got {accepted} A / {rejected} R"
        )

    return cases


def build_user_prompt(field: str, candidate_text: str) -> str:
    definition = FIELD_DEFINITIONS.get(
        field,
        FIELD_DEFINITIONS["generic"],
    )

    return (
        f"Requested field: {field}\n\n"
        f"Field definition:\n{definition}\n\n"
        f"Candidate text:\n{candidate_text}\n\n"
        "Classify only the candidate text against the requested field.\n"
        "Return exactly one JSON object."
    )


def call_openrouter(
    api_key: str,
    field: str,
    candidate_text: str,
) -> dict[str, Any]:

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    field,
                    candidate_text,
                ),
            },
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": MAX_TOKENS,

    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Investment OS V3.3-B.3 Nemotron Smoke",
    }

    request_body = json.dumps(payload).encode("utf-8")

    for attempt in range(1, RETRIES + 1):
        started = time.perf_counter()

        request = urllib.request.Request(
            API_URL,
            data=request_body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT_SEC,
            ) as response:

                raw = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

                latency = time.perf_counter() - started
                data = json.loads(raw)
                choices = data.get("choices") or []

                if not choices:
                    return {
                        "error": "response_empty",
                        "http_status": response.status,
                        "latency_sec": latency,
                        "raw_response": None,
                        "usage": data.get("usage", {}),
                        "attempt": attempt,
                    }

                message = choices[0].get("message") or {}
                content = message.get("content")

                if content is None:
                    return {
                        "error": "response_empty",
                        "http_status": response.status,
                        "latency_sec": latency,
                        "raw_response": None,
                        "usage": data.get("usage", {}),
                        "attempt": attempt,
                    }

                return {
                    "raw_response": content,
                    "http_status": response.status,
                    "latency_sec": latency,
                    "usage": data.get("usage", {}),
                    "attempt": attempt,
                }

        except urllib.error.HTTPError as exc:
            latency = time.perf_counter() - started

            try:
                error_body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = str(exc)

            if exc.code == 429:
                if attempt < RETRIES:
                    delay = min(
                        BACKOFF_INITIAL_SEC * (2 ** (attempt - 1)),
                        BACKOFF_MAX_SEC,
                    )
                    delay += random.uniform(0, 1)

                    print(
                        f"    provider 429; backing off "
                        f"{delay:.1f}s "
                        f"(attempt {attempt}/{RETRIES})",
                        flush=True,
                    )

                    time.sleep(delay)
                    continue

                return {
                    "error": "provider_rate_limited",
                    "http_status": 429,
                    "latency_sec": latency,
                    "raw_response": None,
                    "http_error": error_body[:4000],
                    "attempt": attempt,
                }

            if exc.code in {
                408, 409, 425, 500, 502, 503, 504
            } and attempt < RETRIES:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue

            return {
                "error": "http_error",
                "http_status": exc.code,
                "latency_sec": latency,
                "raw_response": None,
                "http_error": error_body[:4000],
                "attempt": attempt,
            }

        except (socket.timeout, TimeoutError) as exc:
            latency = time.perf_counter() - started

            if attempt < RETRIES:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue

            return {
                "error": "transport_timeout",
                "http_status": None,
                "latency_sec": latency,
                "raw_response": None,
                "exception": str(exc),
                "attempt": attempt,
            }

        except (urllib.error.URLError, ssl.SSLError) as exc:
            latency = time.perf_counter() - started

            if attempt < RETRIES:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue

            return {
                "error": "transport_network_error",
                "http_status": None,
                "latency_sec": latency,
                "raw_response": None,
                "exception": str(exc),
                "attempt": attempt,
            }

        except Exception as exc:
            return {
                "error": "transport_error",
                "http_status": None,
                "latency_sec": time.perf_counter() - started,
                "raw_response": None,
                "exception": str(exc),
                "attempt": attempt,
            }

    return {
        "error": "transport_error",
        "http_status": None,
        "latency_sec": 0.0,
        "raw_response": None,
    }


def parse_binary_response(raw_response: str | None) -> tuple[bool, str | None, str | None]:
    """Accept only a single A or R character after surrounding whitespace."""
    if raw_response is None:
        return False, None, "response_empty"

    normalized = raw_response.strip()

    if normalized == "A":
        return True, "A", None
    if normalized == "R":
        return True, "R", None

    return False, None, "response_contract_invalid"


def run_case(
    api_key: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    api = call_openrouter(
        api_key,
        case["field"],
        case["candidate_text"],
    )

    raw_response = api.get("raw_response")
    if raw_response is None:
        valid, actual_label, parse_error = False, None, "response_empty"
    else:
        valid, actual_label, parse_error = parse_binary_response(raw_response)

    error = parse_error or api.get("error")

    return {
        **case,
        "model": MODEL,
        "valid": valid,
        "accepted": actual_label == "A" if valid else None,
        "actual_label": actual_label,
        "correct": bool(valid and actual_label == case["expected_label"]),
        "reason": None,
        "raw_response": raw_response,
        "response_recovery": "strict_binary" if valid else "none",
        "error": error,
        "http_status": api.get("http_status"),
        "http_error": api.get("http_error"),
        "exception": api.get("exception"),
        "latency_sec": round(api.get("latency_sec", 0.0), 4),
        "attempt": api.get("attempt"),
        "usage": api.get("usage", {}),
    }


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return (
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )


def main() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY is not set"
        )

    data = load_json(INPUT_PATH)
    cases = extract_cases(data)

    print(
        f"B.3-NEMOTRON smoke input : {INPUT_PATH}"
    )
    print(f"Model                     : {MODEL}")
    print(f"Cases                     : {len(cases)}")
    print(f"Concurrency               : {CONCURRENCY}")
    print(
        f"429 backoff               : "
        f"{BACKOFF_INITIAL_SEC:.1f}s -> "
        f"{BACKOFF_MAX_SEC:.1f}s"
    )
    print("Response format           : strict A/R")
    print("Response parsing          : strict single-character")
    print("Production path           : NOT MODIFIED")
    print()

    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=CONCURRENCY
    ) as executor:

        future_map = {
            executor.submit(
                run_case,
                api_key,
                case,
            ): case
            for case in cases
        }

        for n, future in enumerate(
            concurrent.futures.as_completed(future_map),
            1,
        ):
            case = future_map[future]

            try:
                result = future.result()
            except Exception as exc:
                result = {
                    **case,
                    "model": MODEL,
                    "valid": False,
                    "accepted": None,
                    "actual_label": None,
                    "correct": False,
                    "reason": None,
                    "raw_response": None,
                    "response_recovery": "none",
                    "error": "transport_error",
                    "http_status": None,
                    "http_error": None,
                    "exception": str(exc),
                    "latency_sec": 0.0,
                    "attempt": None,
                    "usage": {},
                }

            results.append(result)

            suffix = (
                f" error={result['error']}"
                if result["error"]
                else ""
            )

            print(
                f"[{n:02d}/{len(cases):02d}] "
                f"{result['field']} "
                f"expected={result['expected_label']} "
                f"actual={result['actual_label']} "
                f"valid={'yes' if result['valid'] else 'no'} "
                f"contract={result['response_recovery']} "
                f"{result['latency_sec']:.2f}s"
                f"{suffix}",
                flush=True,
            )

    results.sort(
        key=lambda x: x["index"]
    )

    wall = time.perf_counter() - started

    valid = [
        r for r in results
        if r["valid"]
    ]

    correct = [
        r for r in valid
        if r["correct"]
    ]

    negative_cases = [
        r for r in results
        if r["expected_label"] == "R"
    ]

    negative_correct = [
        r for r in negative_cases
        if r["valid"] and r["correct"]
    ]

    strict_binary = sum(
        r["response_recovery"] == "strict_binary"
        for r in results
    )

    response_contract_invalid = sum(
        r["error"] == "response_contract_invalid"
        for r in results
    )


    errors: dict[str, int] = {}

    for r in results:
        if r.get("error"):
            errors[r["error"]] = (
                errors.get(r["error"], 0) + 1
            )

    accuracy = (
        len(correct) / EXPECTED_CASES
    )

    negative_accuracy = (
        len(negative_correct)
        / EXPECTED_NEGATIVE
    )

    contract_gate = (
        len(valid) == EXPECTED_CASES
    )

    semantic_gate = (
        accuracy >= MIN_ACCURACY
    )

    negative_gate = (
        negative_accuracy >= MIN_NEGATIVE_ACCURACY
    )

    if any(
        r.get("error") == "provider_rate_limited"
        for r in results
    ):
        status = "BLOCKED"
    elif (
        contract_gate
        and semantic_gate
        and negative_gate
    ):
        status = "PASS"
    else:
        status = "FAIL"

    latencies = [
        r["latency_sec"]
        for r in results
        if r["latency_sec"] > 0
    ]

    average_latency = (
        sum(latencies) / len(latencies)
        if latencies
        else None
    )

    p95_latency = percentile(
        latencies,
        0.95,
    )

    summary = {
        "processed": len(results),
        "structured_valid": len(valid),
        "structured_valid_rate": (
            len(valid) / EXPECTED_CASES
        ),
        "expected_accepted": EXPECTED_POSITIVE,
        "expected_rejected": EXPECTED_NEGATIVE,
        "actual_accepted": sum(
            r["actual_label"] == "A"
            for r in valid
        ),
        "actual_rejected": sum(
            r["actual_label"] == "R"
            for r in valid
        ),
        "correct": len(correct),
        "accuracy": accuracy,
        "negative_correct": len(
            negative_correct
        ),
        "negative_accuracy": negative_accuracy,
        "strict_binary": strict_binary,
        "response_contract_invalid": response_contract_invalid,
        "average_latency_sec": average_latency,
        "p95_latency_sec": p95_latency,
        "total_wall_sec": wall,
        "error_counts": errors,
        "contract_gate": contract_gate,
        "semantic_accuracy_gate": semantic_gate,
        "negative_boundary_gate": negative_gate,
        "status": status,
    }

    output = {
        "benchmark": {
            "version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "observational": True,
            "production_pipeline_modified": False,
            "full_benchmark_authorized": False,
            "output_contract": "single_character_A_or_R",
        },
        "input": {
            "path": str(INPUT_PATH),
            "source_benchmark_version": data.get(
                "benchmark"
            ),
            "source_gate_version": data.get(
                "source_gate_version"
            ),
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
            "response_format": {
                "type": "json_object"
            },
            "concurrency": CONCURRENCY,
            "timeout_sec": TIMEOUT_SEC,
            "retries": RETRIES,
            "429_backoff_initial_sec": (
                BACKOFF_INITIAL_SEC
            ),
            "429_backoff_max_sec": (
                BACKOFF_MAX_SEC
            ),
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
            "expected_labels_hidden": True,
            "response_schema_enforced_in_python": False,
            "binary_contract_enforced_in_python": True,
            "json_schema_provider_enforcement": False,
            "deterministic_binary_contract": True,
            "llm_response_repair": False,
            "production_unmodified": True,
            "accuracy_threshold": MIN_ACCURACY,
            "negative_accuracy_threshold": (
                MIN_NEGATIVE_ACCURACY
            ),
        },
        "timing": {
            "total_wall_sec": wall,
            "average_latency_sec": average_latency,
            "p95_latency_sec": p95_latency,
        },
        "summary": summary,
        "results": results,
        "status": status,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("B.3-NEMOTRON SMOKE RESULT")

    print(
        f"  structured valid       : "
        f"{summary['structured_valid']}/{EXPECTED_CASES}"
    )
    print(
        f"  strict A/R valid       : "
        f"{summary['strict_binary']}"
    )
    print(
        f"  contract invalid       : "
        f"{summary['response_contract_invalid']}"
    )

    print(
        f"  expected accepted      : "
        f"{EXPECTED_POSITIVE}"
    )
    print(
        f"  expected rejected      : "
        f"{EXPECTED_NEGATIVE}"
    )
    print(
        f"  actual accepted        : "
        f"{summary['actual_accepted']}"
    )
    print(
        f"  actual rejected        : "
        f"{summary['actual_rejected']}"
    )
    print(
        f"  correct                : "
        f"{summary['correct']}/{EXPECTED_CASES}"
    )
    print(
        f"  accuracy               : "
        f"{accuracy:.2%}"
    )
    print(
        f"  negative accuracy      : "
        f"{negative_accuracy:.2%}"
    )

    if average_latency is not None:
        print(
            f"  average latency        : "
            f"{average_latency:.3f}s"
        )
    else:
        print(
            "  average latency        : N/A"
        )

    if p95_latency is not None:
        print(
            f"  p95 latency            : "
            f"{p95_latency:.3f}s"
        )
    else:
        print(
            "  p95 latency            : N/A"
        )

    print(
        f"  total wall             : "
        f"{wall:.2f}s"
    )
    print(
        f"  contract gate          : "
        f"{'PASS' if contract_gate else 'FAIL'}"
    )
    print(
        f"  semantic accuracy gate : "
        f"{'PASS' if semantic_gate else 'FAIL'}"
    )
    print(
        f"  negative boundary gate : "
        f"{'PASS' if negative_gate else 'FAIL'}"
    )
    print(
        f"  error counts           : "
        f"{errors}"
    )
    print(
        f"  status                 : {status}"
    )
    print(
        f"  output                 : {OUTPUT_PATH}"
    )

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
