#!/usr/bin/env python3
"""
V3.3 Semantic Evidence AI Review
================================

Diagnostic-only E1 review layer for the V3.3 semantic-evidence pipeline.

Purpose
-------
Review the 92-row human-review population produced by:
    review_v33_evidence_acceptance.py

The model evaluates the semantic relationship between each V3.3 accepted
proposition and the available canonical evidence / review context.

This script MUST NOT:
- mutate AnalysisEvidence
- mutate dimension_evidence.json
- write production analysis state
- replace B3/B4.2 semantic validation
- create new semantic candidates
- silently promote evidence

AI decisions:
    NEW_EVIDENCE
    SAME_PROPOSITION
    DUPLICATE_OR_OVERLAP
    WRONG_DIMENSION_OR_FIELD
    INSUFFICIENT_EVIDENCE
    UNCERTAIN

Promotion recommendations are deterministic mappings from the AI decision
plus safety checks. They are recommendations only.

Initial operating mode:
    diagnostic_only = True
    production_mutation = False

Expected 92-row population:
    90 proposition review items
     2 ambiguous canonical-match items
    92 total

The script is deliberately standalone so it can be run against the existing
generated artifacts before integration into production services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# Frozen / explicit configuration
# ---------------------------------------------------------------------------

REPORT_VERSION = "v33-semantic-evidence-ai-review-v1"
PROMPT_VERSION = "v33-canonical-evidence-review-v1"

MODEL = "openai/gpt-oss-20b"
PROVIDER = "CoreWeave"

TEMPERATURE = 0
TOP_P = 1
MAX_TOKENS = 1024
REASONING = "medium"

CONCURRENCY = 1
TIMEOUT = 120
RETRIES = 3
FALLBACK_ENABLED = False

EXPECTED_PROPOSITION_ITEMS = 90
EXPECTED_AMBIGUOUS_ITEMS = 2
EXPECTED_TOTAL_ITEMS = 92

PRODUCTION_MUTATION = False
DIAGNOSTIC_ONLY = True

DECISIONS = {
    "NEW_EVIDENCE",
    "SAME_PROPOSITION",
    "DUPLICATE_OR_OVERLAP",
    "WRONG_DIMENSION_OR_FIELD",
    "INSUFFICIENT_EVIDENCE",
    "UNCERTAIN",
}

CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}

PROMOTION_BY_DECISION = {
    "NEW_EVIDENCE": "PROMOTE",
    "SAME_PROPOSITION": "RETAIN_EXISTING",
    "DUPLICATE_OR_OVERLAP": "DO_NOT_PROMOTE",
    "WRONG_DIMENSION_OR_FIELD": "DO_NOT_PROMOTE",
    "INSUFFICIENT_EVIDENCE": "DO_NOT_PROMOTE",
    "UNCERTAIN": "REVIEW_REQUIRED",
}

# Conservative safety conditions. Even a high-confidence NEW_EVIDENCE result
# is not an unconditional production promotion.
SAFE_FOR_AI_PROPOSED_PROMOTION = {
    "provenance_complete",
    "dimension_valid",
    "field_valid",
    "v33_accepted",
    "a12_passed",
    "canonical_match_absent",
    "compound_proposition_false",
    "contradictory_canonical_evidence_absent",
}

SYSTEM_PROMPT = r"""
You are reviewing candidate investment evidence for canonicalization.

Your task is NOT to decide whether the startup is investable.
Your task is NOT to score the startup.
Your task is NOT to infer facts.
Your task is NOT to create new facts.

Your task is to determine the semantic relationship between the candidate
proposition and the supplied existing canonical evidence and review context.

Use only the supplied candidate, canonical evidence, cluster context,
dimension/field context, and provenance.

Decision definitions:

1. NEW_EVIDENCE
   The candidate expresses a substantively distinct factual proposition that
   is not already represented by the supplied canonical evidence.

2. SAME_PROPOSITION
   The candidate expresses substantially the same factual proposition as
   existing canonical evidence, even when wording differs.

3. DUPLICATE_OR_OVERLAP
   The candidate is redundant with another candidate or overlapping evidence
   and should not create a separate canonical evidence item.

4. WRONG_DIMENSION_OR_FIELD
   The evidence may be factual, but the assigned dimension or field is not
   the correct semantic location.

5. INSUFFICIENT_EVIDENCE
   The supplied text does not provide enough factual support for the claimed
   proposition.

6. UNCERTAIN
   The supplied information is insufficient to distinguish reliably between
   the decisions above.

Rules:

- Do not infer missing values.
- Do not treat keywords alone as evidence.
- Do not treat legal boilerplate as substantive company evidence.
- Do not treat a heading or formula as direct evidence of the field.
- Do not merge merely related propositions.
- Do not call two propositions duplicates merely because they concern the same
  topic.
- A different metric, period, population, threshold, or business fact may
  constitute distinct evidence.
- If a candidate combines multiple independent propositions, mark
  compound_proposition=true and normally require human review.
- If canonical matching is ambiguous, do not force SAME_PROPOSITION.
- If the evidence is fragmentary or OCR context is insufficient, prefer
  INSUFFICIENT_EVIDENCE or UNCERTAIN.
- You must distinguish factual evidence from legal/template language.
- Do not decide investment merit.
- Do not decide whether a business claim is true beyond what the supplied
  evidence supports.
- Return strict JSON only.

Required JSON fields:
{
  "decision": "...",
  "confidence": "HIGH|MEDIUM|LOW",
  "reason": "...",
  "canonical_match_ids": [],
  "same_proposition": false,
  "field_valid": true,
  "evidence_sufficient": true,
  "compound_proposition": false,
  "contradictory_canonical_evidence": false,
  "requires_human_review": false
}
""".strip()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def die(message: str, code: int = 2) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        die(f"input file not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {p}: {exc}")


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def first_value(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", as_text(value)).strip().casefold()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_json_object(text: str) -> dict[str, Any]:
    """
    Accept strict JSON, but tolerate a model wrapping it in a markdown fence
    or surrounding whitespace. Never perform semantic repair.
    """
    raw = text.strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        obj = json.loads(raw[start : end + 1])

    if not isinstance(obj, dict):
        raise ValueError("LLM response JSON root must be an object")
    return obj


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "1", "yes"}
    return bool(value)


# ---------------------------------------------------------------------------
# Review record normalization
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReviewItem:
    review_item: int
    item_type: str
    proposal_id: str
    candidate_id: str
    dimension: str
    field: str
    text: str
    cluster: str
    cluster_members: str
    source_id: str
    source_sha256: str
    extraction_id: str
    source_type: str
    source_path: str
    segment_index: str
    signal_start: str
    signal_end: str
    v33_accepted: bool
    a12_passed: bool
    canonical_match_ids: tuple[str, ...]
    canonical_evidence: tuple[dict[str, Any], ...]
    cluster_evidence: tuple[dict[str, Any], ...]
    raw: dict[str, Any]


def _nested(record: Mapping[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = record
        ok = True
        for part in path.split("."):
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok:
            return cur
    return None


def _get_provenance(record: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("provenance", "candidate_provenance", "source_provenance"):
        value = record.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _get_text(record: Mapping[str, Any]) -> str:
    for key in ("text", "evidence_text", "candidate_text", "proposition_text"):
        value = record.get(key)
        if value:
            return as_text(value)
    nested = _nested(record, "candidate.text", "candidate.evidence_text")
    return as_text(nested)


def _get_canonical_evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = []
    for key in (
        "canonical_evidence",
        "canonical_matches",
        "existing_canonical_evidence",
    ):
        value = record.get(key)
        if isinstance(value, list):
            values.extend(v for v in value if isinstance(v, Mapping))

    return [dict(v) for v in values]


def _get_cluster_evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = []
    for key in ("cluster_evidence", "cluster_members_detail", "members"):
        value = record.get(key)
        if isinstance(value, list):
            values.extend(v for v in value if isinstance(v, Mapping))
    return [dict(v) for v in values]


def _get_match_ids(record: Mapping[str, Any]) -> tuple[str, ...]:
    values = []
    for key in (
        "canonical_match_ids",
        "canonical_evidence_ids",
        "canonical_ids",
    ):
        value = record.get(key)
        if isinstance(value, list):
            values.extend(as_text(v) for v in value if v)
        elif value:
            values.append(as_text(value))
    return tuple(dict.fromkeys(values))


def normalize_review_items(payload: Any) -> list[ReviewItem]:
    if not isinstance(payload, Mapping):
        die("review input root must be a JSON object")

    records = payload.get("records")
    if not isinstance(records, list):
        die("review input does not contain a top-level 'records' list")

    result: list[ReviewItem] = []

    for idx, raw in enumerate(records, start=1):
        if not isinstance(raw, Mapping):
            die(f"review record {idx} is not an object")

        prov = _get_provenance(raw)
        ai_seed = raw.get("ai_review") if isinstance(raw.get("ai_review"), Mapping) else {}

        review_item = first_value(raw, "review_item", "item", "index", default=idx)
        try:
            review_item = int(review_item)
        except (TypeError, ValueError):
            review_item = idx

        proposal_id = as_text(first_value(
            raw, "proposal_id", "id", default=f"review:{review_item}"
        ))
        candidate_id = as_text(first_value(
            raw, "candidate_id", default=""
        ))

        item_type = as_text(first_value(
            raw, "item_type", "type", default="PROPOSITION"
        ))

        result.append(
            ReviewItem(
                review_item=review_item,
                item_type=item_type,
                proposal_id=proposal_id,
                candidate_id=candidate_id,
                dimension=as_text(first_value(raw, "dimension", default="")),
                field=as_text(first_value(raw, "field", default="")),
                text=_get_text(raw),
                cluster=as_text(first_value(raw, "cluster", "cluster_id", default="")),
                cluster_members=as_text(first_value(
                    raw, "cluster_members", "cluster_member_ids", default=""
                )),
                source_id=as_text(first_value(
                    prov, "source_id", default=first_value(raw, "source_id", default="")
                )),
                source_sha256=as_text(first_value(
                    prov, "source_sha256", "sha256",
                    default=first_value(raw, "source_sha256", default="")
                )),
                extraction_id=as_text(first_value(
                    prov, "extraction_id",
                    default=first_value(raw, "extraction_id", default="")
                )),
                source_type=as_text(first_value(
                    prov, "source_type",
                    default=first_value(raw, "source_type", default="")
                )),
                source_path=as_text(first_value(
                    prov, "source_path",
                    default=first_value(raw, "source_path", default="")
                )),
                segment_index=as_text(first_value(
                    prov, "segment_index",
                    default=first_value(raw, "segment_index", default="")
                )),
                signal_start=as_text(first_value(
                    prov, "signal_start",
                    default=first_value(raw, "signal_start", default="")
                )),
                signal_end=as_text(first_value(
                    prov, "signal_end",
                    default=first_value(raw, "signal_end", default="")
                )),
                v33_accepted=bool_value(first_value(
                    raw, "v33_accepted",
                    default=first_value(ai_seed, "v33_accepted", default=True)
                )),
                a12_passed=bool_value(first_value(
                    raw, "a12_passed",
                    default=first_value(ai_seed, "a12_passed", default=True)
                )),
                canonical_match_ids=_get_match_ids(raw),
                canonical_evidence=tuple(_get_canonical_evidence(raw)),
                cluster_evidence=tuple(_get_cluster_evidence(raw)),
                raw=dict(raw),
            )
        )

    return result


# ---------------------------------------------------------------------------
# Canonical evidence loading / indexing
# ---------------------------------------------------------------------------

def load_canonical_evidence(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []

    payload = load_json(path)

    if isinstance(payload, list):
        return [dict(x) for x in payload if isinstance(x, Mapping)]

    if isinstance(payload, Mapping):
        for key in (
            "evidence",
            "records",
            "items",
            "dimension_evidence",
            "analysis_evidence",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(x) for x in value if isinstance(x, Mapping)]

        # Some dimension_evidence files are mappings of dimensions to lists.
        flattened: list[dict[str, Any]] = []
        for dimension, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping):
                        item_copy = dict(item)
                        item_copy.setdefault("dimension", dimension)
                        flattened.append(item_copy)
        if flattened:
            return flattened

    die(f"cannot identify canonical evidence records in {path}")


def canonical_identity(record: Mapping[str, Any]) -> str:
    for key in (
        "evidence_id",
        "id",
        "analysis_evidence_id",
        "canonical_id",
        "item_id",
    ):
        value = record.get(key)
        if value:
            return as_text(value)
    return ""


def canonical_text(record: Mapping[str, Any]) -> str:
    for key in ("text", "evidence_text", "proposition", "claim", "value"):
        value = record.get(key)
        if value:
            return as_text(value)
    return ""


def select_canonical_context(
    item: ReviewItem,
    canonical_records: Sequence[Mapping[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Conservative deterministic retrieval for context only.

    Prefer:
      1. explicitly matched IDs
      2. same dimension + field
      3. same normalized text

    This does not make a semantic decision.
    """
    explicit = set(item.canonical_match_ids)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(record: Mapping[str, Any], reason: str) -> None:
        ident = canonical_identity(record)
        key = ident or sha256_text(
            normalize_text(canonical_text(record))
            + "|"
            + as_text(record.get("dimension"))
            + "|"
            + as_text(record.get("field"))
        )[:24]
        if key in seen:
            return
        seen.add(key)
        copy = dict(record)
        copy["_context_match_reason"] = reason
        selected.append(copy)

    for record in canonical_records:
        ident = canonical_identity(record)
        if ident and ident in explicit:
            add(record, "explicit_canonical_match")

    item_text = normalize_text(item.text)
    for record in canonical_records:
        if len(selected) >= limit:
            break
        if (
            as_text(record.get("dimension")) == item.dimension
            and as_text(record.get("field")) == item.field
        ):
            add(record, "same_dimension_field")

    if item_text:
        for record in canonical_records:
            if len(selected) >= limit:
                break
            if normalize_text(canonical_text(record)) == item_text:
                add(record, "exact_normalized_text")

    return selected[:limit]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def format_provenance(item: ReviewItem) -> dict[str, Any]:
    return {
        "source_id": item.source_id,
        "source_sha256": item.source_sha256,
        "extraction_id": item.extraction_id,
        "source_type": item.source_type,
        "source_path": item.source_path,
        "segment_index": item.segment_index,
        "signal_start": item.signal_start,
        "signal_end": item.signal_end,
    }


def build_user_prompt(
    item: ReviewItem,
    canonical_context: Sequence[Mapping[str, Any]],
) -> str:
    cluster_context = list(item.cluster_evidence)
    if not cluster_context and item.cluster_members:
        cluster_context = [{"cluster_members": item.cluster_members}]

    payload = {
        "review_item": item.review_item,
        "item_type": item.item_type,
        "proposal_id": item.proposal_id,
        "candidate_id": item.candidate_id,
        "dimension": item.dimension,
        "field": item.field,
        "candidate_proposition": item.text,
        "candidate_provenance": format_provenance(item),
        "cluster": item.cluster,
        "cluster_context": cluster_context,
        "canonical_match_ids_from_review_artifact": list(item.canonical_match_ids),
        "existing_canonical_evidence": list(canonical_context),
        "v33_accepted": item.v33_accepted,
        "a12_passed": item.a12_passed,
    }

    return (
        "Review the following V3.3 evidence proposition.\n\n"
        "Determine its semantic relationship to the supplied canonical "
        "evidence and review context.\n\n"
        "Do not infer facts outside the supplied material.\n"
        "Return JSON only using the required schema.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


# ---------------------------------------------------------------------------
# OpenRouter / CoreWeave client
# ---------------------------------------------------------------------------

class LLMReviewError(RuntimeError):
    pass


class OpenRouterClient:
    """
    Minimal stdlib-only OpenRouter client.

    Expected environment:
        OPENROUTER_API_KEY

    The implementation intentionally has no fallback provider.
    """

    def __init__(
        self,
        api_key: str,
        model: str = MODEL,
        provider: str = PROVIDER,
        timeout: int = TIMEOUT,
        retries: int = RETRIES,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.timeout = timeout
        self.retries = retries

    def review(self, user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            import urllib.error
            import urllib.request
        except ImportError as exc:
            raise LLMReviewError(f"stdlib HTTP imports unavailable: {exc}")

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "v33_canonical_evidence_review",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": sorted(DECISIONS),
                            },
                            "confidence": {
                                "type": "string",
                                "enum": sorted(CONFIDENCE),
                            },
                            "reason": {"type": "string"},
                            "canonical_match_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "same_proposition": {"type": "boolean"},
                            "field_valid": {"type": "boolean"},
                            "evidence_sufficient": {"type": "boolean"},
                            "compound_proposition": {"type": "boolean"},
                            "contradictory_canonical_evidence": {
                                "type": "boolean"
                            },
                            "requires_human_review": {"type": "boolean"},
                        },
                        "required": [
                            "decision",
                            "confidence",
                            "reason",
                            "canonical_match_ids",
                            "same_proposition",
                            "field_valid",
                            "evidence_sufficient",
                            "compound_proposition",
                            "contradictory_canonical_evidence",
                            "requires_human_review",
                        ],
                    },
                },
            },
            "provider": {
                "order": [self.provider],
                "allow_fallbacks": FALLBACK_ENABLED,
            },
        }

        encoded = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=encoded,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/KritvaOS/KritvaOS",
                "X-Title": "Investment OS V3.3 Evidence Review",
            },
        )

        last_error: Exception | None = None

        for attempt in range(1, self.retries + 2):
            started = time.monotonic()
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout,
                ) as response:
                    raw = response.read().decode("utf-8")

                elapsed = time.monotonic() - started
                payload = json.loads(raw)

                choice = payload["choices"][0]
                message = choice["message"]
                content = message.get("content", "")

                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, Mapping)
                    )

                result = extract_json_object(as_text(content))

                telemetry = {
                    "attempt": attempt,
                    "elapsed_seconds": round(elapsed, 6),
                    "model": payload.get("model", self.model),
                    "provider": self.provider,
                    "usage": payload.get("usage", {}),
                    "response_id": payload.get("id"),
                }

                return result, telemetry

            except Exception as exc:
                last_error = exc
                if attempt <= self.retries:
                    # Deterministic retry sequence; no alternate provider.
                    time.sleep(min(2 ** (attempt - 1), 8))

        raise LLMReviewError(
            f"LLM request failed after {self.retries + 1} attempts: {last_error}"
        )


# ---------------------------------------------------------------------------
# LLM response validation
# ---------------------------------------------------------------------------

def validate_llm_result(result: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "decision",
        "confidence",
        "reason",
        "canonical_match_ids",
        "same_proposition",
        "field_valid",
        "evidence_sufficient",
        "compound_proposition",
        "contradictory_canonical_evidence",
        "requires_human_review",
    }

    missing = sorted(required - set(result))
    if missing:
        raise ValueError(f"LLM response missing fields: {missing}")

    decision = as_text(result["decision"])
    confidence = as_text(result["confidence"])

    if decision not in DECISIONS:
        raise ValueError(f"invalid decision: {decision}")

    if confidence not in CONFIDENCE:
        raise ValueError(f"invalid confidence: {confidence}")

    if not isinstance(result["canonical_match_ids"], list):
        raise ValueError("canonical_match_ids must be a list")

    if not all(isinstance(x, str) for x in result["canonical_match_ids"]):
        raise ValueError("canonical_match_ids must contain strings")

    for key in (
        "same_proposition",
        "field_valid",
        "evidence_sufficient",
        "compound_proposition",
        "contradictory_canonical_evidence",
        "requires_human_review",
    ):
        if not isinstance(result[key], bool):
            raise ValueError(f"{key} must be boolean")

    reason = as_text(result["reason"]).strip()
    if not reason:
        raise ValueError("reason must not be empty")

    return {
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "canonical_match_ids": list(
            dict.fromkeys(result["canonical_match_ids"])
        ),
        "same_proposition": result["same_proposition"],
        "field_valid": result["field_valid"],
        "evidence_sufficient": result["evidence_sufficient"],
        "compound_proposition": result["compound_proposition"],
        "contradictory_canonical_evidence": result[
            "contradictory_canonical_evidence"
        ],
        "requires_human_review": result["requires_human_review"],
    }


# ---------------------------------------------------------------------------
# Deterministic safety / recommendation policy
# ---------------------------------------------------------------------------

def provenance_complete(item: ReviewItem) -> bool:
    required = (
        item.source_id,
        item.source_sha256,
        item.extraction_id,
        item.source_type,
        item.source_path,
        item.segment_index,
        item.text,
        item.dimension,
        item.field,
    )
    return all(as_text(x).strip() for x in required)


def canonical_match_absent(
    item: ReviewItem,
    canonical_context: Sequence[Mapping[str, Any]],
    ai_result: Mapping[str, Any],
) -> bool:
    if item.canonical_match_ids:
        return False

    if ai_result.get("canonical_match_ids"):
        return False

    # Exact normalized text match in supplied canonical context means that
    # promotion should not be proposed as new evidence.
    candidate_norm = normalize_text(item.text)
    if candidate_norm:
        for record in canonical_context:
            if normalize_text(canonical_text(record)) == candidate_norm:
                return False

    return True


def deterministic_safety_checks(
    item: ReviewItem,
    ai_result: Mapping[str, Any],
    canonical_context: Sequence[Mapping[str, Any]],
) -> dict[str, bool]:
    compound = bool(ai_result["compound_proposition"])
    contradiction = bool(ai_result["contradictory_canonical_evidence"])

    return {
        "provenance_complete": provenance_complete(item),
        "dimension_valid": bool(item.dimension.strip()),
        "field_valid": bool(item.field.strip()) and bool(ai_result["field_valid"]),
        "v33_accepted": item.v33_accepted,
        "a12_passed": item.a12_passed,
        "canonical_match_absent": canonical_match_absent(
            item, canonical_context, ai_result
        ),
        "compound_proposition_false": not compound,
        "contradictory_canonical_evidence_absent": not contradiction,
    }


def recommendation_from_result(
    item: ReviewItem,
    ai_result: Mapping[str, Any],
    safety: Mapping[str, bool],
) -> tuple[str, list[str]]:
    decision = ai_result["decision"]
    reasons: list[str] = []

    if decision not in PROMOTION_BY_DECISION:
        return "REVIEW_REQUIRED", ["invalid_ai_decision"]

    recommendation = PROMOTION_BY_DECISION[decision]

    if decision == "NEW_EVIDENCE":
        failed = [
            key
            for key in SAFE_FOR_AI_PROPOSED_PROMOTION
            if not safety.get(key, False)
        ]

        if failed:
            recommendation = "REVIEW_REQUIRED"
            reasons.extend(f"promotion_safety_failed:{x}" for x in failed)

        if ai_result["confidence"] != "HIGH":
            recommendation = "REVIEW_REQUIRED"
            reasons.append("new_evidence_not_high_confidence")

        if ai_result["requires_human_review"]:
            recommendation = "REVIEW_REQUIRED"
            reasons.append("model_requested_human_review")

        if not ai_result["evidence_sufficient"]:
            recommendation = "REVIEW_REQUIRED"
            reasons.append("model_marked_evidence_insufficient")

    elif decision == "SAME_PROPOSITION":
        if ai_result["confidence"] == "LOW":
            recommendation = "REVIEW_REQUIRED"
            reasons.append("same_proposition_low_confidence")

        if ai_result["requires_human_review"]:
            recommendation = "REVIEW_REQUIRED"
            reasons.append("model_requested_human_review")

    elif decision == "UNCERTAIN":
        recommendation = "REVIEW_REQUIRED"
        reasons.append("model_uncertain")

    # Compound propositions are never auto-promoted.
    if ai_result["compound_proposition"]:
        recommendation = "REVIEW_REQUIRED"
        reasons.append("compound_proposition")

    # Contradiction is always human review.
    if ai_result["contradictory_canonical_evidence"]:
        recommendation = "REVIEW_REQUIRED"
        reasons.append("contradictory_canonical_evidence")

    return recommendation, reasons


# ---------------------------------------------------------------------------
# Population / artifact validation
# ---------------------------------------------------------------------------

def validate_review_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    diagnostic_only = payload.get("diagnostic_only", True)
    production_mutation = payload.get("production_mutation", False)
    llm_calls = payload.get("llm_calls", 0)

    records = payload.get("records")
    if not isinstance(records, list):
        records = []

    proposition_count = sum(
        1
        for record in records
        if isinstance(record, Mapping)
        and as_text(record.get("item_type", "PROPOSITION"))
        != "AMBIGUOUS_CANONICAL_MATCH"
    )
    ambiguous_count = sum(
        1
        for record in records
        if isinstance(record, Mapping)
        and as_text(record.get("item_type", ""))
        == "AMBIGUOUS_CANONICAL_MATCH"
    )

    return {
        "diagnostic_only": diagnostic_only is True,
        "production_mutation_absent": production_mutation is False,
        "review_records_present": isinstance(records, list),
        "review_population_expected": len(records) == EXPECTED_TOTAL_ITEMS,
        "proposition_population_expected": proposition_count
        == EXPECTED_PROPOSITION_ITEMS,
        "ambiguous_population_expected": ambiguous_count
        == EXPECTED_AMBIGUOUS_ITEMS,
        "input_llm_calls_zero": llm_calls == 0,
    }


def validate_v33_artifact(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {
            "v33_artifact_available": False,
            "v33_artifact_valid": True,
        }

    checks = {
        "v33_artifact_available": True,
        "v33_artifact_valid": True,
    }

    # Be tolerant of exact artifact naming differences while checking the
    # critical population accounting when fields are present.
    for key, expected in (
        ("raw_candidates", 1167),
        ("a12_passed", 251),
        ("final_accepted", 107),
        ("final_rejected", 144),
        ("recovered", 3),
        ("b4_2_selected", 14),
    ):
        if key in payload:
            try:
                checks[f"v33_{key}_expected"] = int(payload[key]) == expected
            except (TypeError, ValueError):
                checks[f"v33_{key}_expected"] = False

    return checks


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def decision_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in sorted(DECISIONS)}
    for record in records:
        decision = (
            record.get("ai_review", {}).get("decision")
            if isinstance(record.get("ai_review"), Mapping)
            else None
        )
        if decision in counts:
            counts[decision] += 1
    return counts


def recommendation_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    allowed = {
        "PROMOTE",
        "RETAIN_EXISTING",
        "DO_NOT_PROMOTE",
        "REVIEW_REQUIRED",
    }
    counts = {key: 0 for key in sorted(allowed)}
    for record in records:
        value = record.get("promotion_recommendation")
        if value in counts:
            counts[value] += 1
    return counts


def build_text_report(report: Mapping[str, Any]) -> str:
    lines: list[str] = []

    def line(value: Any = "") -> None:
        lines.append(as_text(value))

    line("=" * 100)
    line("V3.3 SEMANTIC EVIDENCE AI REVIEW")
    line("=" * 100)
    line(f"REPORT VERSION           : {report['report_version']}")
    line(f"PROMPT VERSION           : {report['prompt_version']}")
    line(f"STARTUP                  : {report['startup']}")
    line(f"MODEL                    : {report['model']}")
    line(f"PROVIDER                 : {report['provider']}")
    line()
    line(f"PROPOSITION ITEMS        : {report['input_population']['proposition_items']}")
    line(f"AMBIGUOUS ITEMS          : {report['input_population']['ambiguous_items']}")
    line(f"TOTAL ITEMS              : {report['input_population']['total_items']}")
    line()
    line("AI DECISION COUNTS")
    line("-" * 100)
    for key, value in report["decision_counts"].items():
        line(f"{key:<32}: {value}")
    line()
    line("PROMOTION RECOMMENDATIONS")
    line("-" * 100)
    for key, value in report["promotion_recommendation_counts"].items():
        line(f"{key:<32}: {value}")
    line()
    line(f"LLM CALLS                : {report['llm_calls']}")
    line(f"VALID RESPONSES          : {report['valid_responses']}")
    line(f"INVALID RESPONSES        : {report['invalid_responses']}")
    line(f"RETRIES                  : {report['retries']}")
    line(f"PRODUCTION MUTATION      : {'YES' if report['production_mutation'] else 'NO'}")
    line(f"DIAGNOSTIC ONLY          : {'YES' if report['diagnostic_only'] else 'NO'}")
    line()

    line("=" * 100)
    line("REVIEW RECORDS")
    line("=" * 100)

    for record in report["records"]:
        line()
        line(
            f"[{record['review_item']}] "
            f"{record['promotion_recommendation']}"
        )
        line(f"Proposal ID              : {record['proposal_id']}")
        line(f"Candidate ID             : {record['candidate_id']}")
        line(f"Item Type                : {record['item_type']}")
        line(f"Dimension                : {record['dimension']}")
        line(f"Field                    : {record['field']}")
        line(f"Cluster                  : {record['cluster']}")
        line(f"AI Decision              : {record['ai_review']['decision']}")
        line(f"AI Confidence            : {record['ai_review']['confidence']}")
        line(f"AI Reason                : {record['ai_review']['reason']}")
        line(
            "Canonical Match IDs      : "
            + ", ".join(record["ai_review"]["canonical_match_ids"])
        )
        line(
            "Requires Human Review    : "
            + ("YES" if record["ai_review"]["requires_human_review"] else "NO")
        )
        line(
            "Compound Proposition     : "
            + ("YES" if record["ai_review"]["compound_proposition"] else "NO")
        )
        line(
            "Contradictory Canonical  : "
            + (
                "YES"
                if record["ai_review"]["contradictory_canonical_evidence"]
                else "NO"
            )
        )
        line(f"Recommendation            : {record['promotion_recommendation']}")
        if record["recommendation_reasons"]:
            line(
                "Recommendation Reasons   : "
                + "; ".join(record["recommendation_reasons"])
            )
        line("Safety Checks:")
        for key, value in record["safety_checks"].items():
            line(f"  {key:<36}: {'PASS' if value else 'FAIL'}")
        line("Evidence Text:")
        line(record["evidence_text"])

    line()
    line("=" * 100)
    line("ACCOUNTING CHECKS")
    line("=" * 100)
    for key, value in report["accounting_checks"].items():
        line(f"{key:<45}: {'PASS' if value else 'FAIL'}")

    line()
    line(f"STATUS                   : {report['status']}")
    line("=" * 100)

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostic LLM review of V3.3 semantic evidence."
    )
    parser.add_argument("--startup", required=True)

    parser.add_argument(
        "--review-input",
        required=True,
        help="v33_semantic_evidence_acceptance_review.json",
    )
    parser.add_argument(
        "--v33-input",
        default=None,
        help="Optional v33_semantic_evidence_validation.json",
    )
    parser.add_argument(
        "--reconciliation-input",
        default=None,
        help="Optional v33_semantic_evidence_reconciliation_analysis.json",
    )
    parser.add_argument(
        "--clusters-input",
        default=None,
        help="Optional v33_semantic_evidence_clusters.json",
    )
    parser.add_argument(
        "--canonical-input",
        default=None,
        help="Optional canonical dimension_evidence.json",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="AI review JSON output path",
    )
    parser.add_argument(
        "--text-output",
        required=True,
        help="AI review text output path",
    )

    parser.add_argument(
        "--api-key-env",
        default="OPENROUTER_API_KEY",
        help="Environment variable containing OpenRouter API key",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Diagnostic limit; must not be used for a production promotion run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts and validate input without making LLM calls",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    review_payload = load_json(args.review_input)
    if not isinstance(review_payload, Mapping):
        die("review input must be a JSON object")

    input_checks = validate_review_artifact(review_payload)

    items = normalize_review_items(review_payload)

    if len(items) != EXPECTED_TOTAL_ITEMS and args.limit is None:
        die(
            f"expected {EXPECTED_TOTAL_ITEMS} review items, "
            f"found {len(items)}"
        )

    if args.limit is not None:
        if args.limit <= 0:
            die("--limit must be > 0")
        items = items[: args.limit]

    v33_payload = None
    if args.v33_input:
        loaded = load_json(args.v33_input)
        if isinstance(loaded, Mapping):
            v33_payload = loaded

    v33_checks = validate_v33_artifact(v33_payload)

    canonical_records = load_canonical_evidence(args.canonical_input)

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key and not args.dry_run:
        die(
            f"missing API key environment variable {args.api_key_env}; "
            "use --dry-run for prompt/input validation only"
        )

    client = None
    if not args.dry_run:
        client = OpenRouterClient(
            api_key=api_key,
            model=MODEL,
            provider=PROVIDER,
            timeout=TIMEOUT,
            retries=RETRIES,
        )

    records: list[dict[str, Any]] = []
    llm_calls = 0
    valid_responses = 0
    invalid_responses = 0
    retries_total = 0
    total_elapsed = 0.0

    for ordinal, item in enumerate(items, start=1):
        canonical_context = select_canonical_context(
            item,
            canonical_records,
        )

        user_prompt = build_user_prompt(
            item,
            canonical_context,
        )

        if args.dry_run:
            # No semantic decision in dry-run mode.
            ai_result = {
                "decision": "UNCERTAIN",
                "confidence": "LOW",
                "reason": "Dry-run: no LLM call performed.",
                "canonical_match_ids": list(item.canonical_match_ids),
                "same_proposition": False,
                "field_valid": bool(item.field),
                "evidence_sufficient": False,
                "compound_proposition": False,
                "contradictory_canonical_evidence": False,
                "requires_human_review": True,
            }
            telemetry = {
                "dry_run": True,
                "attempt": 0,
                "elapsed_seconds": 0.0,
            }
        else:
            assert client is not None
            try:
                raw_result, telemetry = client.review(user_prompt)
                llm_calls += 1
                valid_responses += 1
                retries_total += max(
                    0, int(telemetry.get("attempt", 1)) - 1
                )
                total_elapsed += float(
                    telemetry.get("elapsed_seconds", 0.0)
                )
                ai_result = validate_llm_result(raw_result)
            except Exception as exc:
                invalid_responses += 1
                # A failed item becomes review-required, never auto-promoted.
                ai_result = {
                    "decision": "UNCERTAIN",
                    "confidence": "LOW",
                    "reason": f"LLM review failed: {exc}",
                    "canonical_match_ids": list(item.canonical_match_ids),
                    "same_proposition": False,
                    "field_valid": bool(item.field),
                    "evidence_sufficient": False,
                    "compound_proposition": False,
                    "contradictory_canonical_evidence": False,
                    "requires_human_review": True,
                }
                telemetry = {
                    "error": str(exc),
                    "attempt": 0,
                    "elapsed_seconds": 0.0,
                }

        safety = deterministic_safety_checks(
            item,
            ai_result,
            canonical_context,
        )

        recommendation, recommendation_reasons = recommendation_from_result(
            item,
            ai_result,
            safety,
        )

        record = {
            "review_item": item.review_item,
            "item_type": item.item_type,
            "proposal_id": item.proposal_id,
            "candidate_id": item.candidate_id,
            "dimension": item.dimension,
            "field": item.field,
            "cluster": item.cluster,
            "cluster_members": item.cluster_members,
            "evidence_text": item.text,
            "provenance": format_provenance(item),
            "canonical_context": canonical_context,
            "ai_review": ai_result,
            "promotion_recommendation": recommendation,
            "recommendation_reasons": recommendation_reasons,
            "safety_checks": safety,
            "telemetry": telemetry,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": sha256_text(
                SYSTEM_PROMPT + "\n\n" + user_prompt
            ),
        }

        records.append(record)

        print(
            f"[{ordinal}/{len(items)}] "
            f"{item.proposal_id} -> "
            f"{ai_result['decision']} / "
            f"{recommendation}"
        )

    counts = decision_counts(records)
    recommendation_count = recommendation_counts(records)

    proposition_count = sum(
        1 for item in items if item.item_type != "AMBIGUOUS_CANONICAL_MATCH"
    )
    ambiguous_count = sum(
        1 for item in items if item.item_type == "AMBIGUOUS_CANONICAL_MATCH"
    )

    unique_proposals = len(
        {record["proposal_id"] for record in records}
    )

    all_safety_valid = all(
        all(
            value is True
            for key, value in record["safety_checks"].items()
            if (
                record["ai_review"]["decision"] == "NEW_EVIDENCE"
                and key in SAFE_FOR_AI_PROPOSED_PROMOTION
            )
        )
        or record["promotion_recommendation"] != "PROMOTE"
        for record in records
    )

    no_unreviewed_promotions = all(
        record["promotion_recommendation"] != "PROMOTE"
        or not record["ai_review"]["requires_human_review"]
        for record in records
    )

    no_unsafe_promotions = all(
        record["promotion_recommendation"] != "PROMOTE"
        or (
            record["ai_review"]["decision"] == "NEW_EVIDENCE"
            and record["ai_review"]["confidence"] == "HIGH"
            and all(
                record["safety_checks"].get(k, False)
                for k in SAFE_FOR_AI_PROPOSED_PROMOTION
            )
        )
        for record in records
    )

    accounting_checks = {
        **input_checks,
        **v33_checks,
        "population_92_when_full_run": (
            len(records) == EXPECTED_TOTAL_ITEMS
            if args.limit is None
            else True
        ),
        "proposition_population_90_when_full_run": (
            proposition_count == EXPECTED_PROPOSITION_ITEMS
            if args.limit is None
            else True
        ),
        "ambiguous_population_2_when_full_run": (
            ambiguous_count == EXPECTED_AMBIGUOUS_ITEMS
            if args.limit is None
            else True
        ),
        "unique_proposal_ids": unique_proposals == len(records),
        "decision_partition": sum(counts.values()) == len(records),
        "recommendation_partition": (
            sum(recommendation_count.values()) == len(records)
        ),
        "all_promotion_safety_checks_pass": all_safety_valid,
        "no_unreviewed_promotion": no_unreviewed_promotions,
        "no_unsafe_promotion": no_unsafe_promotions,
        "diagnostic_only": DIAGNOSTIC_ONLY is True,
        "production_mutation_absent": PRODUCTION_MUTATION is False,
        "fallback_disabled": FALLBACK_ENABLED is False,
        "model_exact": MODEL == "openai/gpt-oss-20b",
        "provider_exact": PROVIDER == "CoreWeave",
    }

    status = "PASS" if all(accounting_checks.values()) else "FAIL"

    report = {
        "report_version": REPORT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "startup": args.startup,
        "diagnostic_only": DIAGNOSTIC_ONLY,
        "production_mutation": PRODUCTION_MUTATION,
        "model": MODEL,
        "provider": PROVIDER,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "reasoning": REASONING,
        "concurrency": CONCURRENCY,
        "timeout": TIMEOUT,
        "retries_configured": RETRIES,
        "fallback_enabled": FALLBACK_ENABLED,
        "input_population": {
            "proposition_items": proposition_count,
            "ambiguous_items": ambiguous_count,
            "total_items": len(records),
        },
        "llm_calls": llm_calls,
        "valid_responses": valid_responses,
        "invalid_responses": invalid_responses,
        "retries": retries_total,
        "wall_seconds_observed": round(total_elapsed, 6),
        "decision_counts": counts,
        "promotion_recommendation_counts": recommendation_count,
        "records": records,
        "accounting_checks": accounting_checks,
        "status": status,
    }

    write_json(args.output, report)
    write_text(args.text_output, build_text_report(report))

    print()
    print("=" * 100)
    print("V3.3 SEMANTIC EVIDENCE AI REVIEW")
    print("=" * 100)
    print(f"PROPOSITION ITEMS        : {proposition_count}")
    print(f"AMBIGUOUS ITEMS          : {ambiguous_count}")
    print(f"TOTAL ITEMS              : {len(records)}")
    print(f"LLM CALLS                : {llm_calls}")
    print(f"VALID RESPONSES          : {valid_responses}")
    print(f"INVALID RESPONSES        : {invalid_responses}")
    print(f"PROMOTE                  : {recommendation_count['PROMOTE']}")
    print(
        "RETAIN_EXISTING          : "
        f"{recommendation_count['RETAIN_EXISTING']}"
    )
    print(
        "DO_NOT_PROMOTE           : "
        f"{recommendation_count['DO_NOT_PROMOTE']}"
    )
    print(
        "REVIEW_REQUIRED          : "
        f"{recommendation_count['REVIEW_REQUIRED']}"
    )
    print(f"JSON REPORT              : {args.output}")
    print(f"TEXT REPORT              : {args.text_output}")
    print(
        "PRODUCTION MUTATION      : "
        f"{'YES' if PRODUCTION_MUTATION else 'NO'}"
    )
    print(f"STATUS                   : {status}")
    print("=" * 100)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
