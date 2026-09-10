#!/usr/bin/env python3
"""
V3.3-B.3-V2 controlled GPT-OSS-20B teacher smoke benchmark.

Purpose
-------
Determine whether GPT-OSS-20B can reliably perform the existing B.2.2
semantic-validation task when:
  * the provider is pinned,
  * provider fallback is disabled,
  * concurrency is 1,
  * reasoning effort is medium,
  * generation budget is 1024 tokens,
  * the semantic task and 16 frozen smoke cases remain unchanged.

This is an EXPERIMENTAL benchmark only.
Production candidate generation / validation paths are NOT modified.

Environment
-----------
OPENROUTER_API_KEY must be available inside the backend container.

Optional environment overrides:
  GPTOSS_PROVIDER=AkashML
  GPTOSS_REASONING_EFFORT=medium
  GPTOSS_MAX_TOKENS=1024
  GPTOSS_TEMPERATURE=0.0
  GPTOSS_TOP_P=1.0
  GPTOSS_INPUT_PATH=...
  GPTOSS_OUTPUT_PATH=...

No response repair is performed.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Frozen benchmark configuration
# ---------------------------------------------------------------------------

BENCHMARK_VERSION = "V3.3-B.3-V2"
BENCHMARK_TYPE = "controlled_teacher_smoke"

MODEL = "openai/gpt-oss-20b"
PINNED_PROVIDER = os.getenv("GPTOSS_PROVIDER", "AkashML")

CONCURRENCY = 1
REASONING_EFFORT = os.getenv("GPTOSS_REASONING_EFFORT", "medium")
TEMPERATURE = float(os.getenv("GPTOSS_TEMPERATURE", "0.0"))
TOP_P = float(os.getenv("GPTOSS_TOP_P", "1.0"))
MAX_TOKENS = int(os.getenv("GPTOSS_MAX_TOKENS", "1024"))

REQUIRE_PARAMETERS = True
ALLOW_FALLBACKS = False

EXPECTED_CASE_COUNT = 16
EXPECTED_SOURCE_BENCHMARK = "V3.3-B.2.2"

DEFAULT_INPUT_PATH = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json"
)
DEFAULT_OUTPUT_PATH = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_openrouter_v3_3_b3_gptoss20b_teacher_v2_smoke.json"
)

INPUT_PATH = os.getenv("GPTOSS_INPUT_PATH", DEFAULT_INPUT_PATH)
OUTPUT_PATH = os.getenv("GPTOSS_OUTPUT_PATH", DEFAULT_OUTPUT_PATH)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Smoke acceptance gates.
MIN_STRUCTURED_VALID = 0.95
MIN_OVERALL_ACCURACY = 0.875
MIN_POSITIVE_ACCURACY = 0.875
MIN_NEGATIVE_ACCURACY = 0.875
MAX_EMPTY = 1
MAX_BUDGET_EXHAUSTED = 0
MAX_PROVIDER_DRIFT = 0


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "accepted": {"type": "boolean"},
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "reason": {"type": "string"},
    },
    "required": ["accepted", "confidence", "reason"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Field definitions
# Keep aligned with the B.2.2 semantic task.
# ---------------------------------------------------------------------------

FIELD_DEFINITIONS = {
    "cash_burn": (
        "Evidence of cash consumption, cash burn rate, cash depletion, "
        "cash runway, or equivalent direct cash-burn evidence."
    ),
    "board_rights": (
        "Evidence of specific investor or shareholder board appointment, "
        "nomination, observer, representation, consent, or governance "
        "rights. An incidental mention of the Board is insufficient."
    ),
    "adoption_usage": (
        "Evidence of actual product/service adoption, usage, active users, "
        "usage volume, deployments, utilization, or equivalent concrete "
        "adoption evidence. A forecast, break-even calculation, or generic "
        "business description is insufficient."
    ),
    "customers": (
        "Evidence of actual customers, customer count, named customers, "
        "customer relationships, deployments to customers, or equivalent "
        "concrete customer evidence. A generic description of the business "
        "model or target customer is insufficient."
    ),
    "market_size": (
        "Evidence quantifying the addressable market, TAM, SAM, SOM, market "
        "value, market volume, or equivalent market-size measurement."
    ),
    "instrument": (
        "Evidence explicitly identifying the financing/security instrument "
        "used in the transaction or financing round, such as CCPS."
    ),
    "valuation": (
        "Evidence explicitly stating a company valuation, valuation cap, "
        "pre-money valuation, post-money valuation, or equivalent valuation "
        "figure."
    ),
    "gmv": (
        "Evidence explicitly stating gross merchandise value (GMV) or a "
        "specific GMV figure."
    ),
    "growth": (
        "Evidence of actual or explicitly stated business growth, growth "
        "rate, period-over-period increase, or equivalent quantified growth."
    ),
    "founder_background": (
        "Evidence of a founder's identity, professional background, prior "
        "experience, education, achievements, or relevant entrepreneurial "
        "history."
    ),
    "revenue": (
        "Evidence explicitly stating actual or projected company revenue, "
        "sales revenue, or a specific revenue figure."
    ),
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_usage(data: dict[str, Any]) -> dict[str, Any] | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None

    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        details = {}

    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
        "cost": usage.get("cost"),
        "is_byok": usage.get("is_byok"),
    }


def validate_schema(obj: Any) -> tuple[bool, str | None]:
    if not isinstance(obj, dict):
        return False, "root_not_object"

    required = {"accepted", "confidence", "reason"}
    if set(obj.keys()) != required:
        return False, "schema_keys_mismatch"

    if not isinstance(obj["accepted"], bool):
        return False, "accepted_not_boolean"

    confidence = obj["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return False, "confidence_not_number"

    if not math.isfinite(float(confidence)):
        return False, "confidence_not_finite"

    if not 0.0 <= float(confidence) <= 1.0:
        return False, "confidence_out_of_range"

    if not isinstance(obj["reason"], str):
        return False, "reason_not_string"

    return True, None


def detect_budget_exhaustion(
    usage: dict[str, Any] | None,
    finish_reason: Any,
    raw_response: str | None,
) -> bool:
    if usage:
        completion = usage.get("completion_tokens")
        if isinstance(completion, int) and completion >= MAX_TOKENS:
            return True

    if finish_reason in {
        "length",
        "max_tokens",
        "max_completion_tokens",
    }:
        return True

    # A partial JSON object ending at the configured output limit is also
    # useful diagnostic evidence, even when the provider omits finish_reason.
    if (
        raw_response
        and usage
        and isinstance(usage.get("completion_tokens"), int)
        and usage["completion_tokens"] >= MAX_TOKENS
        and raw_response.strip().startswith("{")
        and not raw_response.strip().endswith("}")
    ):
        return True

    return False


def build_prompt(field: str, candidate: str) -> str:
    definition = FIELD_DEFINITIONS.get(
        field,
        "Direct evidence supporting the specified investment-analysis field.",
    )

    return f"""You are a strict investment-analysis evidence validator.

Evaluate ONLY whether the candidate text explicitly supports the specified
investment-analysis field.

FIELD:
{field}

FIELD DEFINITION:
{definition}

RULES:
1. Accept only if the candidate itself contains direct evidence supporting
   the field.
2. Do not infer facts that are not explicitly present.
3. A keyword alone is NOT sufficient evidence.
4. Reject incidental references.
5. Reject generic or legal boilerplate when it does not establish the field.
6. Reject unrelated financial, accounting, administrative, or legal text.
7. For customers, require actual customer evidence; a business description
   or target-customer statement is insufficient.
8. For board_rights, require a specific governance/board right; an incidental
   Board reference is insufficient.
9. For adoption_usage, require concrete adoption/usage evidence; calculations
   or generic descriptions are insufficient.
10. Give the classification based only on the candidate text.

Return ONLY the requested structured JSON object.

CANDIDATE TEXT:
{candidate}
"""

def load_cases(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Expected B.2.2 benchmark object")

    cases = data.get("results")

    if not isinstance(cases, list):
        raise ValueError("B.2.2 benchmark has no results list")

    if len(cases) != 16:
        raise ValueError(
            f"Expected 16 frozen smoke cases, found {len(cases)}"
        )

    normalized = []

    for i, case in enumerate(cases, 1):
        field = case.get("field")
        candidate = case.get("candidate_text")
        expected = case.get("smoke_expected_label")

        if not isinstance(field, str):
            raise ValueError(f"Case {i}: missing field")

        if not isinstance(candidate, str):
            raise ValueError(f"Case {i}: missing candidate_text")

        if expected not in {"A", "R"}:
            raise ValueError(
                f"Case {i}: smoke_expected_label must be A or R, "
                f"got {expected!r}"
            )

        normalized.append({
            "index": i,
            "candidate_id": case.get("candidate_id"),
            "field": field,
            "candidate": candidate,
            "expected_label": expected,
            "challenge_type": case.get("smoke_challenge_type"),
            "signal": case.get("signal"),
            "source": case.get("source"),
            "extraction": case.get("extraction"),
        })

    return normalized, {
        "source_benchmark_version": (
            data.get("benchmark", {}).get("version")
            if isinstance(data.get("benchmark"), dict)
            else None
        ),
        "input_case_count": len(normalized),
    }


def call_openrouter(
    opener: urllib.request.OpenerDirector,
    api_key: str,
    prompt: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://investment-os.local",
        "X-Title": "Investment OS GPT-OSS Teacher Smoke",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "candidate_validation",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
        "provider": {
            "order": [PINNED_PROVIDER],
            "allow_fallbacks": ALLOW_FALLBACKS,
            "require_parameters": REQUIRE_PARAMETERS,
        },
        "reasoning": {
            "effort": REASONING_EFFORT,
        },
    }

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    started = time.perf_counter()

    try:
        with opener.open(request, timeout=180) as response:
            status_code = response.status
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        response_text = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return {
            "http_status": None,
            "latency_sec": time.perf_counter() - started,
            "error": f"request_exception:{type(exc).__name__}:{exc}",
            "contract_status": "HTTP_ERROR",
            "raw_response": None,
        }

    latency = time.perf_counter() - started

    result: dict[str, Any] = {
        "http_status": status_code,
        "latency_sec": latency,
        "error": None,
        "contract_status": None,
        "raw_response": None,
        "provider_actual": None,
        "provider_model_id": None,
        "finish_reason": None,
        "usage": None,
    }

    try:
        body = json.loads(response_text)
    except (TypeError, ValueError):
        body = None

    if status_code != 200:
        result["contract_status"] = "HTTP_ERROR"
        if isinstance(body, dict):
            result["error"] = body.get("error")
        else:
            result["error"] = response_text[:4000]
        return result

    if not isinstance(body, dict):
        result["contract_status"] = "RESPONSE_NOT_JSON"
        result["error"] = "response_body_not_json"
        return result

    result["usage"] = extract_usage(body)
    result["provider_actual"] = body.get("provider")
    result["provider_model_id"] = body.get("model")

    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            result["finish_reason"] = choice.get("finish_reason")
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    result["raw_response"] = content

    raw = result["raw_response"]

    if raw is None or not raw.strip():
        result["contract_status"] = "RESPONSE_EMPTY"
        result["error"] = "response_empty"
        if detect_budget_exhaustion(
            result["usage"],
            result["finish_reason"],
            raw,
        ):
            result["contract_status"] = "GENERATION_BUDGET_EXHAUSTED"
            result["error"] = "generation_budget_exhausted"
        return result

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        result["contract_status"] = "RESPONSE_NOT_JSON"
        result["error"] = f"response_not_json:{exc.msg}"
        if detect_budget_exhaustion(
            result["usage"],
            result["finish_reason"],
            raw,
        ):
            result["contract_status"] = "GENERATION_BUDGET_EXHAUSTED"
            result["error"] = "generation_budget_exhausted"
        return result

    valid, schema_error = validate_schema(parsed)
    if not valid:
        result["contract_status"] = "SCHEMA_INVALID"
        result["error"] = schema_error
        return result

    result["contract_status"] = "VALID"
    result["parsed"] = parsed
    return result


def run_case(
    opener: urllib.request.OpenerDirector,
    api_key: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    prompt = build_prompt(case["field"], case["candidate"])

    api_result = call_openrouter(
        opener=opener,
        api_key=api_key,
        prompt=prompt,
    )

    result = {
        "index": case["index"],
        "field": case["field"],
        "expected_label": case["expected_label"],
        "candidate": case["candidate"],
        "actual_label": None,
        "correct": None,
        "confidence": None,
        "reason": None,
        "contract_status": api_result.get("contract_status"),
        "error": api_result.get("error"),
        "http_status": api_result.get("http_status"),
        "provider_requested": PINNED_PROVIDER,
        "provider_actual": api_result.get("provider_actual"),
        "provider_model_id": api_result.get("provider_model_id"),
        "provider_match": (
            api_result.get("provider_actual") == PINNED_PROVIDER
            if api_result.get("provider_actual") is not None
            else None
        ),
        "finish_reason": api_result.get("finish_reason"),
        "latency_sec": api_result.get("latency_sec"),
        "usage": api_result.get("usage"),
        "raw_response": api_result.get("raw_response"),
    }

    parsed = api_result.get("parsed")
    if isinstance(parsed, dict):
        accepted = parsed["accepted"]
        result["actual_label"] = "A" if accepted else "R"
        result["correct"] = (
            result["actual_label"] == result["expected_label"]
        )
        result["confidence"] = parsed["confidence"]
        result["reason"] = parsed["reason"]

    return result


def evaluate(results: list[dict[str, Any]], wall_time: float) -> dict[str, Any]:
    total = len(results)

    valid = [
        r for r in results if r["contract_status"] == "VALID"
    ]

    correct = [
        r for r in valid if r["correct"] is True
    ]

    positives = [
        r for r in results if r["expected_label"] == "A"
    ]
    negatives = [
        r for r in results if r["expected_label"] == "R"
    ]

    positive_valid = [
        r for r in positives if r["contract_status"] == "VALID"
    ]
    negative_valid = [
        r for r in negatives if r["contract_status"] == "VALID"
    ]

    positive_correct = [
        r for r in positive_valid if r["correct"] is True
    ]
    negative_correct = [
        r for r in negative_valid if r["correct"] is True
    ]

    latencies = [
        safe_float(r["latency_sec"])
        for r in results
        if safe_float(r["latency_sec"]) is not None
    ]

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_reasoning_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    cost_seen = False

    for r in results:
        usage = r.get("usage") or {}

        for key, accumulator in (
            ("prompt_tokens", "prompt"),
            ("completion_tokens", "completion"),
            ("reasoning_tokens", "reasoning"),
            ("total_tokens", "total"),
        ):
            value = usage.get(key)
            if isinstance(value, int):
                if accumulator == "prompt":
                    total_prompt_tokens += value
                elif accumulator == "completion":
                    total_completion_tokens += value
                elif accumulator == "reasoning":
                    total_reasoning_tokens += value
                elif accumulator == "total":
                    total_tokens += value

        cost = usage.get("cost")
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
            cost_seen = True

    status_counts: dict[str, int] = {}
    for r in results:
        status = r["contract_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    provider_drift = [
        r for r in results
        if r["provider_match"] is False
    ]

    budget_exhausted = [
        r for r in results
        if r["contract_status"] == "GENERATION_BUDGET_EXHAUSTED"
    ]

    empty_count = status_counts.get("RESPONSE_EMPTY", 0)

    structured_rate = len(valid) / total if total else 0.0
    overall_accuracy = len(correct) / total if total else 0.0

    positive_accuracy = (
        len(positive_correct) / len(positives)
        if positives
        else 0.0
    )
    negative_accuracy = (
        len(negative_correct) / len(negatives)
        if negatives
        else 0.0
    )

    decision_contract = (
        structured_rate >= MIN_STRUCTURED_VALID
        and empty_count <= MAX_EMPTY
        and len(budget_exhausted) <= MAX_BUDGET_EXHAUSTED
        and len(provider_drift) <= MAX_PROVIDER_DRIFT
    )

    decision_semantic = (
        overall_accuracy >= MIN_OVERALL_ACCURACY
        and positive_accuracy >= MIN_POSITIVE_ACCURACY
        and negative_accuracy >= MIN_NEGATIVE_ACCURACY
    )

    overall_pass = decision_contract and decision_semantic

    projected_251_cost = None
    if cost_seen and total:
        projected_251_cost = total_cost / total * 251

    return {
        "total": total,
        "structured_valid": len(valid),
        "structured_valid_rate": structured_rate,
        "correct": len(correct),
        "overall_accuracy": overall_accuracy,
        "positive": {
            "total": len(positives),
            "correct": len(positive_correct),
            "accuracy": positive_accuracy,
        },
        "negative": {
            "total": len(negatives),
            "correct": len(negative_correct),
            "accuracy": negative_accuracy,
        },
        "contract_status_counts": status_counts,
        "empty": empty_count,
        "budget_exhausted": len(budget_exhausted),
        "provider_drift": len(provider_drift),
        "latency": {
            "total_wall_sec": wall_time,
            "average_sec": (
                statistics.mean(latencies) if latencies else None
            ),
            "median_sec": (
                statistics.median(latencies) if latencies else None
            ),
            "p95_sec": percentile(latencies, 0.95),
            "min_sec": min(latencies) if latencies else None,
            "max_sec": max(latencies) if latencies else None,
        },
        "tokens": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "reasoning_tokens": total_reasoning_tokens,
            "total_tokens": total_tokens,
        },
        "cost": {
            "total_usd": total_cost if cost_seen else None,
            "average_usd": (
                total_cost / total if cost_seen and total else None
            ),
            "projected_251_usd": projected_251_cost,
        },
        "gates": {
            "contract_pass": decision_contract,
            "semantic_pass": decision_semantic,
            "structured_valid_pass": (
                structured_rate >= MIN_STRUCTURED_VALID
            ),
            "overall_accuracy_pass": (
                overall_accuracy >= MIN_OVERALL_ACCURACY
            ),
            "positive_accuracy_pass": (
                positive_accuracy >= MIN_POSITIVE_ACCURACY
            ),
            "negative_accuracy_pass": (
                negative_accuracy >= MIN_NEGATIVE_ACCURACY
            ),
            "provider_drift_pass": (
                len(provider_drift) <= MAX_PROVIDER_DRIFT
            ),
            "budget_pass": (
                len(budget_exhausted) <= MAX_BUDGET_EXHAUSTED
            ),
            "overall_pass": overall_pass,
        },
        "decision": (
            "PASS"
            if overall_pass
            else "CONTRACT_FAIL"
            if not decision_contract
            else "SEMANTIC_FAIL"
        ),
        "next_step": (
            "RUN_251_CANDIDATE_TEACHER_BENCHMARK"
            if overall_pass
            else "DO_NOT_RUN_251_YET"
        ),
    }


def print_case(result: dict[str, Any], position: int) -> None:
    actual = result["actual_label"]
    expected = result["expected_label"]
    valid = result["contract_status"] == "VALID"

    print(
        f"[{position:02d}/{EXPECTED_CASE_COUNT}] "
        f"{result['field']} "
        f"expected={expected} "
        f"actual={actual} "
        f"valid={'yes' if valid else 'no'} "
        f"status={result['contract_status']} "
        f"provider={result['provider_actual']} "
        f"{result['latency_sec']:.2f}s"
    )

    if not valid:
        print(f"          error={result['error']}")


def main() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return 2

    cases, input_metadata = load_cases(INPUT_PATH)

    output_parent = Path(OUTPUT_PATH).parent
    output_parent.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("B.3-GPTOSS20B-V2 controlled teacher smoke")
    print(f"Input                    : {INPUT_PATH}")
    print(f"Output                   : {OUTPUT_PATH}")
    print(f"Model                    : {MODEL}")
    print(f"Provider requested       : {PINNED_PROVIDER}")
    print(f"Provider pinned          : yes")
    print(f"Provider fallback        : no")
    print(f"Concurrency              : {CONCURRENCY}")
    print(f"Reasoning effort         : {REASONING_EFFORT}")
    print(f"Max tokens               : {MAX_TOKENS}")
    print(f"Temperature              : {TEMPERATURE}")
    print(f"Response format          : strict json_schema")
    print(f"Provider require params  : {REQUIRE_PARAMETERS}")
    print(f"Production path          : NOT MODIFIED")
    print("=" * 100)

    results: list[dict[str, Any]] = []
    wall_started = time.perf_counter()

    opener = urllib.request.build_opener()

    for position, case in enumerate(cases, start=1):
        result = run_case(opener, api_key, case)
        results.append(result)
        print_case(result, position)

    wall_time = time.perf_counter() - wall_started

    summary = evaluate(results, wall_time)

    # Explicit provider verification.
    actual_providers = sorted(
        {
            r["provider_actual"]
            for r in results
            if r["provider_actual"] is not None
        }
    )

    output = {
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_type": BENCHMARK_TYPE,
        "model": MODEL,
        "provider_requested": PINNED_PROVIDER,
        "provider_pinned": True,
        "allow_fallbacks": ALLOW_FALLBACKS,
        "require_parameters": REQUIRE_PARAMETERS,
        "actual_providers": actual_providers,
        "concurrency": CONCURRENCY,
        "reasoning_effort": REASONING_EFFORT,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "response_format": "strict_json_schema",
        "input": {
            "path": INPUT_PATH,
            "case_count": len(cases),
            "expected_case_count": EXPECTED_CASE_COUNT,
            "source_benchmark_version": input_metadata.get(
                "source_benchmark_version"
            ),
            "expected_source_benchmark": EXPECTED_SOURCE_BENCHMARK,
        },
        "acceptance_gates": {
            "min_structured_valid": MIN_STRUCTURED_VALID,
            "min_overall_accuracy": MIN_OVERALL_ACCURACY,
            "min_positive_accuracy": MIN_POSITIVE_ACCURACY,
            "min_negative_accuracy": MIN_NEGATIVE_ACCURACY,
            "max_empty": MAX_EMPTY,
            "max_budget_exhausted": MAX_BUDGET_EXHAUSTED,
            "max_provider_drift": MAX_PROVIDER_DRIFT,
        },
        "summary": summary,
        "production_path_modified": False,
        "results": results,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(
        f"Structured valid : "
        f"{summary['structured_valid']}/{summary['total']} "
        f"({summary['structured_valid_rate']:.1%})"
    )
    print(
        f"Correct          : "
        f"{summary['correct']}/{summary['total']} "
        f"({summary['overall_accuracy']:.1%})"
    )
    print(
        f"Positive accuracy: "
        f"{summary['positive']['correct']}/{summary['positive']['total']} "
        f"({summary['positive']['accuracy']:.1%})"
    )
    print(
        f"Negative accuracy: "
        f"{summary['negative']['correct']}/{summary['negative']['total']} "
        f"({summary['negative']['accuracy']:.1%})"
    )
    print(f"Provider drift   : {summary['provider_drift']}")
    print(f"Empty responses  : {summary['empty']}")
    print(f"Budget exhausted : {summary['budget_exhausted']}")
    print(
        f"Avg latency      : "
        f"{summary['latency']['average_sec']:.3f}s"
        if summary["latency"]["average_sec"] is not None
        else "Avg latency      : n/a"
    )
    print(
        f"P95 latency      : "
        f"{summary['latency']['p95_sec']:.3f}s"
        if summary["latency"]["p95_sec"] is not None
        else "P95 latency      : n/a"
    )
    print(f"Total wall       : {wall_time:.3f}s")

    if summary["cost"]["total_usd"] is not None:
        print(f"Total cost       : ${summary['cost']['total_usd']:.6f}")
        print(
            f"Projected 251    : "
            f"${summary['cost']['projected_251_usd']:.6f}"
        )

    print(f"Decision          : {summary['decision']}")
    print(f"Next step         : {summary['next_step']}")
    print(f"Output            : {OUTPUT_PATH}")
    print("=" * 100)

    return 0 if summary["gates"]["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
