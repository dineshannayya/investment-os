from __future__ import annotations

import json
from typing import Any

from app.models.investment_scorecard import InvestmentScorecard


SYSTEM_PROMPT = """
You are an investment-analysis assistant for a personal Investment OS.

Your task is to evaluate ONE investment dimension using ONLY:

1. The supplied startup evidence.
2. The supplied investment dimension specification.
3. The supplied investor preferences.

STRICT RULES:

EVIDENCE
1. Do not invent facts.
2. Do not assume information that is not present in the supplied evidence.
3. Distinguish factual evidence from interpretation.
4. Preserve supplied evidence references.
5. Do not treat unsupported claims as verified facts.

MISSING INFORMATION
6. Missing information is NOT negative evidence.
7. Report missing information separately.
8. Do not manufacture a negative score because information is missing.
9. Missing information may reduce confidence when it materially limits evaluation.

RISK
10. Separate risks from missing information.
11. Identify specific, material investment risks.
12. Do not convert every uncertainty into a risk.
13. Do not duplicate the same risk merely to increase its importance.
14. Reference supporting evidence where available.
15. Respect all supplied "do_not_assume" constraints.

SCORING
16. Score this dimension from 0 to 100.
17. Use the supplied scoring guidance for this dimension.
18. Score only the evidence-supported condition of this dimension.
19. Do not use a default or neutral score.
20. Do not assume 67 is a neutral, typical, or preferred score.
21. First assess the strength of the positive evidence.
22. Then assess the strength of the negative or risk evidence.
23. Consider the materiality and durability of the evidence.
24. Select the scoring band that best matches the evidence.
25. Select a specific score within that band based on the evidence.
26. Missing information may reduce confidence, but must not by itself
    reduce the score.
27. Confidence must be from 0 to 100.
28. Confidence represents confidence in the evaluation, NOT investment quality.
29. Confidence should reflect the completeness, quality, consistency,
    and relevance of the supplied evidence.
30. Do not use a default confidence value.

WEIGHTING
31. Do NOT apply investment weight.
32. Do NOT calculate weighted score.
33. Do NOT calculate overall investment score.
34. Dimension weight is NOT part of the AI evaluation.

INVESTMENT DECISION
35. Do NOT produce an overall investment recommendation.
36. Do NOT say invest or do not invest.
37. The deterministic Investment OS engine will apply weights,
    aggregate dimension scores, evaluate risks, and support the
    final investor decision.

OUTPUT
38. Return ONLY the requested structured dimension evaluation.
39. dimension_id must exactly match the requested dimension.
40. Keep reasoning concise and evidence-based.

SCORE OUTPUT RULE:

The "score" field MUST contain exactly one numeric value.

The score must be between 0 and 100 inclusive.

Do not return a score range.
Do not return a percentile range.
Do not return explanatory text in the score field.

SCORING GUIDANCE INTERPRETATION:

The dimension specification contains scoring_guidance with score bands.

Use those bands as the primary calibration framework.

Do not choose a score merely because it is near the middle of
the 0-100 range.

A score near the middle must be supported by the evidence.

MISSING INFORMATION OUTPUT:

Report unavailable information under missing_information.

Each item may contain:
- item: the unavailable information
- reason: why it matters to evaluating this dimension

Missing information is not negative evidence.

Do not create a risk merely because information is unavailable.

OUTPUT CONSTRUCTION:

Before producing the JSON:

1. Determine the dimension's evidence-supported condition.
2. Determine the applicable scoring band.
3. Select the actual numeric score.
4. Determine confidence based on evidence completeness and quality.
5. Populate the JSON with those calculated values.

The JSON structure shown below is a STRUCTURE EXAMPLE ONLY.

Do NOT copy numeric placeholder values from the example.
Do NOT treat placeholder values as recommended scores.
""".strip()


def build_scorecard_system_prompt() -> str:
    """Return the immutable scorecard evaluation system prompt."""
    return SYSTEM_PROMPT


def _find_dimension(
    *,
    scorecard: InvestmentScorecard,
    dimension_id: str,
):
    """Find a dimension by its canonical ID."""

    dimension = next(
        (
            item
            for item in scorecard.dimensions
            if item.id == dimension_id
        ),
        None,
    )

    if dimension is None:
        raise ValueError(
            f"Unknown investment dimension: {dimension_id}"
        )

    return dimension


def _build_dimension_specification(dimension) -> dict[str, Any]:
    """
    Build the dimension specification sent to the LLM.

    Weight is deliberately excluded because weighting is a
    deterministic Investment OS operation.
    """

    return dimension.model_dump(
        mode="json",
        exclude={"weight"},
    )

def _build_evaluation_principles(
    scorecard: InvestmentScorecard,
) -> dict:
    principles = scorecard.evaluation_principles

    return {
        "evidence_semantics": {
            "missing_information_is_not_negative_evidence": (
                principles.evidence_semantics
                .missing_information_is_not_negative_evidence
            ),
            "absence_of_evidence_is_not_evidence_of_negative_condition": (
                principles.evidence_semantics
                .absence_of_evidence_is_not_evidence_of_negative_condition
            ),
            "risk_requires_supporting_evidence": (
                principles.evidence_semantics
                .risk_requires_supporting_evidence
            ),
        },
        "missing_information_rule": {
            "title": (
                principles.missing_information_rule.title
            ),
            "rules": (
                principles.missing_information_rule.rules
            ),
        },
    }

def build_dimension_evaluation_prompt(
    *,
    scorecard: InvestmentScorecard,
    dimension_id: str,
    startup_name: str,
    startup_evidence: list[dict[str, Any]],
) -> str:
    """Build the user prompt for one investment dimension."""

    dimension = _find_dimension(
        scorecard=scorecard,
        dimension_id=dimension_id,
    )

    payload = {
        "startup": {
            "name": startup_name,
        },
        "investor_profile": (
            scorecard.investor_profile.model_dump(mode="json")
        ),

        "evaluation_principles": _build_evaluation_principles(
            scorecard
        ),
        "dimension": _build_dimension_specification(
            dimension
        ),
        "evidence": startup_evidence,
        "required_output": {
            "dimension_id": dimension_id,

            # Placeholder only. Qwen must calculate actual values.
            "score": 0,
 
            # Placeholder only. Qwen must calculate actual values.
            "confidence": 0,
            "evidence": [
                {
                    "evidence_ref": "reference to supplied evidence",
                    "observation": "fact supported by evidence",
                    "source_type": "source type",
                }
            ],
            "positive_observations": [],
            "risk_observations": [
                {
                    "risk": "specific material risk",
                    "severity": "low|medium|high|critical",
                    "impact": "specific investment impact",
                    "evidence_refs": [],
                }
            ],
            "missing_information": [
              {
                "item": "specific unavailable information",
                "reason": "why this information is relevant to the dimension"
              }
            ],

            "reasoning": "concise evidence-based reasoning",
        },
    }

    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    )


def build_dimension_evaluation_messages(
    *,
    scorecard: InvestmentScorecard,
    dimension_id: str,
    startup_name: str,
    startup_evidence: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build messages suitable for the LLM provider."""

    return [
        {
            "role": "system",
            "content": build_scorecard_system_prompt(),
        },
        {
            "role": "user",
            "content": build_dimension_evaluation_prompt(
                scorecard=scorecard,
                dimension_id=dimension_id,
                startup_name=startup_name,
                startup_evidence=startup_evidence,
            ),
        },
    ]


