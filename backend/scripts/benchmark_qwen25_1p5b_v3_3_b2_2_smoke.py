#!/usr/bin/env python3
"""
V3.3-B.2 SMOKE — Qwen2.5-1.5B Semantic Validation Contract Check
================================================================

Purpose
-------
Validate the LLM output contract on 16 balanced semantic-boundary candidates before
running the full 251-candidate V3.3-B.2 benchmark.

This is a SEMANTIC BOUNDARY SMOKE.

Architecture
------------
V3.3-A.1.2 deterministic candidate quality gate
        |
        v
251 gated candidates
        |
        v
16 deterministic challenge candidates (8 positive / 8 trap)
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
- The smoke gate validates both the binary output contract and selected semantic boundary cases.
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

BENCHMARK_VERSION = "V3.3-B.2.2-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v4-field-specific-boundary-grammar"

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
    "benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json"
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
SMOKE_COUNT = 16

CONTEXT_MODE = "candidate_only"

BINARY_GRAMMAR_TEXT = 'root ::= "A" | "R"'

FIELD_GUIDANCE = {
    "cash_burn": {
        "definition": "cash consumed by the business over time, such as burn rate, operating cash outflow, cash consumption, or runway explicitly tied to burn.",
        "accept": "Accept only explicit cash-burn, cash-consumption, cash-outflow, burn-rate, or runway evidence.",
        "reject": "Reject working-capital balances, capital-turnover ratios, current/quick ratios, profitability alone, and generic financial statements."
    },
    "customers": {
        "definition": "actual customers, clients, accounts, or explicitly onboarded/served buyers.",
        "accept": "Accept actual customer/client/account counts, named customer relationships, onboarded/served customers, or explicit customer traction.",
        "reject": "Reject company descriptions, target customer segments, customer types, markets served in general, or product descriptions without actual customer evidence."
    },
    "adoption_usage": {
        "definition": "actual customer/product adoption or observed usage.",
        "accept": "Accept actual users, active users, customers using the product, deployed accounts, completed transactions/orders, utilization, repeat usage, or observed adoption.",
        "reject": "Reject break-even thresholds, projected/target orders, capacity, theoretical throughput, or financial metrics that merely contain the word orders."
    },
    "board_rights": {
        "definition": "an explicit right or entitlement concerning board appointment, nomination, representation, board seat, or observer status.",
        "accept": "Accept explicit rights to appoint/nominate a director, board seat, board representation, or board observer rights.",
        "reject": "Reject incidental references to the Board, Board approval/discretion, Board requirements, or generic corporate-law boilerplate."
    },
    "exit_liquidity": {
        "definition": "explicit mechanisms or conditions enabling investor/shareholder exit or liquidity.",
        "accept": "Accept explicit IPO/listing, sale/exit, liquidity event, transfer exit, tag-along, drag-along, put/call exit, or buyback provisions when they clearly establish an exit/liquidity mechanism.",
        "reject": "Reject generic references to shares, transfers, or buybacks unless the text clearly establishes an exit/liquidity mechanism."
    },
    "market_size": {
        "definition": "quantified or explicit addressable market size, TAM/SAM/SOM, or market opportunity magnitude.",
        "accept": "Accept quantified market size or explicit addressable/TAM/SAM/SOM opportunity.",
        "reject": "Reject generic statements that a market exists, market names, or target geographies without market magnitude."
    },
    "instrument": {
        "definition": "the security or financing instrument being issued or raised.",
        "accept": "Accept explicit identification of the financing security/instrument such as CCPS, CCD, equity shares, SAFE, note, or debt instrument in the fundraising context.",
        "reject": "Reject incidental mentions of securities or shares that do not identify the financing instrument for the transaction."
    },
    "gmv": {
        "definition": "gross merchandise value or transaction value generated through the business.",
        "accept": "Accept explicit GMV/gross merchandise value or clearly identified transaction value.",
        "reject": "Reject revenue, valuation, funding, or generic transaction language unless it is explicitly GMV/transaction value."
    },
    "growth": {
        "definition": "change or expansion in a business metric over time.",
        "accept": "Accept explicit historical or projected growth in revenue, GMV, customers, orders, users, or another business metric with a time/change relationship.",
        "reject": "Reject a single static metric or generic use of the word growth without a business metric/change relationship."
    },
    "founder_background": {
        "definition": "founder identity plus relevant prior experience, role, company, education, or domain background.",
        "accept": "Accept explicit founder experience, prior role/company, education, tenure, or domain background.",
        "reject": "Reject generic founder/legal boilerplate, signature/identity clauses, or mere use of the word founder without background."
    },
    "revenue": {
        "definition": "business revenue actually generated or explicitly projected.",
        "accept": "Accept explicit revenue amount, revenue history, revenue forecast, or revenue growth.",
        "reject": "Reject funding, valuation, GMV, capital, or income references that are not clearly business revenue."
    },
    "valuation": {
        "definition": "company valuation associated with the financing or transaction.",
        "accept": "Accept explicit pre-money, post-money, enterprise, or transaction valuation.",
        "reject": "Reject issue price, share capital, or funding amount without an explicit valuation."
    },
}

def get_field_guidance(field: str) -> dict[str, str]:
    return FIELD_GUIDANCE.get(
        field,
        {
            "definition": "the specific investment-analysis fact represented by this field.",
            "accept": "Accept only when the candidate itself explicitly states that fact.",
            "reject": "Reject related but indirect, incidental, generic, projected-without-context, or boilerplate references."
        },
    )


SYSTEM_PROMPT = """You are a strict semantic evidence validator for investment analysis.

FIELD:
{field}

FIELD DEFINITION:
{field_definition}

ACCEPTANCE TEST:
{acceptance_test}

REJECTION TEST:
{rejection_test}

CANDIDATE:
{candidate}

QUESTION:
Does the candidate itself explicitly support the specified field?

Decision standard:
- Evaluate the candidate text itself, not the signal keyword.
- Accept only when the candidate contains the actual fact represented by the field.
- A related concept is NOT sufficient.
- A keyword match is NOT sufficient.
- Do not infer facts that are missing.
- Do not use world knowledge to complete the candidate.
- Legal or accounting boilerplate is not evidence unless it directly establishes the field.
- A target, plan, capacity, threshold, or projection is not actual traction unless the field explicitly permits projected evidence.
- If the candidate is ambiguous, incidental, or insufficient, reject it.

Output contract:
- Return exactly one character.
- Output A if the candidate passes the acceptance test.
- Output R if the candidate fails the acceptance test.
- Do not output any other character, word, explanation, punctuation, or formatting.
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


def _text_lower(candidate: dict[str, Any]) -> str:
    return normalize(candidate.get("text", "")).lower()


# Stable false-positive traps observed in B.2.1.
KNOWN_TRAP_IDS = {
    "843cee73ec756754aa60b9b6": "cash_burn_accounting_ratio",
    "0a2df3215469e53175301f10": "board_rights_incidental_board_reference",
    "ebc0a72a67a3d1d5ed8126fd": "adoption_usage_break_even_threshold",
    "6ea618b66d5fb1423d359606": "customers_business_description",
}

TRAP_PATTERNS = {
    "cash_burn": [
        r"net capital turnover", r"capital turnover", r"working capital",
        r"current ratio", r"quick ratio", r"debt[- ]equity"
    ],
    "board_rights": [
        r"\bboard\b.*\brequire", r"\bboard\b.*\bmay\b",
        r"\bboard\b.*\bapproval", r"\bboard\b.*\bdiscretion"
    ],
    "adoption_usage": [
        r"breaks? even", r"break[- ]even", r"target .* orders",
        r"projected .* orders", r"orders/month", r"capacity"
    ],
    "customers": [
        r"b2b .* platform", r"target customer", r"target market",
        r"restaurant procurement platform", r"serving .* market"
    ],
}

POSITIVE_PATTERNS = {
    "cash_burn": [
        r"cash burn", r"burn rate", r"cash consumption",
        r"monthly cash outflow", r"cash runway"
    ],
    "board_rights": [
        r"appoint .* director", r"nominate .* director", r"board seat",
        r"board observer", r"board representation"
    ],
    "adoption_usage": [
        r"active users", r"users .* month", r"customers .* using",
        r"orders .* completed", r"orders .* last", r"adopted",
        r"onboarded .* customers", r"transactions .* month"
    ],
    "customers": [
        r"\b\d+\+? customers\b", r"\b\d+\+? clients\b",
        r"customers onboarded", r"customers served", r"named customers",
        r"paying customers"
    ],
    "market_size": [
        r"\$[\d,.]+[bm]?\+? .* market", r"addressable market",
        r"\btam\b", r"\bsam\b", r"\bsom\b"
    ],
    "instrument": [
        r"\bccps\b", r"\bccd\b", r"\bsafe\b", r"equity shares",
        r"convertible note", r"debt instrument"
    ],
    "valuation": [
        r"pre[- ]money valuation", r"post[- ]money valuation",
        r"valuation of", r"valued at"
    ],
    "gmv": [
        r"\bgmv\b", r"gross merchandise value"
    ],
    "growth": [
        r"revenue growth", r"gmv growth", r"customer growth",
        r"grew .* from .* to", r"growth to"
    ],
    "founder_background": [
        r"founder .* years", r"founder .* experience",
        r"prior to", r"previously", r"\d+\+? years .* experience"
    ],
    "revenue": [
        r"\brevenue\b.*(?:inr|rs\.?|₹|\$|\d)", r"(?:inr|rs\.?|₹|\$)\s*[\d,.]+ .* revenue"
    ],
}

def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def select_smoke_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Select a deterministic 16-case semantic boundary challenge set:
      - 8 deliberately strong positive candidates
      - 8 deliberately difficult false-positive/trap candidates

    Expected labels are diagnostic/manual-review expectations only. They are
    never supplied to the model and do not affect A/R inference.
    """
    by_id = {str(c.get("candidate_id")): c for c in candidates}
    ordered = sorted(candidates, key=smoke_selection_key)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    expected: dict[str, str] = {}
    challenge: dict[str, str] = {}

    def add(candidate, label: str, challenge_type: str) -> bool:
        cid = str(candidate.get("candidate_id"))
        if cid in selected_ids or len(selected) >= SMOKE_COUNT:
            return False
        selected.append(candidate)
        selected_ids.add(cid)
        expected[cid] = label
        challenge[cid] = challenge_type
        return True

    # First reserve the known B.2.1 false positives.
    for cid, reason in KNOWN_TRAP_IDS.items():
        candidate = by_id.get(cid)
        if candidate is not None:
            add(candidate, "R", f"known_b2_1_trap:{reason}")

    # Additional field-specific traps.
    trap_targets = [
        ("cash_burn", "R", "accounting_ratio_or_working_capital"),
        ("board_rights", "R", "incidental_board_reference"),
        ("adoption_usage", "R", "projection_threshold_or_capacity"),
        ("customers", "R", "segment_description_not_actual_customers"),
    ]
    for field, label, kind in trap_targets:
        if len(selected) >= SMOKE_COUNT:
            break
        for candidate in ordered:
            if str(candidate.get("candidate_id")) in selected_ids:
                continue
            if str(candidate.get("field")) != field:
                continue
            if _matches_any(_text_lower(candidate), TRAP_PATTERNS.get(field, [])):
                if add(candidate, label, kind):
                    break

    # Strong positive candidates across important fields.
    positive_fields = [
        "cash_burn", "board_rights", "adoption_usage", "customers",
        "market_size", "instrument", "valuation", "gmv",
        "growth", "founder_background", "revenue",
    ]
    for field in positive_fields:
        if len([x for x in selected if expected[str(x.get("candidate_id"))] == "A"]) >= 8:
            break
        for candidate in ordered:
            cid = str(candidate.get("candidate_id"))
            if cid in selected_ids:
                continue
            if str(candidate.get("field")) != field:
                continue
            text = _text_lower(candidate)
            if _matches_any(text, POSITIVE_PATTERNS.get(field, [])):
                add(candidate, "A", f"strong_positive:{field}")
                break

    # Fill any remaining positive slots from candidates with strong
    # field-specific lexical support, scoring exact field terms first.
    def positive_score(candidate):
        field = str(candidate.get("field", ""))
        text = _text_lower(candidate)
        patterns = POSITIVE_PATTERNS.get(field, [])
        return sum(bool(re.search(p, text, re.I | re.S)) for p in patterns)

    for candidate in sorted(ordered, key=lambda c: (-positive_score(c), smoke_selection_key(c))):
        if len([x for x in selected if expected[str(x.get("candidate_id"))] == "A"]) >= 8:
            break
        if str(candidate.get("candidate_id")) in selected_ids:
            continue
        if positive_score(candidate) > 0:
            add(candidate, "A", "strong_positive_fallback")

    # Fill remaining trap slots from field-specific trap patterns.
    for candidate in ordered:
        if len(selected) >= SMOKE_COUNT:
            break
        cid = str(candidate.get("candidate_id"))
        if cid in selected_ids:
            continue
        field = str(candidate.get("field", ""))
        text = _text_lower(candidate)
        if _matches_any(text, TRAP_PATTERNS.get(field, [])):
            add(candidate, "R", f"semantic_trap:{field}")

    if len(selected) != SMOKE_COUNT:
        raise RuntimeError(
            f"Unable to construct {SMOKE_COUNT}-case semantic boundary smoke; "
            f"constructed {len(selected)}"
        )

    positive_count = sum(expected[str(c.get("candidate_id"))] == "A" for c in selected)
    negative_count = sum(expected[str(c.get("candidate_id"))] == "R" for c in selected)
    if positive_count != 8 or negative_count != 8:
        raise RuntimeError(
            f"semantic smoke balance failure: positives={positive_count}, "
            f"negatives={negative_count}; expected 8/8"
        )

    # Attach only diagnostic metadata in-memory; it is not sent to Qwen.
    for candidate in selected:
        cid = str(candidate.get("candidate_id"))
        candidate["_smoke_expected_label"] = expected[cid]
        candidate["_smoke_challenge_type"] = challenge[cid]

    return selected



# ---------------------------------------------------------------------------
# Prompt / inference
# ---------------------------------------------------------------------------

def build_binary_grammar() -> Any:
    """Create the frozen A/R grammar used for every semantic call."""
    if LlamaGrammar is None:
        raise RuntimeError("llama_cpp.LlamaGrammar is unavailable")
    grammar = LlamaGrammar.from_string(BINARY_GRAMMAR_TEXT)
    if grammar is None:
        raise RuntimeError("llama_cpp returned no binary grammar object")
    return grammar


def run_grammar_preflight(llm: Any, grammar: Any) -> tuple[bool, str, float]:
    """Exercise the actual llama.cpp grammar path before candidate inference."""
    preflight_prompt = (
        "Classify the following statement as investment evidence for revenue.\n"
        "Statement: FY25 revenue was INR 2.1 Cr.\n"
        "Output exactly one character: A or R."
    )
    start = time.perf_counter()
    try:
        response = llm(
            preflight_prompt,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            seed=SEED,
            stop=None,
            echo=False,
            grammar=grammar,
        )
        raw = extract_text_from_completion(response).strip()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}", time.perf_counter() - start

    elapsed = time.perf_counter() - start
    if raw not in {"A", "R"}:
        return False, f"invalid preflight output: {raw!r}", elapsed
    return True, raw, elapsed


def build_prompt(candidate: dict[str, Any]) -> str:
    guidance = get_field_guidance(normalize(candidate.get("field", "")))
    return SYSTEM_PROMPT.format(
        field=normalize(candidate.get("field", "")),
        field_definition=guidance["definition"],
        acceptance_test=guidance["accept"],
        rejection_test=guidance["reject"],
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
            grammar=grammar,
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
        "smoke_expected_label": candidate.get("_smoke_expected_label"),
        "smoke_challenge_type": candidate.get("_smoke_challenge_type"),
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
    preflight_sec: float,
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

    challenge_expected = [
        r["smoke_expected_label"]
        for r in records
        if r.get("smoke_expected_label") in {"A", "R"}
    ]
    challenge_predicted = [
        "A" if r["semantic"]["accepted"] is True else
        "R" if r["semantic"]["accepted"] is False else ""
        for r in records
    ]
    challenge_comparable = [
        (e, p) for e, p in zip(challenge_expected, challenge_predicted)
        if p in {"A", "R"}
    ]
    challenge_correct = sum(e == p for e, p in challenge_comparable)

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
            "challenge_expected_count": len(challenge_expected),
            "challenge_comparable_count": len(challenge_comparable),
            "challenge_correct": challenge_correct,
            "challenge_accuracy_pct": pct(challenge_correct, len(challenge_comparable)),
        },
        "timing": {
            "grammar_preflight_sec": round(preflight_sec, 4),
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
    print("V3.3-B.2.2 SMOKE — QWEN BINARY SEMANTIC BOUNDARY")
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
            f"| expected={candidate.get('_smoke_expected_label')} "
            f"| {candidate.get('_smoke_challenge_type')} "
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

    preflight_ok, preflight_value, preflight_sec = run_grammar_preflight(
        llm, binary_grammar
    )
    if not preflight_ok:
        print(
            f"ERROR: grammar preflight failed: {preflight_value}",
            file=sys.stderr,
        )
        return 2
    print(
        f"GRAMMAR PREFLIGHT  : PASS ({preflight_value}) "
        f"{preflight_sec:.4f}s"
    )

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
        preflight_sec,
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

    semantic_boundary_pass = (
        summary["population"]["challenge_comparable_count"] == SMOKE_COUNT
        and summary["population"]["challenge_accuracy_pct"] >= 75.0
    )

    smoke_pass = contract_pass and semantic_boundary_pass

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
            "purpose": "validate_semantic_boundary_before_full_251_run",
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
            "grammar_preflight_pass": preflight_ok,
            "candidate_count_exact": len(candidates) == SMOKE_COUNT,
            "all_candidates_processed": len(records) == len(candidates),
            "binary_validity_pct": summary["population"]["binary_validity_pct"],
            "contract_gate_pass": contract_pass,
            "semantic_boundary_gate_pass": semantic_boundary_pass,
            "smoke_gate_pass": smoke_pass,
            "provenance_owned_by_python": True,
            "dimension_field_owned_by_python": True,
            "candidate_text_owned_by_python": True,
            "qwen_generated_evidence_text": False,
            "qwen_generated_provenance": False,
            "semantic_gold_labels_available": True,
            "semantic_gold_labels_type": "manual_smoke_expectations_only",
        },
        "results": records,
        "unique_evidence": unique_evidence,
        "status": "PASS" if smoke_pass else "FAIL",
        "full_benchmark_authorized": smoke_pass,
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
    print("V3.3-B.2.2 SMOKE SUMMARY")
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
    print(f"BOUNDARY ACCURACY  : {summary['population']['challenge_accuracy_pct']:.3f}%")
    print(f"BOUNDARY PASS      : {semantic_boundary_pass}")
    print(f"SMOKE PASS         : {smoke_pass}")
    print(f"STATUS             : {result['status']}")
    print("=" * 78)

    if summary["invalid_reason_counts"]:
        print("INVALID RESPONSE REASONS")
        for reason, count in sorted(
            summary["invalid_reason_counts"].items()
        ):
            print(f"  {reason:24s}: {count}")

    return 0 if smoke_pass else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "V3.3-B.2.1 10-candidate Qwen binary grammar smoke"
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
