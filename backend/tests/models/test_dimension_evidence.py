import pytest
import json
from pathlib import Path
from pydantic import ValidationError

from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceItem,
    DimensionEvidenceSet,
)



def test_dimension_evidence_item_accepts_valid_evidence():
    evidence = DimensionEvidenceItem(
        evidence_ref="financials_2025",
        observation="Reported revenue is INR 2.68 crore.",
        source_type="financial_document",
    )

    assert evidence.evidence_ref == "financials_2025"
    assert evidence.observation == (
        "Reported revenue is INR 2.68 crore."
    )
    assert evidence.source_type == "financial_document"


def test_dimension_evidence_item_rejects_empty_evidence_ref():
    with pytest.raises(ValidationError):
        DimensionEvidenceItem(
            evidence_ref="",
            observation="Revenue is INR 2.68 crore.",
            source_type="financial_document",
        )


def test_dimension_evidence_item_rejects_empty_observation():
    with pytest.raises(ValidationError):
        DimensionEvidenceItem(
            evidence_ref="financials_2025",
            observation="",
            source_type="financial_document",
        )


def test_dimension_evidence_item_rejects_empty_source_type():
    with pytest.raises(ValidationError):
        DimensionEvidenceItem(
            evidence_ref="financials_2025",
            observation="Revenue is INR 2.68 crore.",
            source_type="",
        )


def test_dimension_evidence_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        DimensionEvidence(
            evidence=[],
            unexpected_field="not_allowed",
        )


def test_dimension_evidence_set_accepts_empty_dimension_evidence():
    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "market_tam": DimensionEvidence(
                evidence=[],
            ),
        },
    )

    assert evidence_set.startup == "RestoMart"
    assert evidence_set.dimensions["market_tam"].evidence == []


def test_dimension_evidence_set_accepts_dimension_evidence():
    evidence_set = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "commercial_traction": DimensionEvidence(
                evidence=[
                    DimensionEvidenceItem(
                        evidence_ref="financials_2025",
                        observation=(
                            "Reported revenue is INR 2.68 crore."
                        ),
                        source_type="financial_document",
                    ),
                ],
            ),
        },
    )

    evidence = evidence_set.dimensions[
        "commercial_traction"
    ].evidence

    assert len(evidence) == 1
    assert evidence[0].evidence_ref == "financials_2025"


def test_dimension_evidence_set_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        DimensionEvidenceSet(
            schema_version="1.0",
            startup="RestoMart",
            dimensions={},
            unexpected_field="not_allowed",
        )


def test_dimension_evidence_set_round_trip():
    original = DimensionEvidenceSet(
        schema_version="1.0",
        startup="RestoMart",
        dimensions={
            "founder_team": DimensionEvidence(
                evidence=[
                    DimensionEvidenceItem(
                        evidence_ref="founders_2025",
                        observation=(
                            "Three founders are identified."
                        ),
                        source_type="startup_database",
                    ),
                ],
            ),
        },
    )

    payload = original.model_dump(mode="json")

    restored = DimensionEvidenceSet.model_validate(
        payload,
    )

    assert restored == original


def test_restomart_dimension_evidence_file_is_valid():
    path = (
        Path(__file__).parents[2]
        / "data"
        / "real_startups"
        / "restomart"
        / "dimension_evidence.json"
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    result = DimensionEvidenceSet.model_validate(
        payload,
    )

    assert result.schema_version == "1.0"
    assert result.startup == "RestoMart"

    expected_dimensions = {
        "founder_team",
        "market_tam",
        "product_pmf",
        "technology_ip_moat",
        "commercial_traction",
        "unit_economics_margins",
        "financial_health",
        "governance_cap_table",
        "valuation_deal_terms",
        "risk_exit_potential",
    }

    assert set(result.dimensions) == expected_dimensions


def test_restomart_dimension_evidence_contains_real_evidence():
    path = (
        Path(__file__).parents[2]
        / "data"
        / "real_startups"
        / "restomart"
        / "dimension_evidence.json"
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    result = DimensionEvidenceSet.model_validate(
        payload,
    )

    commercial = result.dimensions[
        "commercial_traction"
    ]

    refs = {
        item.evidence_ref
        for item in commercial.evidence
    }

    assert "financials_revenue" in refs
    assert "financials_customer_base" in refs
    assert "investor_brief_repeat_usage" in refs


def test_restomart_market_evidence_does_not_invent_tam():
    path = (
        Path(__file__).parents[2]
        / "data"
        / "real_startups"
        / "restomart"
        / "dimension_evidence.json"
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    result = DimensionEvidenceSet.model_validate(
        payload,
    )

    market = result.dimensions["market_tam"]

    observations = " ".join(
        item.observation.lower()
        for item in market.evidence
    )

    assert "tam" not in observations
    assert "sam" not in observations
