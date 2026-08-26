import json
from pathlib import Path

from app.models.investment_scorecard import InvestmentScorecard
from app.services.investment_scorecard_evaluation import (
    InvestmentScorecardEvaluationService,
)


ROOT = Path("/opt/investment-os")

SCORECARD_PATH = (
    ROOT
    / "data"
    / "real_startups"
    / "restomart"
    / "investment_scorecard.json"
)


print("=" * 88)
print(
    "C.7.7.7.DAY-1.7.3 — "
    "REAL QWEN 10-DIMENSION RESTOMART EVALUATION"
)
print("=" * 88)


# ============================================================================
# SCORECARD
# ============================================================================

data = json.loads(
    SCORECARD_PATH.read_text(encoding="utf-8")
)

scorecard = InvestmentScorecard.model_validate(data)

print()
print("=" * 88)
print("SCORECARD")
print("=" * 88)

print("name       :", scorecard.scorecard.name)
print("version    :", scorecard.scorecard.version)
print("dimensions :", len(scorecard.dimensions))

for index, dimension in enumerate(
    scorecard.dimensions,
    start=1,
):
    print(
        f"{index:2}. "
        f"{dimension.id:30} "
        f"weight={dimension.weight}"
    )

assert len(scorecard.dimensions) == 10


# ============================================================================
# EVIDENCE
# ============================================================================

startup_evidence = [
    {
        "evidence_ref": "financials_2025",
        "observation": "Revenue is INR 2.68 crore.",
        "source_type": "financial_document",
    },
    {
        "evidence_ref": "startup_database_founders",
        "observation": "Three founders are identified.",
        "source_type": "startup_database",
    },
]


print()
print("=" * 88)
print("EVIDENCE")
print("=" * 88)

for item in startup_evidence:
    print(
        f"{item['evidence_ref']:30} "
        f"{item['source_type']:25} "
        f"{item['observation']}"
    )


# ============================================================================
# REAL QWEN
# ============================================================================

print()
print("=" * 88)
print("REAL QWEN 10-DIMENSION EXECUTION")
print("=" * 88)

service = InvestmentScorecardEvaluationService()

result = service.evaluate(
    scorecard=scorecard,
    startup_name="RestoMart",
    startup_evidence=startup_evidence,
    temperature=0.0,
    max_tokens=768,
    thinking_enabled=False,
)


# ============================================================================
# RESULT
# ============================================================================

print()
print("=" * 88)
print("MULTI-DIMENSION RESULT")
print("=" * 88)

print("startup        :", result.startup_name)
print("scorecard      :", result.scorecard_version)
print("evaluations    :", len(result.evaluations))

assert result.startup_name == "RestoMart"
assert result.scorecard_version == scorecard.scorecard.version
assert len(result.evaluations) == 10


print()
print(
    f"{'#':>2} "
    f"{'DIMENSION':30} "
    f"{'SCORE':>6} "
    f"{'CONF':>6} "
    f"{'RISKS':>6} "
    f"{'MISSING':>8}"
)
print("-" * 88)

for index, evaluation in enumerate(
    result.evaluations,
    start=1,
):
    print(
        f"{index:2} "
        f"{evaluation.dimension_id:30} "
        f"{evaluation.score:6} "
        f"{evaluation.confidence:6} "
        f"{len(evaluation.risk_observations):6} "
        f"{len(evaluation.missing_information):8}"
    )


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

print("expected :", expected_ids)
print("actual   :", actual_ids)

assert actual_ids == expected_ids

print()
print("[PASS] All 10 dimensions evaluated")
print("[PASS] Dimension ordering preserved")
print("[PASS] Structured parser accepted all responses")
print("[PASS] Dimension coverage validated")
print()
print("=" * 88)
print("C.7.7.7.DAY-1.7.3 RESULT : PASS")
print("=" * 88)
