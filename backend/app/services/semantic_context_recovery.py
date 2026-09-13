"""
B.4.2-v2 selective semantic context recovery.

Architecture
------------
A.1.2 deterministic quality gate
    -> B.3 candidate-only semantic validation
    -> deterministic ambiguity/fragmentation selector
    -> N-1 / N / N+1 context
    -> same-proposition completion
    -> field-semantics validation
    -> final normalized decision

This service is intentionally independent of:
- candidate generation
- A.1.2
- B.3 validation implementation
- AnalysisEvidence persistence
- investment scoring/decision logic

The service consumes the already frozen B.3 candidate population/results.
It never regenerates candidates.

The implementation is designed for parity with the frozen
B.4.2-v2 / GPT-OSS-20B / CoreWeave benchmark.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BENCHMARK_VERSION = "V3.3-B.4.2-V2-20B-2048"
PROMPT_VERSION = "candidate-context-recovery-v2"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
PROVIDER = "CoreWeave"

TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 2048
REASONING_EFFORT = "medium"
CONCURRENCY = 1
TIMEOUT_SECONDS = 120
MAX_RETRIES = 3

FIELD_DEFINITIONS = {
    "cash_burn": "Explicit company cash consumption, burn rate, depletion, or runway over a stated period.",
    "customers": "Actual customers, customer count, named customers, customer relationships, deployments, or customer acquisition. Target segment alone is insufficient.",
    "adoption_usage": "Actual product/service usage or adoption, active users, orders, transactions, deployments, or usage volume.",
    "board_rights": "Investor/shareholder right to appoint, nominate, or designate board representation. Generic board references are insufficient.",
    "market_size": "TAM, SAM, SOM, addressable market size, or quantified market opportunity.",
    "instrument": "Explicit financing/security instrument such as CCPS, equity shares, debt, SAFE, or another stated security.",
    "valuation": "Explicit company valuation.",
    "gmv": "Explicit GMV amount, period, or growth.",
    "growth": "Explicit historical/projected growth rate, trajectory, or direct growth statement.",
    "founder_background": "Founder identity, experience, education, prior company, career, or professional background.",
    "revenue": "Actual/projected company revenue, amount, period, or revenue growth where revenue itself is directly established.",
    "generic": "Direct substantive evidence for the requested field.",
}

# These are intentionally conservative lexical/structural indicators.
# They identify possible fragmentation; they do not decide semantic acceptance.
_REFERENCE_PHRASES = (
    "as follows",
    "as set out",
    "set out in",
    "listed in",
    "list of",
    "including",
    "namely",
    "respectively",
    "pursuant to",
    "subject to",
    "provided that",
    "the following",
    "schedule",
    "annexure",
    "appendix",
    "see ",
)

_INCOMPLETE_ENDINGS = re.compile(
    r"(?:\b(?:of|for|from|to|at|in|on|by|with|under|including|namely|and|or|"
    r"as|per|pursuant|subject|following|listed|set\s+out)\s*)$",
    re.IGNORECASE,
)

_CURRENCY_ENDING = re.compile(
    r"(?:₹|rs\.?|inr|\$|€|£)\s*$",
    re.IGNORECASE,
)

_COLON_ENDING = re.compile(r":\s*$")

_FRAGMENT_ENDING = re.compile(
    r"(?:\b(?:revenue|valuation|investment|price|amount|founder|shareholder|"
    r"shareholding|shares|reserved\s+matters|board|customers?|orders?)\s*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContextRecoveryCandidate:
    candidate_id: str
    dimension: str
    field: str
    candidate_text: str
    source_id: str
    source_sha256: str
    source_type: str
    segment_index: int
    signal: str | None = None
    signal_start: int | None = None
    signal_end: int | None = None
    source_category: str | None = None
    source_authority: str | None = None
    extraction_id: str | None = None
    extraction_method: str | None = None
    document_kind: str | None = None


@dataclass(frozen=True)
class EscalationFeatures:
    has_previous: bool
    has_next: bool
    ends_incomplete: bool
    has_reference_phrase: bool
    has_unresolved_currency: bool
    looks_like_fragment: bool
    candidate_length: int
    sentence_complete: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextWindow:
    candidate_id: str
    center_index: int
    previous_candidate_id: str | None
    next_candidate_id: str | None
    previous_text: str | None
    candidate_text: str
    next_text: str | None
    source_id: str
    source_sha256: str
    segment_index: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextRecoveryResult:
    candidate_id: str
    dimension: str
    field: str
    original_b3_accepted: bool
    original_b3_reason: str
    escalated: bool
    same_proposition: bool
    field_supported: bool
    accepted: bool
    recovered: bool
    reason: str
    candidate_text: str
    previous_text: str | None
    next_text: str | None
    context_candidate_ids: tuple[str, ...]
    valid: bool
    raw_response: str | None
    latency_ms: float | None
    error: str | None
    http_status: int | None
    attempts: int
    retries: int
    provider: str | None
    model: str | None
    finish_reason: str | None
    usage: dict[str, Any] | None
    escalation_features: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["context_candidate_ids"] = list(self.context_candidate_ids)
        return value


class SemanticContextRecoveryError(RuntimeError):
    """Raised for configuration or unrecoverable B.4.2 service errors."""


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _string(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return str(enum_value)
    return str(value)


def _bool(value: Any) -> bool:
    return bool(value)


def _candidate_from_any(value: Any) -> ContextRecoveryCandidate:
    candidate_id = _string(_value(value, "candidate_id"))
    if not candidate_id:
        raise SemanticContextRecoveryError("Candidate is missing candidate_id")

    return ContextRecoveryCandidate(
        candidate_id=candidate_id,
        dimension=_string(_value(value, "dimension"), "") or "",
        field=_string(_value(value, "field"), "") or "",
        candidate_text=_string(
            _value(value, "candidate_text", _value(value, "text", "")),
            "",
        ) or "",
        source_id=_string(_value(value, "source_id"), "") or "",
        source_sha256=_string(_value(value, "source_sha256"), "") or "",
        source_type=_string(_value(value, "source_type"), "") or "",
        segment_index=int(_value(value, "segment_index", 0) or 0),
        signal=_string(_value(value, "signal")),
        signal_start=_value(value, "signal_start"),
        signal_end=_value(value, "signal_end"),
        source_category=_string(_value(value, "source_category")),
        source_authority=_string(_value(value, "source_authority")),
        extraction_id=_string(_value(value, "extraction_id")),
        extraction_method=_string(_value(value, "extraction_method")),
        document_kind=_string(_value(value, "document_kind")),
    )


def _b3_result_accepted(value: Any) -> bool:
    # Accept common frozen/reference shapes.
    if isinstance(value, Mapping):
        if "accepted" in value:
            return bool(value["accepted"])
        model = value.get("model")
        if isinstance(model, Mapping) and "accepted" in model:
            return bool(model["accepted"])
        gate = value.get("gate")
        if isinstance(gate, Mapping) and "accepted" in gate:
            return bool(gate["accepted"])
    else:
        if hasattr(value, "accepted"):
            return bool(value.accepted)
    return False


def _b3_reason(value: Any) -> str:
    if isinstance(value, Mapping):
        if value.get("reason") is not None:
            return str(value["reason"])
        model = value.get("model")
        if isinstance(model, Mapping) and model.get("reason") is not None:
            return str(model["reason"])
    else:
        reason = getattr(value, "reason", None)
        if reason is not None:
            return str(reason)
    return ""


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _features(text: str, has_previous: bool, has_next: bool) -> EscalationFeatures:
    normalized = _normalize_text(text)
    lower = normalized.lower()

    reference = any(
        phrase in lower for phrase in _REFERENCE_PHRASES
    )
    incomplete = bool(
        _INCOMPLETE_ENDINGS.search(normalized)
        or _CURRENCY_ENDING.search(normalized)
        or _COLON_ENDING.search(normalized)
    )
    fragment = bool(_FRAGMENT_ENDING.search(normalized))

    # This deliberately does not attempt grammatical parsing.
    sentence_complete = bool(
        normalized.endswith((".", "!", "?", ";"))
    )

    return EscalationFeatures(
        has_previous=has_previous,
        has_next=has_next,
        ends_incomplete=incomplete,
        has_reference_phrase=reference,
        has_unresolved_currency=bool(_CURRENCY_ENDING.search(normalized)),
        looks_like_fragment=fragment,
        candidate_length=len(normalized),
        sentence_complete=sentence_complete,
    )


class ContextEscalationSelector:
    """
    Deterministic selector.

    A candidate is eligible only when:
      1. B.3 rejected it;
      2. it has at least one same-source adjacent segment;
      3. its text contains a structural indication that adjacent context
         may complete/clarify the proposition.

    No candidate IDs are special-cased.
    """

    def select(
        self,
        candidates: Sequence[Any],
        b3_results: Mapping[str, Any],
    ) -> list[ContextRecoveryCandidate]:
        normalized = [_candidate_from_any(c) for c in candidates]
        by_source = self._group_and_sort(normalized)

        selected: list[ContextRecoveryCandidate] = []

        for candidate in normalized:
            b3 = b3_results.get(candidate.candidate_id)
            if b3 is None:
                raise SemanticContextRecoveryError(
                    f"Missing B.3 result for {candidate.candidate_id}"
                )

            if _b3_result_accepted(b3):
                continue

            window = self._window_for(candidate, by_source)
            features = _features(
                candidate.candidate_text,
                window.previous_candidate_id is not None,
                window.next_candidate_id is not None,
            )

            if self._should_escalate(features):
                selected.append(candidate)

        return selected

    @staticmethod
    def _group_and_sort(
        candidates: Sequence[ContextRecoveryCandidate],
    ) -> dict[tuple[str, str], list[ContextRecoveryCandidate]]:
        groups: dict[
            tuple[str, str],
            list[ContextRecoveryCandidate],
        ] = {}

        for candidate in candidates:
            groups.setdefault(
                (candidate.source_id, candidate.source_sha256),
                [],
            ).append(candidate)

        for group in groups.values():
            group.sort(key=lambda c: (c.segment_index, c.candidate_id))

        return groups

    @classmethod
    def _window_for(
        cls,
        candidate: ContextRecoveryCandidate,
        groups: Mapping[tuple[str, str], Sequence[ContextRecoveryCandidate]],
    ) -> ContextWindow:
        group = groups[(candidate.source_id, candidate.source_sha256)]
        idx = next(
            i for i, item in enumerate(group)
            if item.candidate_id == candidate.candidate_id
        )

        previous = group[idx - 1] if idx > 0 else None
        nxt = group[idx + 1] if idx + 1 < len(group) else None

        # Only true segment adjacency is allowed.
        if previous is not None and previous.segment_index != candidate.segment_index - 1:
            previous = None
        if nxt is not None and nxt.segment_index != candidate.segment_index + 1:
            nxt = None

        return ContextWindow(
            candidate_id=candidate.candidate_id,
            center_index=candidate.segment_index,
            previous_candidate_id=previous.candidate_id if previous else None,
            next_candidate_id=nxt.candidate_id if nxt else None,
            previous_text=previous.candidate_text if previous else None,
            candidate_text=candidate.candidate_text,
            next_text=nxt.candidate_text if nxt else None,
            source_id=candidate.source_id,
            source_sha256=candidate.source_sha256,
            segment_index=candidate.segment_index,
        )

    @staticmethod
    def _should_escalate(features: EscalationFeatures) -> bool:
        if not (features.has_previous or features.has_next):
            return False

        return (
            features.ends_incomplete
            or features.has_reference_phrase
            or features.has_unresolved_currency
            or features.looks_like_fragment
        )


class SemanticContextRecoveryService:
    """B.4.2-v2 selective context recovery service."""

    RESPONSE_SCHEMA = {
        "name": "candidate_context_recovery",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "same_proposition": {"type": "boolean"},
                "field_supported": {"type": "boolean"},
                "accepted": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": [
                "same_proposition",
                "field_supported",
                "accepted",
                "reason",
            ],
            "additionalProperties": False,
        },
    }

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = MODEL,
        provider: str = PROVIDER,
        timeout_seconds: int = TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
        concurrency: int = CONCURRENCY,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.concurrency = concurrency
        self.selector = ContextEscalationSelector()

        if self.concurrency != 1:
            raise SemanticContextRecoveryError(
                "B.4.2 parity implementation requires concurrency=1"
            )

    @property
    def configuration(self) -> dict[str, Any]:
        return {
            "benchmark_version": BENCHMARK_VERSION,
            "prompt_version": PROMPT_VERSION,
            "model": self.model,
            "provider": self.provider,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "reasoning_effort": REASONING_EFFORT,
            "concurrency": self.concurrency,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "context_mode": "selective_n_minus_1_n_n_plus_1",
            "allow_fallbacks": False,
            "require_parameters": True,
        }

    def select_for_recovery(
        self,
        candidates: Sequence[Any],
        b3_results: Mapping[str, Any],
    ) -> list[ContextRecoveryCandidate]:
        return self.selector.select(candidates, b3_results)

    def build_context_windows(
        self,
        candidates: Sequence[Any],
        selected: Sequence[ContextRecoveryCandidate],
    ) -> dict[str, ContextWindow]:
        normalized = [_candidate_from_any(c) for c in candidates]
        groups = self.selector._group_and_sort(normalized)

        result: dict[str, ContextWindow] = {}
        for candidate in selected:
            result[candidate.candidate_id] = self.selector._window_for(
                candidate,
                groups,
            )
        return result

    @staticmethod
    def build_prompt(
        candidate: ContextRecoveryCandidate,
        window: ContextWindow,
    ) -> str:
        definition = FIELD_DEFINITIONS.get(
            candidate.field,
            FIELD_DEFINITIONS["generic"],
        )

        previous = window.previous_text or "(none)"
        nxt = window.next_text or "(none)"

        return f"""You are a strict investment evidence recovery classifier.

The candidate has ALREADY been rejected by a candidate-only semantic validator.

Your task is to determine whether adjacent context completes or clarifies
the SAME proposition already expressed by the TARGET CANDIDATE.

Requested dimension:
{candidate.dimension}

Requested field:
{candidate.field}

Field definition:
{definition}

PREVIOUS CONTEXT:
{previous}

TARGET CANDIDATE:
{window.candidate_text}

NEXT CONTEXT:
{nxt}

Rules:
1. The TARGET CANDIDATE is the semantic anchor.
2. Use PREVIOUS and NEXT only to complete or clarify the same proposition.
3. Do not introduce a new independent fact from surrounding context.
4. The resulting proposition must directly support the requested field.
5. Do not infer missing information.
6. Keyword or phrase presence alone is insufficient.
7. Reject incidental mentions.
8. Reject legal, administrative, accounting, or boilerplate language unless it
   directly establishes the requested field.
9. Reject formulas, ratios, headings, labels, or related metrics when they do
   not directly establish the requested field.
10. If uncertain, reject.

Return JSON only with:
- same_proposition: whether context completes/clarifies the same proposition
- field_supported: whether the completed proposition directly supports the field
- accepted: true only when BOTH are true
- reason: concise explanation
"""

    def recover(
        self,
        candidate: ContextRecoveryCandidate,
        window: ContextWindow,
        b3_result: Any,
    ) -> ContextRecoveryResult:
        if _b3_result_accepted(b3_result):
            return ContextRecoveryResult(
                candidate_id=candidate.candidate_id,
                dimension=candidate.dimension,
                field=candidate.field,
                original_b3_accepted=True,
                original_b3_reason=_b3_reason(b3_result),
                escalated=False,
                same_proposition=False,
                field_supported=False,
                accepted=True,
                recovered=False,
                reason="B.3 accepted; B.4.2 not applicable.",
                candidate_text=candidate.candidate_text,
                previous_text=window.previous_text,
                next_text=window.next_text,
                context_candidate_ids=tuple(
                    x for x in (
                        window.previous_candidate_id,
                        window.next_candidate_id,
                    ) if x
                ),
                valid=True,
                raw_response=None,
                latency_ms=None,
                error=None,
                http_status=None,
                attempts=0,
                retries=0,
                provider=None,
                model=None,
                finish_reason=None,
                usage=None,
                escalation_features=_features(
                    candidate.candidate_text,
                    window.previous_candidate_id is not None,
                    window.next_candidate_id is not None,
                ).as_dict(),
            )

        prompt = self.build_prompt(candidate, window)
        return self._request_and_normalize(candidate, window, b3_result, prompt)

    def recover_many(
        self,
        candidates: Sequence[Any],
        b3_results: Mapping[str, Any],
        *,
        progress: bool = False,
    ) -> list[ContextRecoveryResult]:
        normalized = [_candidate_from_any(c) for c in candidates]
        selected = self.select_for_recovery(normalized, b3_results)
        windows = self.build_context_windows(normalized, selected)

        results: list[ContextRecoveryResult] = []

        for index, candidate in enumerate(selected, start=1):
            if progress:
                print(
                    f"[B4.2 START] {index}/{len(selected)} "
                    f"{candidate.candidate_id} "
                    f"{candidate.dimension}.{candidate.field}",
                    flush=True,
                )

            result = self.recover(
                candidate,
                windows[candidate.candidate_id],
                b3_results[candidate.candidate_id],
            )
            results.append(result)

            if progress:
                status = "A" if result.accepted else "R"
                print(
                    f"[B4.2 END]   {index}/{len(selected)} "
                    f"{candidate.candidate_id} -> {status} "
                    f"same={result.same_proposition} "
                    f"field={result.field_supported}",
                    flush=True,
                )

        return results

    @staticmethod
    def apply_results(
        candidates: Sequence[Any],
        b3_results: Mapping[str, Any],
        recovery_results: Sequence[ContextRecoveryResult],
    ) -> list[dict[str, Any]]:
        recovery_by_id = {
            result.candidate_id: result
            for result in recovery_results
        }

        output: list[dict[str, Any]] = []

        for raw_candidate in candidates:
            candidate = _candidate_from_any(raw_candidate)
            b3 = b3_results.get(candidate.candidate_id)

            if b3 is None:
                raise SemanticContextRecoveryError(
                    f"Missing B.3 result for {candidate.candidate_id}"
                )

            b3_accepted = _b3_result_accepted(b3)
            recovery = recovery_by_id.get(candidate.candidate_id)

            final_accepted = b3_accepted
            recovery_override = False

            if (
                not b3_accepted
                and recovery is not None
                and recovery.valid
                and recovery.accepted
                and recovery.same_proposition
                and recovery.field_supported
            ):
                final_accepted = True
                recovery_override = True

            output.append({
                "candidate_id": candidate.candidate_id,
                "dimension": candidate.dimension,
                "field": candidate.field,
                "b3": {
                    "accepted": b3_accepted,
                    "reason": _b3_reason(b3),
                },
                "b4_2": recovery.as_dict() if recovery else {
                    "escalated": False,
                    "accepted": False,
                    "recovered": False,
                },
                "final": {
                    "accepted": final_accepted,
                    "recovery_override": recovery_override,
                },
                "provenance": {
                    "candidate_id": candidate.candidate_id,
                    "source_id": candidate.source_id,
                    "source_sha256": candidate.source_sha256,
                    "segment_index": candidate.segment_index,
                    "context_candidate_ids": (
                        list(recovery.context_candidate_ids)
                        if recovery else []
                    ),
                },
            })

        return output

    def _request_and_normalize(
        self,
        candidate: ContextRecoveryCandidate,
        window: ContextWindow,
        b3_result: Any,
        prompt: str,
    ) -> ContextRecoveryResult:
        features = _features(
            candidate.candidate_text,
            window.previous_candidate_id is not None,
            window.next_candidate_id is not None,
        )

        started = time.monotonic()
        try:
            response = self._request_openrouter(prompt)
            latency_ms = (time.monotonic() - started) * 1000.0

            parsed = response["parsed"]
            same = parsed["same_proposition"]
            field_supported = parsed["field_supported"]
            accepted = parsed["accepted"]

            # Contract is intentionally strict. Do not "fix" a model response.
            if accepted != (same and field_supported):
                return ContextRecoveryResult(
                    candidate_id=candidate.candidate_id,
                    dimension=candidate.dimension,
                    field=candidate.field,
                    original_b3_accepted=False,
                    original_b3_reason=_b3_reason(b3_result),
                    escalated=True,
                    same_proposition=same,
                    field_supported=field_supported,
                    accepted=False,
                    recovered=False,
                    reason="Invalid semantic contract: accepted must equal "
                           "same_proposition AND field_supported.",
                    candidate_text=candidate.candidate_text,
                    previous_text=window.previous_text,
                    next_text=window.next_text,
                    context_candidate_ids=tuple(
                        x for x in (
                            window.previous_candidate_id,
                            window.next_candidate_id,
                        ) if x
                    ),
                    valid=False,
                    raw_response=response.get("raw_response"),
                    latency_ms=latency_ms,
                    error="semantic_contract_violation",
                    http_status=response.get("http_status"),
                    attempts=response.get("attempts", 1),
                    retries=response.get("retries", 0),
                    provider=response.get("provider"),
                    model=response.get("model"),
                    finish_reason=response.get("finish_reason"),
                    usage=response.get("usage"),
                    escalation_features=features.as_dict(),
                )

            return ContextRecoveryResult(
                candidate_id=candidate.candidate_id,
                dimension=candidate.dimension,
                field=candidate.field,
                original_b3_accepted=False,
                original_b3_reason=_b3_reason(b3_result),
                escalated=True,
                same_proposition=same,
                field_supported=field_supported,
                accepted=accepted,
                recovered=accepted,
                reason=parsed["reason"],
                candidate_text=candidate.candidate_text,
                previous_text=window.previous_text,
                next_text=window.next_text,
                context_candidate_ids=tuple(
                    x for x in (
                        window.previous_candidate_id,
                        window.next_candidate_id,
                    ) if x
                ),
                valid=True,
                raw_response=response.get("raw_response"),
                latency_ms=latency_ms,
                error=None,
                http_status=response.get("http_status"),
                attempts=response.get("attempts", 1),
                retries=response.get("retries", 0),
                provider=response.get("provider"),
                model=response.get("model"),
                finish_reason=response.get("finish_reason"),
                usage=response.get("usage"),
                escalation_features=features.as_dict(),
            )

        except Exception as exc:
            latency_ms = (time.monotonic() - started) * 1000.0
            return ContextRecoveryResult(
                candidate_id=candidate.candidate_id,
                dimension=candidate.dimension,
                field=candidate.field,
                original_b3_accepted=False,
                original_b3_reason=_b3_reason(b3_result),
                escalated=True,
                same_proposition=False,
                field_supported=False,
                accepted=False,
                recovered=False,
                reason="B.4.2 request failed.",
                candidate_text=candidate.candidate_text,
                previous_text=window.previous_text,
                next_text=window.next_text,
                context_candidate_ids=tuple(
                    x for x in (
                        window.previous_candidate_id,
                        window.next_candidate_id,
                    ) if x
                ),
                valid=False,
                raw_response=None,
                latency_ms=latency_ms,
                error=str(exc),
                http_status=None,
                attempts=1,
                retries=0,
                provider=None,
                model=None,
                finish_reason=None,
                usage=None,
                escalation_features=features.as_dict(),
            )

    def _request_openrouter(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise SemanticContextRecoveryError(
                "OPENROUTER_API_KEY is required for live B.4.2 execution."
            )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict investment evidence recovery "
                        "classifier. Return only the requested JSON object."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "reasoning": {
                "effort": REASONING_EFFORT,
            },
            "response_format": {
                "type": "json_schema",
                "json_schema": self.RESPONSE_SCHEMA,
            },
            "provider": {
                "order": [self.provider],
                "allow_fallbacks": False,
                "require_parameters": True,
            },
        }

        body = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 2):
            request = Request(
                OPENROUTER_URL,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://openrouter.ai/",
                    "X-Title": "Investment OS B.4.2 parity",
                },
            )

            try:
                with urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    status = int(response.status)
                    raw = response.read().decode("utf-8")

                parsed_response = json.loads(raw)
                choice = parsed_response["choices"][0]
                message = choice["message"]

                content = message.get("content")
                if not isinstance(content, str):
                    raise SemanticContextRecoveryError(
                        "OpenRouter response content is not a string."
                    )

                parsed = json.loads(content)

                if not isinstance(parsed, dict):
                    raise SemanticContextRecoveryError(
                        "B.4.2 response is not an object."
                    )

                required = {
                    "same_proposition",
                    "field_supported",
                    "accepted",
                    "reason",
                }

                if set(parsed) != required:
                    raise SemanticContextRecoveryError(
                        "B.4.2 response schema mismatch."
                    )

                if not all(
                    isinstance(parsed[key], bool)
                    for key in (
                        "same_proposition",
                        "field_supported",
                        "accepted",
                    )
                ):
                    raise SemanticContextRecoveryError(
                        "B.4.2 Boolean response field has invalid type."
                    )

                if not isinstance(parsed["reason"], str):
                    raise SemanticContextRecoveryError(
                        "B.4.2 reason has invalid type."
                    )

                actual_provider = (
                    parsed_response.get("provider")
                    or choice.get("provider")
                    or message.get("provider")
                )

                # Some OpenRouter responses expose provider on the choice or
                # top-level response. If absent, retain None rather than invent.
                if actual_provider and str(actual_provider) != self.provider:
                    raise SemanticContextRecoveryError(
                        f"Provider drift: expected {self.provider}, "
                        f"got {actual_provider}"
                    )

                actual_model = (
                    choice.get("model")
                    or parsed_response.get("model")
                    or self.model
                )

                usage = parsed_response.get("usage")

                return {
                    "parsed": parsed,
                    "raw_response": content,
                    "http_status": status,
                    "attempts": attempt,
                    "retries": attempt - 1,
                    "provider": str(actual_provider) if actual_provider else self.provider,
                    "model": str(actual_model),
                    "finish_reason": choice.get("finish_reason"),
                    "usage": usage if isinstance(usage, dict) else None,
                }

            except HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504}:
                    raise
            except (URLError, TimeoutError) as exc:
                last_error = exc
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
            except SemanticContextRecoveryError as exc:
                last_error = exc

            if attempt <= self.max_retries:
                # Deliberately small deterministic backoff. Concurrency remains 1.
                time.sleep(min(2 ** (attempt - 1), 4))

        raise SemanticContextRecoveryError(
            f"B.4.2 request exhausted retries: {last_error}"
        )

    @staticmethod
    def prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def context_hash(window: ContextWindow) -> str:
        payload = json.dumps(
            window.as_dict(),
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
