from __future__ import annotations

import json
from pathlib import Path

from app.llm.models import LLMMessage, LLMRequest
from app.llm.providers.qwen import QwenProvider
from app.models.investment_scorecard import InvestmentScorecard
from app.services.dimension_evidence_loader import (
    DimensionEvidenceLoader,
)
from app.services.investment_scorecard_evaluation import (
    InvestmentScorecardEvaluationService,
)


print("=" * 88)
print(
    "C.7.7.7.DAY-1.7.5.3.1 — "
    "REAL QWEN RESTOMART EVALUATION"
)
print("=" * 88)


# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT = Path("/opt/investment-os")

STARTUP_ROOT = (
    ROOT
    / "data"
    / "real_startups"
    / "restomart"
)

SCORECARD_PATH = (
    STARTUP_ROOT
    / "investment_scorecard.json"
)

DIMENSION_EVIDENCE_PATH = (
    STARTUP_ROOT
    / "dimension_evidence.json"
)

STARTUP_NAME = "RestoMart"

TEMPERATURE = 0.0
MAX_TOKENS = 2048
THINKING_ENABLED = False


# ============================================================================
# HELPERS
# ============================================================================


def print_dimension_evidence(
    evidence_set,
    scorecard,
) -> None:
    print()
    print("=" * 88)
    print("DIMENSION-SPECIFIC EVIDENCE")
    print("=" * 88)

    for index, dimension in enumerate(
        scorecard.dimensions,
        start=1,
    ):
        routed = (
            evidence_set.dimensions.get(
                dimension.id
            )
        )

        evidence = (
            routed.evidence
            if routed is not None
            else []
        )

        print()
        print(
            f"{index:2}. "
            f"{dimension.id:32} "
            f"evidence={len(evidence)}"
        )

        for item in evidence:
            print(
                f"      {item.evidence_ref:36} "
                f"{item.source_type}"
            )


def print_results(result) -> None:
    print()
    print("=" * 88)
    print("MULTI-DIMENSION RESULT")
    print("=" * 88)

    print(
        f"startup     : {result.startup_name}"
    )

    print(
        f"scorecard   : {result.scorecard_version}"
    )

    print(
        f"evaluations : {len(result.evaluations)}"
    )

    print()
    print(
        f"{'#':>2} "
        f"{'DIMENSION':32} "
        f"{'SCORE':>5} "
        f"{'CONF':>6} "
        f"{'EVIDENCE':>9} "
        f"{'RISKS':>7} "
        f"{'MISSING':>8}"
    )

    print("-" * 88)

    for index, evaluation in enumerate(
        result.evaluations,
        start=1,
    ):
        print(
            f"{index:2} "
            f"{evaluation.dimension_id:32} "
            f"{evaluation.score:5} "
            f"{evaluation.confidence:6} "
            f"{len(evaluation.evidence):9} "
            f"{len(evaluation.risk_observations):7} "
            f"{len(evaluation.missing_information):8}"
        )


def print_detailed_results(result) -> None:
    print()
    print("=" * 88)
    print("DETAILED DIMENSION RESULTS")
    print("=" * 88)

    for index, evaluation in enumerate(
        result.evaluations,
        start=1,
    ):
        print()
        print("-" * 88)
        print(
            f"{index:2}. {evaluation.dimension_id}"
        )
        print("-" * 88)

        print(
            f"score      : {evaluation.score}"
        )

        print(
            f"confidence : {evaluation.confidence}"
        )

        print()
        print("evidence:")

        if evaluation.evidence:
            for item in evaluation.evidence:
                print(
                    f"  - {item.evidence_ref}: "
                    f"{item.observation}"
                )
        else:
            print("  - NONE")

        print()
        print("positive_observations:")

        if evaluation.positive_observations:
            for item in evaluation.positive_observations:
                print(f"  - {item}")
        else:
            print("  - NONE")

        print()
        print("risk_observations:")

        if evaluation.risk_observations:
            for risk in evaluation.risk_observations:
                print(
                    f"  - {risk.risk}"
                    f" [{risk.severity}]"
                )
                print(
                    f"    impact: {risk.impact}"
                )
                print(
                    "    evidence_refs: "
                    f"{risk.evidence_refs}"
                )
        else:
            print("  - NONE")

        print()
        print("missing_information:")

        if evaluation.missing_information:
            for item in evaluation.missing_information:
                print(f"  - {item}")
        else:
            print("  - NONE")

        print()
        print("reasoning:")
        print(evaluation.reasoning)


# ============================================================================
# LOAD SCORECARD
# ============================================================================

print()
print("=" * 88)
print("CONFIGURATION")
print("=" * 88)

print(
    f"startup             : {STARTUP_NAME}"
)

print(
    f"scorecard           : {SCORECARD_PATH}"
)

print(
    f"dimension evidence  : {DIMENSION_EVIDENCE_PATH}"
)

print(
    f"temperature         : {TEMPERATURE}"
)

print(
    f"max_tokens          : {MAX_TOKENS}"
)

print(
    f"thinking_enabled    : {THINKING_ENABLED}"
)


print()
print("=" * 88)
print("SCORECARD")
print("=" * 88)

with SCORECARD_PATH.open(
    "r",
    encoding="utf-8",
) as handle:
    scorecard_payload = json.load(handle)

scorecard = InvestmentScorecard.model_validate(
    scorecard_payload
)

print(
    f"name       : {scorecard.scorecard.name}"
)

print(
    f"version    : {scorecard.scorecard.version}"
)

print(
    f"dimensions : {len(scorecard.dimensions)}"
)

for index, dimension in enumerate(
    scorecard.dimensions,
    start=1,
):
    print(
        f"{index:2}. "
        f"{dimension.id:32} "
        f"weight={dimension.weight}"
    )


# ============================================================================
# LOAD DIMENSION EVIDENCE
# ============================================================================

print()
print("=" * 88)
print("LOAD DIMENSION EVIDENCE")
print("=" * 88)

evidence_set = (
    DimensionEvidenceLoader.load_for_scorecard(
        path=DIMENSION_EVIDENCE_PATH,
        scorecard=scorecard,
    )
)

print(
    f"startup : {evidence_set.startup}"
)

print(
    f"dimensions configured : "
    f"{len(evidence_set.dimensions)}"
)

print_dimension_evidence(
    evidence_set,
    scorecard,
)


# ============================================================================
# REAL QWEN
# ============================================================================

print()
print("=" * 88)
print("REAL QWEN 10-DIMENSION EXECUTION")
print("=" * 88)

provider = QwenProvider()

service = InvestmentScorecardEvaluationService(
    provider=provider,
)

result = service.evaluate(
    scorecard=scorecard,
    startup_name=STARTUP_NAME,
    evidence_set=evidence_set,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    thinking_enabled=THINKING_ENABLED,
)


# ============================================================================
# RESULT
# ============================================================================

print_results(result)

print_detailed_results(result)


# ============================================================================
# COVERAGE
# ============================================================================

expected_ids = [
    dimension.id
    for dimension in scorecard.dimensions
]

actual_ids = [
    evaluation.dimension_id
    for evaluation in result.evaluations
]

print()
print("=" * 88)
print("DIMENSION COVERAGE")
print("=" * 88)

print(
    f"expected : {expected_ids}"
)

print(
    f"actual   : {actual_ids}"
)

assert actual_ids == expected_ids

assert len(result.evaluations) == len(
    scorecard.dimensions
)

print()
print(
    "[PASS] All scorecard dimensions evaluated"
)

print(
    "[PASS] Dimension ordering preserved"
)

print(
    "[PASS] Dimension evidence loaded through "
    "production loader"
)

print(
    "[PASS] Dimension-specific evidence routed "
    "through production service"
)

print(
    "[PASS] Structured parser accepted all "
    "Qwen responses"
)

print()
print("=" * 88)
print(
    "C.7.7.7.DAY-1.7.5.3.1 RESULT : PASS"
)
print("=" * 88)
