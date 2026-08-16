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

4. Financial metrics supplied in the input have already been calculated deterministically 
   by the application. Treat them as supplied facts.
   Do NOT recalculate them or replace them with your own calculations.

5. Do not make a final investment decision. Provide only a preliminary
   qualitative recommendation.

6. Be concise, factual, and suitable for an investment-review workflow.

7. Return ONLY valid JSON.

8. Do not wrap the JSON in Markdown code fences.

9. The JSON must contain ONLY the fields specified in the requested
   output schema.

Allowed preliminary_recommendation values are exactly:
- "insufficient_information"
- "promising"
- "needs_further_diligence"
- "concerns"
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
- Put information that should be verified in missing_information.
- Put concrete positive attributes in strengths.
- Put concrete concerns in risks.
- Put useful derived observations in key_observations.
- Keep the preliminary recommendation conservative.
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
