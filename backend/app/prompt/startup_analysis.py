"""
Prompt construction for qualitative startup analysis.

This module is intentionally independent of any concrete LLM provider.

Responsibilities:
    - Convert structured startup analysis data into an LLM prompt.
    - Project canonical evidence into a bounded synthesis payload.
    - Provide explicit analysis instructions.
    - Define the required JSON output contract.
    - Enforce a deterministic prompt payload budget.

Non-responsibilities:
    - Financial calculations.
    - LLM invocation.
    - Response parsing or validation.

Important architecture rule:

    StartupAnalysisInput is the canonical analysis input.

    The canonical evidence collection MUST NOT be modified or truncated
    merely to fit the LLM context window.

    Instead, this module creates a bounded LLM-facing projection of the
    canonical evidence.

    Canonical input:
        65 evidence records
        |
        +--> persistence / audit / downstream consumers
        |
        +--> bounded LLM synthesis projection
                    |
                    +--> Qwen
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.models import LLMMessage
from app.schemas.analysis import (
    AnalysisEvidence,
    FinancialMetrics,
    StartupAnalysisInput,
)


# ---------------------------------------------------------------------------
# Prompt budget
# ---------------------------------------------------------------------------

# The Qwen production context is currently 8192 tokens.
#
# STANDARD mode requests 768 output tokens.
#
# Therefore the theoretical input budget is:
#
#     8192 - 768 = 7424 tokens
#
# 18,000 characters is intentionally used as a conservative character-level
# synthesis payload budget. Character count is not a tokenizer substitute,
# but it provides an inexpensive deterministic guard before llama.cpp is
# invoked.
MAX_STARTUP_PAYLOAD_CHARS = 18_000


# ---------------------------------------------------------------------------
# Evidence projection budget
# ---------------------------------------------------------------------------

# Maximum number of canonical evidence records exposed to the LLM.
#
# This does NOT modify StartupAnalysisInput.evidence.
MAX_EVIDENCE_ITEMS = 24


# Maximum total serialized source-text characters contributed by evidence.
#
# Structured startup fields remain outside this budget.
MAX_EVIDENCE_CHARS = 10_000


# Maximum characters retained from a single evidence source_text.
#
# Long evidence records can otherwise dominate the synthesis prompt.
MAX_EVIDENCE_ITEM_CHARS = 600


# ---------------------------------------------------------------------------
# Evidence ranking
# ---------------------------------------------------------------------------

# Higher priority sections are more directly relevant to an investment
# decision. This ranking is deterministic and deliberately conservative.
#
# Unknown sections remain eligible and are ranked after known investment
# categories.
_EVIDENCE_SECTION_PRIORITY: dict[str, int] = {
    # Financial / valuation
    "valuation": 100,
    "revenue": 99,
    "financials": 98,
    "financial": 97,
    "ebitda": 96,
    "cash": 95,
    "burn_rate": 94,
    "runway": 93,
    "fundraising": 92,
    "funding": 91,
    "investment": 90,

    # Traction / customers
    "traction": 88,
    "customers": 87,
    "customer": 86,
    "sales": 85,
    "growth": 84,

    # Business
    "business_model": 82,
    "business_models": 82,
    "product": 80,
    "products": 79,
    "market": 78,
    "markets": 77,
    "competition": 75,
    "competitive": 74,

    # Founder / organization
    "founders": 72,
    "founder": 71,
    "management": 70,
    "team": 69,

    # Technology
    "technology": 65,
    "technologies": 64,
    "tech": 63,

    # Other useful investment signals
    "risk": 60,
    "risks": 60,
    "legal": 58,
    "regulatory": 57,
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

STARTUP_ANALYSIS_SYSTEM_PROMPT = """\
You are an investment analysis assistant for Investment OS.

Your task is to perform a structured qualitative analysis of a startup
using ONLY the information provided in the input.

Important rules:

1. Do not invent facts, numbers, customers, markets, competitors, founder
   experience, financial information, or other information that is not
   provided.

2. If information is not provided, do not infer it as fact. Identify it as
   missing information where appropriate.

3. Clearly distinguish between:
   - facts supported by the input,
   - reasonable observations based on those facts,
   - risks or concerns,
   - information that is missing and should be verified.

4. DETERMINISTIC FINANCIAL METRICS ARE AUTHORITATIVE.

   The field "deterministic_financial_metrics" contains financial
   metrics calculated by the application using deterministic logic.

   These values have already been calculated deterministically by the
   application. They are authoritative and MUST be used exactly as supplied.

   Do not recalculate, independently calculate, estimate, reinterpret, substitute,
   or replace any deterministic financial metric using raw financial
   values elsewhere in the input.

   In particular, if "revenue_multiple" is supplied, use that value
   when discussing the valuation-to-revenue multiple.

   Example:

       revenue_multiple = 3.4514925373

   means approximately 3.45x revenue.

   Do NOT interpret a valuation amount such as INR 9.25 crore as
   "9.25x revenue". The valuation amount and the valuation multiple
   are different facts.

   If a deterministic metric is supplied, it takes precedence over
   any independently calculated or inferred value.

5. SOURCE FACTS AND EVIDENCE ARE AUTHORITATIVE.

   The "source_facts" and "evidence" fields contain information
   extracted from supplied source documents.

   Before declaring information as missing, you MUST check the
   supplied source_facts and evidence.

   If a fact is present in source_facts or evidence, it MUST NOT
   be reported as missing merely because it is absent from another
   normalized field.

   This applies to founder experience, revenue streams, customers,
   customer acquisition information, financial information, market
   information, and other source-supported facts.

   "missing_information" is reserved only for information that is
   genuinely absent from the supplied input.

6. EVIDENCE PROJECTION.

   The evidence field is a bounded synthesis projection of the
   canonical evidence maintained by Investment OS.

   Evidence may therefore be a selected subset of the canonical
   evidence records.

   Use the supplied evidence as supporting source facts.

   Do not claim that a fact is absent merely because it is not present
   in the bounded evidence projection.

   Prefer explicit structured startup fields and deterministic financial
   metrics when available.

7. PRELIMINARY INVESTMENT RECOMMENDATION.

   A preliminary investment recommendation is allowed when the available
   evidence is sufficient to form a meaningful investment view.

   Do not require complete information.

   The detailed recommendation policy below defines how to determine
   whether the available information is sufficient.

   The recommendation must remain explicitly preliminary and must not be
   presented as a final investment decision or a substitute for investor
   due diligence.

8. Be concise, factual, and suitable for an investment-review workflow.

9. Return ONLY valid JSON.

10. Do not wrap the JSON in Markdown code fences.

11. The JSON must contain ONLY the fields specified in the requested
    output schema.

Allowed preliminary_recommendation values are exactly:
- "insufficient_information"
- "promising"
- "needs_further_diligence"
- "concerns"

RECOMMENDATION POLICY
=====================

The analysis may provide a preliminary investment recommendation even
when some information is missing.

Do NOT require 100% information completeness before making a preliminary
recommendation.

Use the following decision framework:

1. INFORMATION SUFFICIENCY

   Assess whether approximately 75% or more of the decision-relevant
   information is available from the supplied startup input, source_facts,
   evidence, and deterministic financial metrics.

   Decision-relevant information includes, where applicable:

   - company and product
   - founders and relevant experience
   - market
   - traction and customers
   - revenue and financial performance
   - fundraising and valuation
   - business model
   - competitive position
   - important risks

2. PRELIMINARY RECOMMENDATION

   If approximately 75% or more of the important information is available
   AND there is sufficient evidence to form a reasonable investment view,
   provide a preliminary recommendation.

   Missing non-critical information does NOT prevent a recommendation.

3. CRITICAL INFORMATION GAPS

   Do NOT provide a strong recommendation when a missing item is critical
   to the investment decision and could materially change the conclusion.

   Examples include:

   - inability to establish the actual valuation or investment terms
   - inability to establish basic revenue or financial performance
   - major unresolved legal or regulatory concerns
   - material debt or liability information that could change the investment
     case
   - inability to establish whether the claimed business actually exists
   - a major contradiction between important source documents

4. RECOMMENDATION OPTIONS

   "promising":
       Use when the available evidence supports a positive preliminary
       investment case and no critical unresolved issue dominates the case.

   "needs_further_diligence":
       Use when the startup appears potentially investable but important
       information remains unresolved or could materially affect the decision.

   "concerns":
       Use when the available evidence indicates material business,
       financial, market, founder, valuation, or execution concerns.

   "insufficient_information":
       Use only when the available information is substantially below the
       level required to form a meaningful preliminary investment view.

5. DO NOT TREAT MISSING INFORMATION AS AUTOMATICALLY NEGATIVE

   Missing information is not itself evidence of a negative attribute.

   Do not convert:

       "information not provided"

   into:

       "the company has a weakness."

   Instead, identify the information as missing and explain why it matters.

6. PRELIMINARY DOES NOT MEAN FINAL

   The recommendation is a preliminary investment assessment based only
   on the supplied evidence.

   It must not be presented as a final investment decision or as a
   substitute for investor due diligence.

OUTPUT CONSTRAINTS
==================

Return concise structured JSON.

List limits:
- strengths: maximum 3 items
- risks: maximum 3 items
- missing_information: maximum 3 items
- key_observations: maximum 3 items

Narrative limits:
- Each narrative field: maximum 1–2 concise sentences
- investment_thesis: maximum 2 sentences
- Do not repeat the same point across multiple fields
- Do not invent information that is not present in the input
- Use null when the available information is insufficient

Narrative fields:
- 1 concise sentence each
- Prefer 15–25 words
- Do not restate numerical data already provided
"""


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

OUTPUT_SCHEMA = {
    "company_overview": "string or null",
    "founder_assessment": "string or null",
    "product_assessment": "string or null",
    "market_assessment": "string or null",
    "traction_assessment": "string or null",
    "financial_assessment": "string or null",
    "valuation_assessment": "string or null",
    "business_model_assessment": "string or null",
    "competitive_assessment": "string or null",
    "strengths": ["string"],
    "risks": ["string"],
    "missing_information": ["string"],
    "key_observations": ["string"],
    "investment_thesis": "string or null",
    "preliminary_recommendation": (
        "insufficient_information | promising | "
        "needs_further_diligence | concerns"
    ),
}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _normalise_section(
    section: str | None,
) -> str:
    """Return a deterministic normalized evidence section name."""

    if not section:
        return ""

    return (
        section
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _section_priority(
    section: str | None,
) -> int:
    """Return deterministic investment relevance priority."""

    normalized = _normalise_section(section)

    if normalized in _EVIDENCE_SECTION_PRIORITY:
        return _EVIDENCE_SECTION_PRIORITY[
            normalized
        ]

    # Support compound section names such as:
    #     financial_metrics
    #     founder_experience
    #     customer_traction
    #
    # Match known terms conservatively.
    best = 0

    for key, priority in _EVIDENCE_SECTION_PRIORITY.items():
        if key in normalized:
            best = max(
                best,
                priority,
            )

    return best


def _evidence_text(
    evidence: AnalysisEvidence,
) -> str:
    """Return normalized source text for an evidence record."""

    text = evidence.source_text

    if text is None:
        return ""

    return " ".join(
        text.strip().split()
    )


def _evidence_confidence(
    evidence: AnalysisEvidence,
) -> float:
    """Return evidence confidence as a comparable float."""

    if evidence.confidence is None:
        return 0.0

    return float(
        evidence.confidence
    )


def _evidence_sort_key(
    item: tuple[int, AnalysisEvidence],
) -> tuple[int, float, int, int]:
    """
    Deterministic ranking key for evidence selection.

    Ranking order:
        1. investment relevance
        2. confidence
        3. shorter source text
        4. original input position

    Shorter text receives preference only as a tie-breaker. This prevents
    very large evidence records from dominating a category while retaining
    high-confidence and high-relevance records.
    """

    original_index, evidence = item

    text = _evidence_text(
        evidence,
    )

    return (
        -_section_priority(
            evidence.section,
        ),
        -_evidence_confidence(
            evidence,
        ),
        len(text),
        original_index,
    )


def _compact_evidence_item(
    evidence: AnalysisEvidence,
) -> dict[str, Any] | None:
    """
    Convert canonical AnalysisEvidence into a compact LLM-facing record.

    document_id is intentionally omitted from the LLM projection.

    The canonical AnalysisEvidence retained in StartupAnalysisInput remains
    unchanged and continues to carry document-level traceability.
    """

    text = _evidence_text(
        evidence,
    )

    if not text:
        return None

    if len(text) > MAX_EVIDENCE_ITEM_CHARS:
        text = (
            text[:MAX_EVIDENCE_ITEM_CHARS]
            .rstrip()
            + "…"
        )

    result: dict[str, Any] = {
        "section": evidence.section,
        "source_text": text,
    }

    if evidence.page is not None:
        result["page"] = evidence.page

    if evidence.confidence is not None:
        result["confidence"] = (
            float(evidence.confidence)
        )

    return result


# ---------------------------------------------------------------------------
# Evidence selection
# ---------------------------------------------------------------------------


def _select_evidence(
    evidence: list[AnalysisEvidence] | tuple[AnalysisEvidence, ...],
) -> list[dict[str, Any]]:
    """
    Select and compact evidence for LLM synthesis.

    The canonical evidence collection is never modified.

    Selection is deterministic and uses:
        - section relevance
        - confidence
        - compactness
        - original order

    A first pass provides category diversity so that the LLM does not receive
    only the highest-confidence records from a single section.

    A second pass fills the remaining budget with the highest-ranked records.
    """

    if not evidence:
        return []

    indexed = list(
        enumerate(evidence)
    )

    # Remove records with no usable source text.
    indexed = [
        item
        for item in indexed
        if _evidence_text(item[1])
    ]

    if not indexed:
        return []

    ranked = sorted(
        indexed,
        key=_evidence_sort_key,
    )

    selected_indices: set[int] = set()
    selected: list[dict[str, Any]] = []

    total_chars = 0
    sections_seen: set[str] = set()

    def try_add(
        original_index: int,
        item: AnalysisEvidence,
    ) -> bool:
        nonlocal total_chars

        if len(selected) >= MAX_EVIDENCE_ITEMS:
            return False

        if original_index in selected_indices:
            return False

        compact = _compact_evidence_item(
            item,
        )

        if compact is None:
            return False

        compact_chars = len(
            json.dumps(
                compact,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

        if (
            total_chars + compact_chars
            > MAX_EVIDENCE_CHARS
        ):
            return False

        selected.append(
            compact,
        )

        selected_indices.add(
            original_index,
        )

        total_chars += compact_chars

        normalized_section = _normalise_section(
            item.section,
        )

        if normalized_section:
            sections_seen.add(
                normalized_section,
            )

        return True

    # ------------------------------------------------------------------
    # Pass 1: category diversity
    #
    # Select the strongest record from each distinct section first.
    # ------------------------------------------------------------------

    for original_index, item in ranked:
        normalized_section = _normalise_section(
            item.section,
        )

        if (
            normalized_section
            and normalized_section in sections_seen
        ):
            continue

        if try_add(
            original_index,
            item,
        ):
            if len(selected) >= MAX_EVIDENCE_ITEMS:
                break

    # ------------------------------------------------------------------
    # Pass 2: fill remaining capacity by deterministic ranking.
    # ------------------------------------------------------------------

    for original_index, item in ranked:
        if len(selected) >= MAX_EVIDENCE_ITEMS:
            break

        try_add(
            original_index,
            item,
        )

    return selected


# ---------------------------------------------------------------------------
# Startup payload projection
# ---------------------------------------------------------------------------

def _build_startup_payload(
    analysis_input: StartupAnalysisInput,
) -> dict[str, Any]:
    """
    Build the bounded LLM-facing startup projection.

    The canonical StartupAnalysisInput is never modified.
    """

    def dump(value: Any) -> Any:
        if value is None:
            return None

        if hasattr(value, "model_dump"):
            return value.model_dump(
                mode="json",
                exclude_none=True,
            )

        if isinstance(value, (list, tuple)):
            return [
                dump(item)
                for item in value
            ]

        return value

    return {
        "company": dump(analysis_input.company),
        "founders": dump(analysis_input.founders),
        "fundraising": dump(analysis_input.fundraising),
        "product": dump(analysis_input.product),
        "market": dump(analysis_input.market),
        "traction": dump(analysis_input.traction),
        "financials": dump(analysis_input.financials),
        "business_model": dump(analysis_input.business_model),
        "evidence": _select_evidence(
            analysis_input.evidence or [],
        ),
    }


def _build_input_payload(
    analysis_input: StartupAnalysisInput,
    metrics: FinancialMetrics,
) -> dict[str, Any]:
    """Build the bounded structured payload supplied to the LLM."""

    startup_payload = _build_startup_payload(
        analysis_input,
    )

    metrics_payload = metrics.model_dump(
        mode="json",
        exclude_none=True,
    )

    return {
        "startup": startup_payload,
        "deterministic_financial_metrics": metrics_payload,
    }


# ---------------------------------------------------------------------------
# Payload budget enforcement
# ---------------------------------------------------------------------------


def _serialize_payload(
    payload: dict[str, Any],
) -> str:
    """Serialize payload deterministically for prompt construction."""

    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )


def _enforce_payload_budget(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Enforce the synthesis payload character budget.

    Evidence selection should normally make the payload fit.

    This function remains as a final guard against unexpected growth in
    structured document-intelligence fields.

    It deliberately does NOT mutate or truncate canonical input.
    """

    serialized = _serialize_payload(
        payload,
    )

    if len(serialized) <= MAX_STARTUP_PAYLOAD_CHARS:
        return payload

    startup_payload = payload.get(
        "startup",
    )

    if not isinstance(
        startup_payload,
        dict,
    ):
        raise ValueError(
            "Startup analysis synthesis payload exceeds the configured "
            "character budget of "
            f"{MAX_STARTUP_PAYLOAD_CHARS}. "
            "Structured startup payload cannot be reduced safely."
        )

    evidence = startup_payload.get(
        "evidence",
    )

    if not isinstance(
        evidence,
        list,
    ):
        evidence = []

    # Deterministically remove the least useful evidence records until the
    # serialized payload fits.
    #
    # At this stage the evidence has already been ranked. Removing from the
    # tail therefore removes the lowest-priority projected evidence first.
    while evidence:
        candidate = dict(payload)

        candidate_startup = dict(
            startup_payload,
        )

        candidate_startup["evidence"] = (
            evidence[:-1]
        )

        candidate["startup"] = (
            candidate_startup
        )

        if (
            len(
                _serialize_payload(
                    candidate,
                )
            )
            <= MAX_STARTUP_PAYLOAD_CHARS
        ):
            return candidate

        evidence = evidence[:-1]

    # If even zero evidence cannot fit, structured fields themselves are
    # larger than the configured budget. Do not silently discard structured
    # investment information.
    candidate = dict(payload)

    candidate_startup = dict(
        startup_payload,
    )

    candidate_startup["evidence"] = []

    candidate["startup"] = (
        candidate_startup
    )

    if (
        len(
            _serialize_payload(
                candidate,
            )
        )
        <= MAX_STARTUP_PAYLOAD_CHARS
    ):
        return candidate

    raise ValueError(
        "Startup analysis synthesis payload exceeds the configured "
        f"character budget of {MAX_STARTUP_PAYLOAD_CHARS}. "
        "Reduce the size of structured document-intelligence fields "
        "before invoking the LLM."
    )


# ---------------------------------------------------------------------------
# Message construction
# ---------------------------------------------------------------------------


def build_startup_analysis_messages(
    analysis_input: StartupAnalysisInput,
    metrics: FinancialMetrics,
) -> tuple[LLMMessage, ...]:
    """
    Build provider-independent messages for startup analysis.

    The returned messages can be passed directly into an LLMRequest.

    The canonical StartupAnalysisInput is never mutated.

    The user message contains a bounded synthesis projection suitable for
    the configured Qwen context window.
    """

    payload = _build_input_payload(
        analysis_input,
        metrics,
    )

    payload = _enforce_payload_budget(
        payload,
    )

    user_prompt = f"""\
Analyze the following startup.

STARTUP INPUT
=============

{json.dumps(
    payload,
    indent=2,
    ensure_ascii=False,
)}

OUTPUT REQUIREMENTS
===================

Return ONLY a JSON object matching the following structure:

{json.dumps(
    OUTPUT_SCHEMA,
    indent=2,
    ensure_ascii=False,
)}

For every assessment:

- Use null when there is insufficient information.
- Do not invent missing information.
- Treat deterministic_financial_metrics as authoritative.
- Treat deterministic financial metrics as authoritative application-generated facts.
- Use source_facts and evidence when assessing whether information
  is available.
- Evidence is a bounded synthesis projection of canonical source evidence.
- Prefer explicit structured startup fields when available.
- Do not list information in missing_information if it is already
  present in the supplied startup fields or evidence.
- Put only genuinely absent information in missing_information.
- Put concrete positive attributes in strengths.
- Put concrete concerns in risks.
- Put useful derived observations in key_observations.
- Make the preliminary recommendation evidence-based.
- Do not avoid a recommendation merely because non-critical information
  is missing.
- Use "needs_further_diligence" when important unresolved information
  could materially affect the investment conclusion.
"""

    return (
        LLMMessage(
            role="system",
            content=STARTUP_ANALYSIS_SYSTEM_PROMPT,
        ),
        LLMMessage(
            role="user",
            content=user_prompt,
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "STARTUP_ANALYSIS_SYSTEM_PROMPT",
    "OUTPUT_SCHEMA",
    "MAX_STARTUP_PAYLOAD_CHARS",
    "MAX_EVIDENCE_ITEMS",
    "MAX_EVIDENCE_CHARS",
    "MAX_EVIDENCE_ITEM_CHARS",
    "build_startup_analysis_messages",
]
