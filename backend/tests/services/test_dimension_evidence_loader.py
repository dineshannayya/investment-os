import json
from pathlib import Path

import pytest

from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceItem,
    DimensionEvidenceSet,
)
from app.models.investment_scorecard import (
    InvestmentScorecard,
)
from app.services.dimension_evidence_loader import (
    DimensionEvidenceLoader,
)

ROOT = Path(__file__).parents[2]

RESTOMART_SCORECARD_PATH = (
    ROOT
    / "data"
    / "real_startups"
    / "restomart"
    / "investment_scorecard.json"
)

RESTOMART_EVIDENCE_PATH = (
    ROOT
    / "data"
    / "real_startups"
    / "restomart"
    / "dimension_evidence.json"
)

def make_scorecard() -> InvestmentScorecard:
    with RESTOMART_SCORECARD_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    return InvestmentScorecard.model_validate(
        payload,
    )

def make_evidence_set() -> DimensionEvidenceSet:
    return DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "founder_team": DimensionEvidence(
                evidence=[
                    DimensionEvidenceItem(
                        evidence_ref="founders_2025",
                        observation="Three founders are identified.",
                        source_type="startup_database",
                    )
                ]
            ),
            "commercial_traction": DimensionEvidence(
                evidence=[
                    DimensionEvidenceItem(
                        evidence_ref="financials_revenue",
                        observation=(
                            "Reported revenue is INR 2.68 crore."
                        ),
                        source_type="financial_document",
                    )
                ]
            ),
        },
    )


def test_load_reads_and_validates_json(tmp_path: Path):
    path = tmp_path / "dimension_evidence.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "startup": "RestoMart",
                "dimensions": {
                    "commercial_traction": {
                        "evidence": [
                            {
                                "evidence_ref": "financials_revenue",
                                "observation": (
                                    "Revenue is INR 2.68 crore."
                                ),
                                "source_type": "financial_document",
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = DimensionEvidenceLoader.load(path)

    assert result.startup == "RestoMart"
    assert (
        result.dimensions[
            "commercial_traction"
        ].evidence[0].evidence_ref
        == "financials_revenue"
    )


def test_load_rejects_missing_file(tmp_path: Path):
    path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Dimension evidence file not found",
    ):
        DimensionEvidenceLoader.load(path)


def test_load_rejects_directory(tmp_path: Path):
    path = tmp_path / "evidence"

    path.mkdir()

    with pytest.raises(
        ValueError,
        match="is not a file",
    ):
        DimensionEvidenceLoader.load(path)


def test_load_rejects_invalid_json(tmp_path: Path):
    path = tmp_path / "dimension_evidence.json"

    path.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        DimensionEvidenceLoader.load(path)


def test_load_rejects_invalid_schema(tmp_path: Path):
    path = tmp_path / "dimension_evidence.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "startup": "RestoMart",
                "dimensions": {
                    "commercial_traction": {
                        "evidence": [
                            {
                                "evidence_ref": "financials",
                                "observation": "",
                                "source_type": "financial_document",
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid dimension evidence structure",
    ):
        DimensionEvidenceLoader.load(path)


def test_get_dimension_evidence_returns_requested_dimension():
    evidence_set = make_evidence_set()

    result = (
        DimensionEvidenceLoader.get_dimension_evidence(
            evidence_set,
            "commercial_traction",
        )
    )

    assert len(result.evidence) == 1
    assert (
        result.evidence[0].evidence_ref
        == "financials_revenue"
    )


def test_get_dimension_evidence_returns_empty_for_missing_dimension():
    evidence_set = make_evidence_set()

    result = (
        DimensionEvidenceLoader.get_dimension_evidence(
            evidence_set,
            "market_tam",
        )
    )

    assert result.evidence == []


def test_get_dimension_evidence_rejects_empty_dimension_id():
    evidence_set = make_evidence_set()

    with pytest.raises(
        ValueError,
        match="dimension_id must not be empty",
    ):
        DimensionEvidenceLoader.get_dimension_evidence(
            evidence_set,
            "",
        )


def test_validate_dimension_coverage_accepts_matching_dimensions():
    scorecard = make_scorecard()
    evidence_set = make_evidence_set()

    DimensionEvidenceLoader.validate_dimension_coverage(
        scorecard=scorecard,
        evidence_set=evidence_set,
    )


def test_validate_dimension_coverage_allows_missing_evidence():
    scorecard = make_scorecard()

    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "commercial_traction": DimensionEvidence(
                evidence=[]
            )
        },
    )

    DimensionEvidenceLoader.validate_dimension_coverage(
        scorecard=scorecard,
        evidence_set=evidence_set,
    )


def test_validate_dimension_coverage_rejects_unknown_dimension():
    scorecard = make_scorecard()

    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "commercial_tracion": DimensionEvidence(
                evidence=[]
            )
        },
    )

    with pytest.raises(
        ValueError,
        match="Unexpected dimension evidence",
    ):
        DimensionEvidenceLoader.validate_dimension_coverage(
            scorecard=scorecard,
            evidence_set=evidence_set,
        )


def test_load_for_scorecard_validates_dimension_coverage(
    tmp_path: Path,
):
    path = tmp_path / "dimension_evidence.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "startup": "RestoMart",
                "dimensions": {
                    "commercial_traction": {
                        "evidence": []
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    scorecard = make_scorecard()

    result = (
        DimensionEvidenceLoader.load_for_scorecard(
            path=path,
            scorecard=scorecard,
        )
    )

    assert result.startup == "RestoMart"
    assert (
        result.dimensions[
            "commercial_traction"
        ].evidence
        == []
    )


def test_load_for_scorecard_rejects_unknown_dimension(
    tmp_path: Path,
):
    path = tmp_path / "dimension_evidence.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "startup": "RestoMart",
                "dimensions": {
                    "unknown_dimension": {
                        "evidence": []
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    scorecard = make_scorecard()

    with pytest.raises(
        ValueError,
        match="Unexpected dimension evidence",
    ):
        DimensionEvidenceLoader.load_for_scorecard(
            path=path,
            scorecard=scorecard,
        )

def test_restomart_dimension_routing():
    result = DimensionEvidenceLoader.load(
        RESTOMART_EVIDENCE_PATH,
    )

    commercial = DimensionEvidenceLoader.get_dimension_evidence(
        result,
        "commercial_traction",
    )

    refs = {
        item.evidence_ref
        for item in commercial.evidence
    }

    assert {
        "mis_fy25_net_sales",
        "mis_fy26_net_sales",
        "mis_active_customers",
        "mis_customer_churn",
        "mis_revenue_concentration",
        "mis_orders_aov",
        "mis_fill_rate",
    }.issubset(refs)

    valuation = DimensionEvidenceLoader.get_dimension_evidence(
        result,
        "valuation_deal_terms",
    )

    valuation_refs = {
        item.evidence_ref
        for item in valuation.evidence
    }

    assert {
        "investment_note_round",
        "investment_note_projection",
        "sha_round_size",
        "sha_investor_subscriptions",
        "sha_ccps_terms",
        "sha_ccps_voting",
        "sha_liquidation_preference",
        "sha_anti_dilution",
        "sha_valuation_condition",
    }.issubset(valuation_refs)
