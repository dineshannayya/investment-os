"""
Prompt construction for qualitative startup analysis.

This module is intentionally independent of any concrete LLM provider.

Responsibilities:
    - Convert structured startup analysis data into an LLM prompt.
    - Provide explicit analysis instructions.
    - Define the required JSON output contract.

Non-responsibilities:
    - Financial calculations.
    - LLM invocation.
    - Response parsing or validation.
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.models import LLMMessage
from app.schemas.analysis import (
    FinancialMetrics,
    StartupAnalysisInput,
)


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

   These values are authoritative and MUST be used exactly as supplied.

   Do NOT independently calculate, estimate, reinterpret, substitute,
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
   complete supplied source_facts and evidence.

   If a fact is present in source_facts or evidence, it MUST NOT
   be reported as missing merely because it is absent from another
   normalized field.

   This applies to founder experience, revenue streams, customers,
   customer acquisition information, financial information, market
   information, and other source-supported facts.

   "missing_information" is reserved only for information that is
   genuinely absent from the complete supplied input.

6. PRELIMINARY INVESTMENT RECOMMENDATION

   A preliminary investment recommendation is allowed when the available
   evidence is sufficient to form a meaningful investment view.

   Do not require complete information.

   The detailed recommendation policy below defines how to determine
   whether the available information is sufficient.

   The recommendation must remain explicitly preliminary and must not be
   presented as a final investment decision or a substitute for investor
   due diligence.

7. Be concise, factual, and suitable for an investment-review workflow.

8. Return ONLY valid JSON.

9. Do not wrap the JSON in Markdown code fences.

10. The JSON must contain ONLY the fields specified in the requested
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


def _build_input_payload(
    analysis_input: StartupAnalysisInput,
    metrics: FinancialMetrics,
) -> dict[str, Any]:
    """Build the structured payload supplied to the LLM."""

    startup_payload = analysis_input.model_dump(
        mode="json",
        exclude_none=True,
    )

    metrics_payload = metrics.model_dump(
        mode="json",
        exclude_none=True,
    )

    return {
        "startup": startup_payload,
        "deterministic_financial_metrics": metrics_payload,
    }


def build_startup_analysis_messages(
    analysis_input: StartupAnalysisInput,
    metrics: FinancialMetrics,
) -> tuple[LLMMessage, ...]:
    """
    Build provider-independent messages for startup analysis.

    The returned messages can be passed directly into an LLMRequest.
    """

    payload = _build_input_payload(
        analysis_input,
        metrics,
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
- Do not recalculate deterministic financial metrics.
- Use source_facts and evidence when assessing whether information
  is available.
- Do not list information in missing_information if it is already
  present in source_facts or evidence.
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


__all__ = [
    "STARTUP_ANALYSIS_SYSTEM_PROMPT",
    "OUTPUT_SCHEMA",
    "build_startup_analysis_messages",
]
