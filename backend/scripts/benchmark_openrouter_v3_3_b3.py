#!/usr/bin/env python3
"""
V3.3-B.3 — 251-candidate GPT-OSS-20B / CoreWeave teacher benchmark.

EXPERIMENTAL / OBSERVATIONAL ONLY.

This benchmark:
  - verifies the actual flat V3.3-B.3-V2 controlled teacher smoke artifact
  - requires smoke summary.decision == PASS
  - requires the exact configuration that passed the smoke
  - pins OpenRouter routing to CoreWeave
  - disables provider fallback
  - evaluates the frozen 251-candidate V3.3-A.1.2 population
  - records provider/contract/retry/latency/usage information
  - NEVER writes or replaces dimension_evidence.json

The 251-candidate run has no gold labels. Therefore accepted/rejected
distribution is observational; no semantic accuracy is claimed for it.

Required:
  AUTHORIZE_FULL_B3=true              # required for API execution
  OPENROUTER_API_KEY                   # required only for API execution

Preflight only:
  PREFLIGHT_ONLY=true                  # validates smoke + 1167->251 population; no API calls

Optional:
  INPUT_JSON
  SMOKE_JSON
  OUTPUT_JSON
  OPENROUTER_TIMEOUT_SEC
  OPENROUTER_MAX_RETRIES
  EXPECTED_CANDIDATES
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


# ---------------------------------------------------------------------------
# Frozen benchmark configuration
# ---------------------------------------------------------------------------

BENCHMARK_VERSION = "V3.3-B.3-251-GPTOSS20B-COREWEAVE"
PROMPT_VERSION = "candidate-semantic-validation-v5-openrouter"

SOURCE_BENCHMARK_VERSION = "V3.3-A.1.2"
SOURCE_GATE_VERSION = "candidate-quality-gate-v1.3"
SOURCE_RAW_CANDIDATES = 1167
EXPECTED_GATED_CANDIDATES = 251

MODEL = "openai/gpt-oss-20b"
PROVIDER = "CoreWeave"

API_URL = "https://openrouter.ai/api/v1/chat/completions"

CONCURRENCY = 1
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 1024
REASONING_EFFORT = "medium"

TIMEOUT_SEC = int(
    os.getenv("OPENROUTER_TIMEOUT_SEC", "120")
)
MAX_RETRIES = int(
    os.getenv("OPENROUTER_MAX_RETRIES", "3")
)
EXPECTED_CANDIDATES = int(os.getenv("EXPECTED_CANDIDATES", "251"))
if EXPECTED_CANDIDATES != EXPECTED_GATED_CANDIDATES:
    raise ValueError(
        "Frozen V3.3-B.3 benchmark requires EXPECTED_CANDIDATES=251; "
        f"got {EXPECTED_CANDIDATES}"
    )

DEFAULT_INPUT = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_gate.json"
)

DEFAULT_SMOKE = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_openrouter_v3_3_b3_gptoss20b_teacher_v2_smoke.json"
)

DEFAULT_OUTPUT = (
    "/opt/investment-os/generated/restomart/"
    "benchmark_openrouter_v3_3_b3_gptoss20b_coreweave_251.json"
)

TRANSIENT_HTTP_CODES = {
    408,
    409,
    425,
    429,
    500,
    502,
    503,
    504,
}


# ---------------------------------------------------------------------------
# Semantic definitions
# ---------------------------------------------------------------------------

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


def build_prompt(
    field: str,
    candidate_text: str,
) -> list[dict[str, str]]:
    definition = FIELD_DEFINITIONS.get(
        field,
        FIELD_DEFINITIONS["generic"],
    )

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

    return [
        {
            "role": "system",
            "content": system,
        },
        {
            "role": "user",
            "content": user,
        },
    ]


# ---------------------------------------------------------------------------
# Candidate loading
# ---------------------------------------------------------------------------

def load_gate_population(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Load the V3.3-A.1.2 gate artifact and derive its 251 passed records.

    The actual gate artifact schema is:
      benchmark_version = V3.3-A.1.2
      gate_version      = candidate-quality-gate-v1.3
      candidates        = 1167 records

    A production candidate is represented by gate.passed == True and its
    evidence text is stored in record['text'] (not candidate_text).
    """
    if not path.exists():
        raise ValueError(f"Gate input not found: {path}")

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not parse gate input: {exc}") from exc

    if not isinstance(source, dict):
        raise ValueError("Gate input root must be a JSON object.")

    if source.get("benchmark_version") != SOURCE_BENCHMARK_VERSION:
        raise ValueError(
            "Input benchmark_version mismatch: "
            f"{source.get('benchmark_version')!r} != "
            f"{SOURCE_BENCHMARK_VERSION!r}"
        )

    if source.get("gate_version") != SOURCE_GATE_VERSION:
        raise ValueError(
            "Input gate_version mismatch: "
            f"{source.get('gate_version')!r} != "
            f"{SOURCE_GATE_VERSION!r}"
        )

    if source.get("benchmark_type") != "deterministic_candidate_quality_gate":
        raise ValueError(
            "Input benchmark_type is not "
            "'deterministic_candidate_quality_gate'."
        )

    if source.get("observational") is not True:
        raise ValueError("Gate artifact is not marked observational.")

    if source.get("production_pipeline_modified") is not False:
        raise ValueError("Gate artifact indicates production modification.")

    if source.get("llm_inference_used") is not False:
        raise ValueError("Gate artifact indicates LLM inference was used.")

    raw = source.get("candidates")
    if not isinstance(raw, list):
        raise ValueError("Gate artifact 'candidates' must be a list.")

    if len(raw) != SOURCE_RAW_CANDIDATES:
        raise ValueError(
            "Raw candidate count mismatch: "
            f"{len(raw)} != {SOURCE_RAW_CANDIDATES}"
        )

    passed: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(raw):
        if not isinstance(record, dict):
            raise ValueError(f"Candidate {index} is not an object.")

        required = {
            "candidate_id", "dimension", "field", "text", "gate"
        }
        missing = sorted(required - set(record))
        if missing:
            raise ValueError(
                f"Candidate {index} missing required keys: {missing}"
            )

        candidate_id = str(record["candidate_id"]).strip()
        if not candidate_id:
            raise ValueError(f"Candidate {index} has empty candidate_id.")
        if candidate_id in seen_ids:
            raise ValueError(
                f"Duplicate candidate_id in gate artifact: {candidate_id}"
            )
        seen_ids.add(candidate_id)

        gate = record["gate"]
        if not isinstance(gate, dict):
            raise ValueError(
                f"Candidate {candidate_id} gate must be an object."
            )

        if gate.get("passed") is True:
            dimension = str(record.get("dimension", "")).strip()
            field = str(record.get("field", "")).strip()
            text = str(record.get("text", "")).strip()

            if not dimension or not field or not text:
                raise ValueError(
                    f"Passed candidate {candidate_id} is incomplete."
                )

            passed.append({
                "candidate_id": candidate_id,
                "dimension": dimension,
                "field": field,
                "candidate_text": text,
                "signal": record.get("signal", ""),
                "source": {
                    "source_id": record.get("source_id"),
                    "source_sha256": record.get("source_sha256"),
                    "source_path": record.get("source_path"),
                    "source_type": record.get("source_type"),
                    "source_category": record.get("source_category"),
                    "source_authority": record.get("source_authority"),
                    "title": record.get("title"),
                    "page_count": record.get("page_count"),
                },
                "extraction": {
                    "extraction_id": record.get("extraction_id"),
                    "extraction_method": record.get("extraction_method"),
                    "processor_name": record.get("processor_name"),
                    "segment_index": record.get("segment_index"),
                    "segment_metadata": record.get("segment_metadata", {}),
                },
                "document_kind": record.get("document_kind"),
                "signal_start": record.get("signal_start"),
                "signal_end": record.get("signal_end"),
                "gate": gate,
            })

    if len(passed) != EXPECTED_CANDIDATES:
        raise ValueError(
            "Gated candidate count mismatch: "
            f"{len(passed)} != {EXPECTED_CANDIDATES}. "
            "The V3.3-A.1.2 artifact does not produce the expected "
            "251-candidate population."
        )

    passed_ids = [c["candidate_id"] for c in passed]
    if len(passed_ids) != len(set(passed_ids)):
        raise ValueError("Passed candidate IDs are not unique.")

    return source, passed, "candidates[gate.passed=true]"


def validate_candidate_population(
    source: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> None:
    """Final fail-closed validation of the derived 251 population."""
    if source.get("benchmark_version") != SOURCE_BENCHMARK_VERSION:
        raise ValueError("Source benchmark provenance validation failed.")
    if source.get("gate_version") != SOURCE_GATE_VERSION:
        raise ValueError("Source gate provenance validation failed.")
    if len(source.get("candidates", [])) != SOURCE_RAW_CANDIDATES:
        raise ValueError("Raw source candidate count validation failed.")
    if len(candidates) != EXPECTED_CANDIDATES:
        raise ValueError(
            f"Candidate count mismatch: {len(candidates)} != "
            f"{EXPECTED_CANDIDATES}"
        )

    ids = [c["candidate_id"] for c in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate population contains duplicate IDs.")

    for candidate in candidates:
        if not candidate["dimension"]:
            raise ValueError(f"Empty dimension: {candidate['candidate_id']}")
        if not candidate["field"]:
            raise ValueError(f"Empty field: {candidate['candidate_id']}")
        if not candidate["candidate_text"].strip():
            raise ValueError(
                f"Empty candidate text: {candidate['candidate_id']}"
            )
        if candidate.get("gate", {}).get("passed") is not True:
            raise ValueError(
                f"Non-passed record entered population: "
                f"{candidate['candidate_id']}"
            )


# ---------------------------------------------------------------------------
# OpenRouter request
# ---------------------------------------------------------------------------

def request_openrouter(
    candidate: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    body = {
        "model": MODEL,
        "messages": build_prompt(
            candidate["field"],
            candidate["candidate_text"],
        ),
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "reasoning": {
            "effort": REASONING_EFFORT,
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": (
                    "candidate_semantic_validation"
                ),
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "accepted": {
                            "type": "boolean"
                        },
                        "reason": {
                            "type": "string"
                        },
                    },
                    "required": [
                        "accepted",
                        "reason",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "provider": {
            "order": [PROVIDER],
            "allow_fallbacks": False,
            "require_parameters": True,
        },
    }

    payload = json.dumps(
        body
    ).encode("utf-8")

    headers = {
        "Authorization": (
            f"Bearer {api_key}"
        ),
        "Content-Type": (
            "application/json"
        ),
        "Accept": (
            "application/json"
        ),
        "HTTP-Referer": (
            "https://openrouter.ai/"
        ),
        "X-Title": (
            "Investment OS V3.3-B.3 "
            "GPT-OSS-20B Teacher Benchmark"
        ),
    }

    started = time.perf_counter()
    attempts = 0
    retry_count = 0
    last_error = ""
    last_http_status: int | None = None

    while attempts < MAX_RETRIES:
        attempts += 1

        try:
            request = urllib.request.Request(
                API_URL,
                data=payload,
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT_SEC,
            ) as response:
                raw = response.read().decode(
                    "utf-8"
                )
                http_status = response.status

            last_http_status = http_status
            elapsed = (
                time.perf_counter()
                - started
            )

            data = json.loads(raw)
            choices = data.get(
                "choices"
            )

            if not choices:
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": "",
                    "latency_sec": elapsed,
                    "error": (
                        "response_no_choices"
                    ),
                    "http_status": http_status,
                    "attempt_count": attempts,
                    "retry_count": retry_count,
                    "provider_requested": PROVIDER,
                    "provider_actual": data.get(
                        "provider"
                    ),
                    "provider_match": False,
                    "model_id": data.get(
                        "model"
                    ),
                    "finish_reason": None,
                    "usage": data.get(
                        "usage",
                        {},
                    ),
                    "raw_api_response": data,
                }

            choice = choices[0]
            message = choice.get(
                "message",
                {},
            )

            content = message.get(
                "content",
                "",
            )

            provider_actual = data.get(
                "provider"
            )
            model_id = data.get(
                "model"
            )
            finish_reason = choice.get(
                "finish_reason"
            )

            provider_match = (
                provider_actual == PROVIDER
            )

            if (
                not isinstance(
                    content,
                    str,
                )
                or not content.strip()
            ):
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": (
                        content
                        if isinstance(
                            content,
                            str,
                        )
                        else ""
                    ),
                    "latency_sec": elapsed,
                    "error": (
                        "response_empty"
                    ),
                    "http_status": http_status,
                    "attempt_count": attempts,
                    "retry_count": retry_count,
                    "provider_requested": PROVIDER,
                    "provider_actual": provider_actual,
                    "provider_match": provider_match,
                    "model_id": model_id,
                    "finish_reason": finish_reason,
                    "usage": data.get(
                        "usage",
                        {},
                    ),
                    "raw_api_response": data,
                }

            try:
                parsed = json.loads(
                    content
                )
            except json.JSONDecodeError as exc:
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": content,
                    "latency_sec": elapsed,
                    "error": (
                        "response_not_json: "
                        f"{exc}"
                    ),
                    "http_status": http_status,
                    "attempt_count": attempts,
                    "retry_count": retry_count,
                    "provider_requested": PROVIDER,
                    "provider_actual": provider_actual,
                    "provider_match": provider_match,
                    "model_id": model_id,
                    "finish_reason": finish_reason,
                    "usage": data.get(
                        "usage",
                        {},
                    ),
                    "raw_api_response": data,
                }

            valid = (
                isinstance(parsed, dict)
                and set(parsed.keys())
                == {
                    "accepted",
                    "reason",
                }
                and isinstance(
                    parsed["accepted"],
                    bool,
                )
                and isinstance(
                    parsed["reason"],
                    str,
                )
            )

            if not valid:
                return {
                    "valid": False,
                    "accepted": None,
                    "reason": "",
                    "raw_response": content,
                    "latency_sec": elapsed,
                    "error": (
                        "schema_validation_failed"
                    ),
                    "http_status": http_status,
                    "attempt_count": attempts,
                    "retry_count": retry_count,
                    "provider_requested": PROVIDER,
                    "provider_actual": provider_actual,
                    "provider_match": provider_match,
                    "model_id": model_id,
                    "finish_reason": finish_reason,
                    "usage": data.get(
                        "usage",
                        {},
                    ),
                    "raw_api_response": data,
                }

            return {
                "valid": True,
                "accepted": parsed[
                    "accepted"
                ],
                "reason": parsed[
                    "reason"
                ],
                "raw_response": content,
                "latency_sec": elapsed,
                "error": "",
                "http_status": http_status,
                "attempt_count": attempts,
                "retry_count": retry_count,
                "provider_requested": PROVIDER,
                "provider_actual": provider_actual,
                "provider_match": provider_match,
                "model_id": model_id,
                "finish_reason": finish_reason,
                "usage": data.get(
                    "usage",
                    {},
                ),
                "raw_api_response": data,
            }

        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            last_http_status = exc.code
            last_error = (
                f"http_{exc.code}: "
                f"{body_text[:2000]}"
            )

            if (
                exc.code
                not in TRANSIENT_HTTP_CODES
            ):
                break

        except Exception as exc:
            last_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        if attempts < MAX_RETRIES:
            retry_count += 1
            time.sleep(
                min(
                    2 ** (attempts - 1),
                    8,
                )
            )

    return {
        "valid": False,
        "accepted": None,
        "reason": "",
        "raw_response": "",
        "latency_sec": (
            time.perf_counter()
            - started
        ),
        "error": (
            last_error
            or "request_failed"
        ),
        "http_status": last_http_status,
        "attempt_count": attempts,
        "retry_count": retry_count,
        "provider_requested": PROVIDER,
        "provider_actual": None,
        "provider_match": False,
        "model_id": None,
        "finish_reason": None,
        "usage": {},
        "raw_api_response": {},
    }


# ---------------------------------------------------------------------------
# Smoke validation — matches the ACTUAL V3.3-B.3-V2 artifact schema
# ---------------------------------------------------------------------------

def verify_smoke(
    smoke_path: Path,
) -> dict[str, Any]:
    if not smoke_path.exists():
        raise ValueError(
            "Required controlled teacher smoke artifact "
            f"not found: {smoke_path}"
        )

    smoke = json.loads(
        smoke_path.read_text(
            encoding="utf-8"
        )
    )

    if smoke.get(
        "benchmark_version"
    ) != "V3.3-B.3-V2":
        raise ValueError(
            "Smoke benchmark_version mismatch: "
            f"{smoke.get('benchmark_version')!r}"
        )

    if smoke.get(
        "benchmark_type"
    ) != "controlled_teacher_smoke":
        raise ValueError(
            "Smoke benchmark_type mismatch: "
            f"{smoke.get('benchmark_type')!r}"
        )

    if smoke.get(
        "model"
    ) != MODEL:
        raise ValueError(
            "Smoke model mismatch: "
            f"{smoke.get('model')!r} != {MODEL!r}"
        )

    if smoke.get(
        "provider_requested"
    ) != PROVIDER:
        raise ValueError(
            "Smoke provider mismatch: "
            f"{smoke.get('provider_requested')!r} "
            f"!= {PROVIDER!r}"
        )

    if smoke.get(
        "provider_pinned"
    ) is not True:
        raise ValueError(
            "Smoke provider_pinned is not True."
        )

    if smoke.get(
        "allow_fallbacks"
    ) is not False:
        raise ValueError(
            "Smoke allow_fallbacks is not False."
        )

    if smoke.get(
        "require_parameters"
    ) is not True:
        raise ValueError(
            "Smoke require_parameters is not True."
        )

    if smoke.get(
        "concurrency"
    ) != CONCURRENCY:
        raise ValueError(
            "Smoke concurrency mismatch: "
            f"{smoke.get('concurrency')} "
            f"!= {CONCURRENCY}"
        )

    if smoke.get(
        "reasoning_effort"
    ) != REASONING_EFFORT:
        raise ValueError(
            "Smoke reasoning_effort mismatch: "
            f"{smoke.get('reasoning_effort')!r}"
        )

    if smoke.get(
        "temperature"
    ) != TEMPERATURE:
        raise ValueError(
            "Smoke temperature mismatch."
        )

    if smoke.get(
        "top_p"
    ) != TOP_P:
        raise ValueError(
            "Smoke top_p mismatch."
        )

    if smoke.get(
        "max_tokens"
    ) != MAX_TOKENS:
        raise ValueError(
            "Smoke max_tokens mismatch."
        )

    if smoke.get(
        "response_format"
    ) != "strict_json_schema":
        raise ValueError(
            "Smoke response_format is not "
            "strict_json_schema."
        )

    if smoke.get(
        "production_path_modified"
    ) is not False:
        raise ValueError(
            "Smoke indicates production path modification."
        )

    actual_providers = smoke.get(
        "actual_providers"
    )

    if actual_providers != [PROVIDER]:
        raise ValueError(
            "Smoke actual_providers mismatch: "
            f"{actual_providers!r}"
        )

    summary = smoke.get(
        "summary"
    )

    if not isinstance(
        summary,
        dict,
    ):
        raise ValueError(
            "Smoke summary is missing or malformed."
        )

    if summary.get(
        "decision"
    ) != "PASS":
        raise ValueError(
            "Full B.3 is blocked because the controlled "
            "teacher smoke decision is not PASS: "
            f"{summary.get('decision')!r}"
        )

    if summary.get(
        "total"
    ) != 16:
        raise ValueError(
            "Smoke total is not 16."
        )

    if summary.get(
        "structured_valid"
    ) != 16:
        raise ValueError(
            "Smoke structured_valid is not 16/16."
        )

    if summary.get(
        "correct"
    ) != 16:
        raise ValueError(
            "Smoke correct is not 16/16."
        )

    positive = summary.get("positive")

    if not isinstance(positive, dict):
        raise ValueError(
            "Smoke positive result has unexpected schema: "
            f"{positive!r}"
        )

    if (
        positive.get("total") != 8
        or positive.get("correct") != 8
    ):
        raise ValueError(
            "Smoke positive result is not 8/8: "
            f"{positive!r}"
        )

    negative = summary.get("negative")

    if not isinstance(negative, dict):
        raise ValueError(
            "Smoke negative result has unexpected schema: "
            f"{negative!r}"
        )

    if (
        negative.get("total") != 8
        or negative.get("correct") != 8
    ):
        raise ValueError(
            "Smoke negative result is not 8/8: "
            f"{negative!r}"
        )


    if summary.get(
        "empty"
    ) != 0:
        raise ValueError(
            "Smoke contains empty responses."
        )

    if summary.get(
        "budget_exhausted"
    ) != 0:
        raise ValueError(
            "Smoke contains budget-exhausted responses."
        )

    if summary.get(
        "provider_drift"
    ) != 0:
        raise ValueError(
            "Smoke contains provider drift."
        )

    input_info = smoke.get(
        "input"
    )

    if not isinstance(
        input_info,
        dict,
    ):
        raise ValueError(
            "Smoke input metadata is missing or malformed."
        )

    if input_info.get(
        "case_count"
    ) != 16:
        raise ValueError(
            "Smoke input case_count is not 16."
        )

    # The actual passing smoke is derived from the frozen V3.3-B.2.2
    # 16-case boundary set. It intentionally does not claim the
    # V3.3-A.1.2 population provenance.
    if input_info.get("expected_source_benchmark") != "V3.3-B.2.2":
        raise ValueError(
            "Smoke expected_source_benchmark mismatch: "
            f"{input_info.get('expected_source_benchmark')!r} "
            "!= 'V3.3-B.2.2'"
        )

    if input_info.get("source_benchmark_version") is not None:
        raise ValueError(
            "Unexpected smoke source_benchmark_version: "
            f"{input_info.get('source_benchmark_version')!r}"
        )

    return smoke


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def summarize_usage(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    cost_records = 0

    for result in results:
        usage = result["model"].get(
            "usage",
            {},
        )

        prompt_tokens += int(
            usage.get(
                "prompt_tokens"
            )
            or usage.get(
                "input_tokens"
            )
            or 0
        )

        completion_tokens += int(
            usage.get(
                "completion_tokens"
            )
            or usage.get(
                "output_tokens"
            )
            or 0
        )

        total_tokens += int(
            usage.get(
                "total_tokens"
            )
            or 0
        )

        cost = usage.get(
            "cost"
        )

        if isinstance(
            cost,
            (int, float),
        ):
            total_cost += float(cost)
            cost_records += 1

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "reported_cost_usd": round(
            total_cost,
            8,
        ),
        "cost_records": cost_records,
    }


def build_stats(
    results: list[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, int]]:
    stats: dict[
        str,
        dict[str, int],
    ] = {}

    for result in results:
        value = (
            result.get(key)
            or "unknown"
        )

        entry = stats.setdefault(
            value,
            {
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "invalid": 0,
            },
        )

        entry["total"] += 1

        if result["actual_label"] == "A":
            entry["accepted"] += 1
        elif result["actual_label"] == "R":
            entry["rejected"] += 1
        else:
            entry["invalid"] += 1

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    preflight_only = os.getenv("PREFLIGHT_ONLY", "").lower() == "true"

    input_path = Path(
        os.getenv(
            "INPUT_JSON",
            DEFAULT_INPUT,
        )
    )

    smoke_path = Path(
        os.getenv(
            "SMOKE_JSON",
            DEFAULT_SMOKE,
        )
    )

    output_path = Path(
        os.getenv(
            "OUTPUT_JSON",
            DEFAULT_OUTPUT,
        )
    )

    try:
        smoke = verify_smoke(
            smoke_path
        )

        source, candidates, selected_path = (
            load_gate_population(
                input_path
            )
        )

        validate_candidate_population(
            source,
            candidates,
        )

    except Exception as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    if preflight_only:
        print("PREFLIGHT VALIDATION PASSED")
        print(f"Input              : {input_path}")
        print(f"Smoke              : {smoke_path}")
        print(
            f"Population derivation: {SOURCE_RAW_CANDIDATES} raw -> "
            f"{len(candidates)} gate.passed=true"
        )
        print(f"Source benchmark   : {SOURCE_BENCHMARK_VERSION}")
        print(f"Source gate        : {SOURCE_GATE_VERSION}")
        print("API calls          : 0")
        print("Production path    : NOT MODIFIED")
        return 0

    if os.getenv("AUTHORIZE_FULL_B3", "").lower() != "true":
        print(
            "BLOCKED: set AUTHORIZE_FULL_B3=true for the 251-candidate API run.",
            file=sys.stderr,
        )
        return 2

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return 2

    print(
        "V3.3-B.3 251-CANDIDATE "
        "TEACHER BENCHMARK AUTHORIZED"
    )
    print(
        f"Input              : {input_path}"
    )
    print(
        f"Smoke              : {smoke_path}"
    )
    print(
        f"Candidate path     : {selected_path}"
    )
    print(
        f"Population derivation: {SOURCE_RAW_CANDIDATES} raw -> "
        f"{EXPECTED_CANDIDATES} gate.passed=true"
    )
    print(
        f"Source benchmark   : "
        f"{SOURCE_BENCHMARK_VERSION}"
    )
    print(
        f"Source gate        : "
        f"{SOURCE_GATE_VERSION}"
    )
    print(
        f"Candidates         : "
        f"{len(candidates)}"
    )
    print(
        f"Model              : {MODEL}"
    )
    print(
        f"Provider            : {PROVIDER}"
    )
    print(
        "Provider fallback   : disabled"
    )
    print(
        f"Reasoning          : "
        f"{REASONING_EFFORT}"
    )
    print(
        f"Max tokens         : {MAX_TOKENS}"
    )
    print(
        f"Concurrency        : {CONCURRENCY}"
    )
    print(
        "Production path    : NOT MODIFIED"
    )
    print()

    started = time.perf_counter()

    results: list[
        dict[str, Any] | None
    ] = [None] * len(candidates)

    def worker(
        item: tuple[int, dict[str, Any]],
    ):
        index, candidate = item

        response = request_openrouter(
            candidate,
            api_key,
        )

        actual = (
            "A"
            if response.get(
                "accepted"
            ) is True
            else "R"
            if response.get(
                "accepted"
            ) is False
            else None
        )

        return index, {
            **candidate,
            "actual_label": actual,
            "model": response,
        }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=CONCURRENCY
    ) as executor:

        futures = [
            executor.submit(
                worker,
                (index, candidate),
            )
            for index, candidate
            in enumerate(candidates)
        ]

        completed = 0

        for future in concurrent.futures.as_completed(
            futures
        ):
            index, result = future.result()

            results[index] = result
            completed += 1

            if (
                completed % 10 == 0
                or completed == len(candidates)
            ):
                print(
                    f"  processed "
                    f"{completed}/"
                    f"{len(candidates)}"
                )

    elapsed = (
        time.perf_counter()
        - started
    )

    final_results = [
        result
        for result in results
        if result is not None
    ]

    valid = sum(
        bool(
            result["model"]["valid"]
        )
        for result in final_results
    )

    invalid = (
        len(final_results)
        - valid
    )

    accepted = sum(
        result["actual_label"] == "A"
        for result in final_results
    )

    rejected = sum(
        result["actual_label"] == "R"
        for result in final_results
    )

    provider_matches = sum(
        result["model"].get(
            "provider_match"
        )
        is True
        for result in final_results
    )

    provider_actual_counts: dict[
        str, int
    ] = {}

    for result in final_results:
        provider_actual = (
            result["model"].get(
                "provider_actual"
            )
            or "unknown"
        )

        provider_actual_counts[
            provider_actual
        ] = (
            provider_actual_counts.get(
                provider_actual,
                0,
            )
            + 1
        )

    retry_count = sum(
        int(
            result["model"].get(
                "retry_count"
            )
            or 0
        )
        for result in final_results
    )

    error_counts: dict[str, int] = {}

    for result in final_results:
        error = result["model"].get(
            "error",
            "",
        )

        if error:
            error_key = error.split(
                ":",
                1,
            )[0]

            error_counts[error_key] = (
                error_counts.get(
                    error_key,
                    0,
                )
                + 1
            )

    finish_reason_counts: dict[
        str, int
    ] = {}

    for result in final_results:
        finish_reason = (
            result["model"].get(
                "finish_reason"
            )
            or "unknown"
        )

        finish_reason_counts[
            finish_reason
        ] = (
            finish_reason_counts.get(
                finish_reason,
                0,
            )
            + 1
        )

    latency_values = [
        float(
            result["model"][
                "latency_sec"
            ]
        )
        for result in final_results
    ]

    latency_sorted = sorted(
        latency_values
    )

    if latency_sorted:
        p95_index = min(
            len(latency_sorted) - 1,
            max(
                0,
                int(
                    0.95
                    * len(latency_sorted)
                )
                - 1,
            ),
        )

        p95_latency = (
            latency_sorted[p95_index]
        )
    else:
        p95_latency = 0.0

    usage_summary = summarize_usage(
        final_results
    )

    unique_ids = {
        result["candidate_id"]
        for result in final_results
    }

    output = {
        "benchmark": {
            "benchmark_version": (
                BENCHMARK_VERSION
            ),
            "prompt_version": (
                PROMPT_VERSION
            ),
            "benchmark_type": (
                "full_semantic_validation_teacher"
            ),
            "observational": True,
            "production_pipeline_modified": (
                False
            ),
            "candidate_generation_used": (
                False
            ),
            "llm_inference_used": True,
            "semantic_gate_only": True,
            "classification_mode": (
                "structured_binary"
            ),
            "context_mode": (
                "candidate_only"
            ),
            "authorized": True,
            "teacher_model": True,
            "gold_labels_available": False,
        },
        "startup": source.get(
            "startup",
            {},
        ),
        "input": {
            "path": str(input_path),
            "source_benchmark_version": (
                SOURCE_BENCHMARK_VERSION
            ),
            "source_gate_version": (
                SOURCE_GATE_VERSION
            ),
            "candidate_path": (
                selected_path
            ),
            "raw_candidate_count": SOURCE_RAW_CANDIDATES,
            "candidate_count": (
                len(final_results)
            ),
            "expected_candidate_count": (
                EXPECTED_CANDIDATES
            ),
            "candidate_ids_unique": (
                len(unique_ids)
                == len(final_results)
            ),
        },
        "smoke": {
            "path": str(smoke_path),
            "benchmark_version": (
                smoke.get(
                    "benchmark_version"
                )
            ),
            "benchmark_type": (
                smoke.get(
                    "benchmark_type"
                )
            ),
            "decision": (
                smoke.get(
                    "summary",
                    {},
                ).get("decision")
            ),
            "model": smoke.get(
                "model"
            ),
            "provider": smoke.get(
                "provider_requested"
            ),
            "overall_accuracy": (
                smoke.get(
                    "summary",
                    {},
                ).get(
                    "overall_accuracy"
                )
            ),
            "structured_valid": (
                smoke.get(
                    "summary",
                    {},
                ).get(
                    "structured_valid"
                )
            ),
            "positive": (
                smoke.get(
                    "summary",
                    {},
                ).get(
                    "positive"
                )
            ),
            "negative": (
                smoke.get(
                    "summary",
                    {},
                ).get(
                    "negative"
                )
            ),
        },
        "model": {
            "provider": "openrouter",
            "name": MODEL,
            "provider_requested": (
                PROVIDER
            ),
            "provider_pinned": True,
            "allow_fallbacks": False,
            "require_parameters": True,
            "endpoint": API_URL,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "reasoning_effort": (
                REASONING_EFFORT
            ),
            "max_tokens": MAX_TOKENS,
            "concurrency": CONCURRENCY,
            "timeout_sec": TIMEOUT_SEC,
            "max_retries": MAX_RETRIES,
            "response_format": (
                "strict_json_schema"
            ),
        },
        "population": {
            "expected": (
                EXPECTED_CANDIDATES
            ),
            "processed": (
                len(final_results)
            ),
            "valid": valid,
            "invalid": invalid,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_pct": (
                round(
                    100.0
                    * accepted
                    / len(final_results),
                    4,
                )
                if final_results
                else 0.0
            ),
            "provider_matches": (
                provider_matches
            ),
            "provider_match_pct": (
                round(
                    100.0
                    * provider_matches
                    / len(final_results),
                    4,
                )
                if final_results
                else 0.0
            ),
            "retry_count": (
                retry_count
            ),
            "provider_actual_counts": (
                provider_actual_counts
            ),
        },
        "timing": {
            "total_wall_sec": round(
                elapsed,
                4,
            ),
            "average_latency_sec": (
                round(
                    sum(latency_values)
                    / len(latency_values),
                    4,
                )
                if latency_values
                else 0.0
            ),
            "min_latency_sec": (
                round(
                    min(latency_values),
                    4,
                )
                if latency_values
                else 0.0
            ),
            "max_latency_sec": (
                round(
                    max(latency_values),
                    4,
                )
                if latency_values
                else 0.0
            ),
            "p95_latency_sec": round(
                p95_latency,
                4,
            ),
            "serial_inference_min": (
                round(
                    sum(latency_values)
                    / 60.0,
                    4,
                )
                if latency_values
                else 0.0
            ),
        },
        "usage": usage_summary,
        "finish_reason_counts": (
            finish_reason_counts
        ),
        "dimension_stats": build_stats(
            final_results,
            "dimension",
        ),
        "field_stats": build_stats(
            final_results,
            "field",
        ),
        "error_counts": error_counts,
        "quality_checks": {
            "raw_candidate_count_exact": (
                len(source.get("candidates", []))
                == SOURCE_RAW_CANDIDATES
            ),
            "candidate_count_exact": (
                len(final_results)
                == EXPECTED_CANDIDATES
            ),
            "all_candidates_processed": (
                len(final_results)
                == EXPECTED_CANDIDATES
            ),
            "candidate_ids_unique": (
                len(unique_ids)
                == len(final_results)
            ),
            "production_pipeline_modified": (
                False
            ),
            "provenance_owned_by_python": (
                True
            ),
            "dimension_field_owned_by_python": (
                True
            ),
            "candidate_text_owned_by_python": (
                True
            ),
            "smoke_gate_verified": True,
            "smoke_model_provider_match": (
                True
            ),
            "provider_pinned": True,
            "provider_fallback_disabled": (
                True
            ),
            "provider_drift": (
                provider_matches
                != len(final_results)
            ),
            "provider_drift_count": (
                len(final_results)
                - provider_matches
            ),
            "contract_valid_all": (
                valid
                == len(final_results)
            ),
            "no_gold_accuracy_claim": True,
            "canonical_dimension_evidence_written": (
                False
            ),
        },
        "results": final_results,
        "status": (
            "COMPLETE"
            if len(final_results)
            == EXPECTED_CANDIDATES
            else "INCOMPLETE"
        ),
        "full_benchmark_authorized": True,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "B.3 251-CANDIDATE "
        "TEACHER RESULT"
    )
    print(
        f"  processed          : "
        f"{len(final_results)}/"
        f"{EXPECTED_CANDIDATES}"
    )
    print(
        f"  structured valid   : "
        f"{valid}"
    )
    print(
        f"  accepted           : "
        f"{accepted}"
    )
    print(
        f"  rejected           : "
        f"{rejected}"
    )
    print(
        f"  provider matches   : "
        f"{provider_matches}"
    )
    print(
        f"  retries            : "
        f"{retry_count}"
    )
    print(
        f"  total wall         : "
        f"{elapsed:.2f}s"
    )
    print(
        f"  status             : "
        f"{output['status']}"
    )
    print(
        f"  output             : "
        f"{output_path}"
    )
    print()
    print(
        "NOTE: This benchmark is "
        "observational and does not "
        "replace dimension_evidence.json."
    )

    return (
        0
        if output["status"] == "COMPLETE"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(run())
