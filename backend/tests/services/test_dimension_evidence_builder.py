"""Tests for DimensionEvidenceBuilder."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from app.models.dimension_evidence import DimensionEvidenceSet
from app.models.investment_scorecard import (
    EvaluationPrinciples,
    EvaluationSpec,
    EvidenceSemantics,
    InvestmentDimension,
    InvestmentScorecard,
    InvestorPreferences,
    InvestorProfile,
    MissingInformationRule,
    ScorecardMetadata,
    ScoringGuidance,
)
from app.schemas.analysis import (
    AnalysisEvidence,
    CompanyAnalysis,
    StartupAnalysisInput,
)
from app.services.dimension_evidence_builder import (
    DimensionEvidenceBuilder,
)


TEST_DOCUMENT_ID = UUID(
    "11111111-1111-1111-1111-111111111111"
)


EXPECTED_DIMENSIONS = (
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
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def scorecard() -> InvestmentScorecard:
    """Build a minimal valid ten-dimension investment scorecard."""

    scoring_guidance = ScoringGuidance(
        score_90_100="Excellent",
        score_75_89="Strong",
        score_60_74="Adequate",
        score_40_59="Weak",
        score_0_39="Poor",
    )

    evaluation_spec = EvaluationSpec(
        objective="Evaluate this investment dimension.",
        evaluate=(
            "Relevant evidence and investment signals.",
        ),
        evidence_required=(
            "Relevant source evidence.",
        ),
        positive_signals=(
            "Positive evidence.",
        ),
        negative_signals=(
            "Negative evidence.",
        ),
        do_not_assume=(
            "Do not assume unsupported facts.",
        ),
        scoring_guidance=scoring_guidance,
    )

    investor_preferences = InvestorPreferences(
        priority="normal",
        notes="Test investor preference.",
    )

    dimensions = tuple(
        InvestmentDimension(
            id=dimension_id,
            name=dimension_id.replace("_", " ").title(),
            weight=Decimal("10"),
            evaluation_spec=evaluation_spec,
            investor_preferences=investor_preferences,
        )
        for dimension_id in EXPECTED_DIMENSIONS
    )

    return InvestmentScorecard(
        schema_version="1.0",
        scorecard=ScorecardMetadata(
            name="Test Investment Scorecard",
            version=1,
            description="Test scorecard.",
        ),
        investor_profile=InvestorProfile(
            name="Test Investor",
            description="Test investor profile.",
        ),
        dimensions=dimensions,
        evaluation_principles=EvaluationPrinciples(
            evidence_semantics=EvidenceSemantics(
                missing_information_is_not_negative_evidence=True,
                absence_of_evidence_is_not_evidence_of_negative_condition=True,
                risk_requires_supporting_evidence=True,
            ),
            missing_information_rule=MissingInformationRule(
                title="Missing information",
                rules=[
                    "Missing information is not negative evidence.",
                    "Missing information should be explicitly identified.",
                    "Do not infer negative conditions from missing information.",
                ],
            ),
        ),
    )


@pytest.fixture
def builder() -> DimensionEvidenceBuilder:
    """Default non-strict builder."""

    return DimensionEvidenceBuilder(
        strict=False,
    )


def make_evidence(
    *,
    evidence_ref: str = "REF-001",
    field: str | None = "revenue",
    section: str | None = "financials",
    source_text: str | None = "Revenue was INR 2.68 Cr.",
    source_type: str | None = "MIS",
    source_name: str | None = "RestoMart MIS",
    document_id: UUID | None = TEST_DOCUMENT_ID,
    page: int | None = 12,
    confidence: Decimal | None = Decimal("0.95"),
) -> AnalysisEvidence:
    """Create a canonical AnalysisEvidence test object."""

    return AnalysisEvidence(
        evidence_ref=evidence_ref,
        document_id=document_id,
        page=page,
        section=section,
        field=field,
        source_text=source_text,
        confidence=confidence,
        source_type=source_type,
        source_name=source_name,
    )


def make_input(
    evidence: list[AnalysisEvidence],
) -> StartupAnalysisInput:
    """Build a valid StartupAnalysisInput for the builder."""

    return StartupAnalysisInput(
        company=CompanyAnalysis(
            name="RestoMart",
        ),
        evidence=evidence,
    )


def get_refs(
    result,
    dimension_id: str,
) -> list[str]:
    """Return evidence references for one dimension."""

    return [
        item.evidence_ref
        for item in result.evidence_set.dimensions[
            dimension_id
        ].evidence
    ]


def get_item(
    result,
    dimension_id: str,
    evidence_ref: str,
):
    """Find one evidence item within a dimension."""

    for item in result.evidence_set.dimensions[
        dimension_id
    ].evidence:
        if item.evidence_ref == evidence_ref:
            return item

    raise AssertionError(
        f"{evidence_ref!r} not found in {dimension_id!r}"
    )


# ============================================================================
# Basic construction
# ============================================================================


class TestDimensionEvidenceBuilder:
    """Contract tests for DimensionEvidenceBuilder."""

    def test_build_returns_dimension_evidence_set(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert isinstance(
            result.evidence_set,
            DimensionEvidenceSet,
        )

        assert result.evidence_set.startup == "RestoMart"
        assert result.evidence_set.schema_version == "1.0"

    def test_build_creates_all_scorecard_dimensions(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert tuple(
            result.evidence_set.dimensions.keys()
        ) == EXPECTED_DIMENSIONS


# ============================================================================
# Routing
# ============================================================================


    def test_revenue_routes_to_commercial_and_financial(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert "REV-001" in get_refs(
            result,
            "commercial_traction",
        )

        assert "REV-001" in get_refs(
            result,
            "financial_health",
        )

        assert "REV-001" not in get_refs(
            result,
            "valuation_deal_terms",
        )

    def test_pre_money_valuation_routes_to_valuation(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="VAL-001",
                field="pre_money_valuation",
                section="valuation",
                source_text=(
                    "Pre-money valuation was INR 9.25 Cr."
                ),
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert get_refs(
            result,
            "valuation_deal_terms",
        ) == ["VAL-001"]

        assert "VAL-001" not in get_refs(
            result,
            "commercial_traction",
        )

    def test_reserved_matters_routes_to_governance(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="GOV-001",
                field="reserved_matters",
                section="governance",
                source_text=(
                    "Certain reserved matters require "
                    "investor approval."
                ),
                source_type="transaction_document",
                source_name="Shareholders Agreement",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert get_refs(
            result,
            "governance_cap_table",
        ) == ["GOV-001"]

    def test_anti_dilution_routes_to_governance_and_valuation(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="SHA-ANTI-001",
                field="anti_dilution",
                section="deal_terms",
                source_text=(
                    "The investor is entitled to anti-dilution "
                    "protection."
                ),
                source_type="transaction_document",
                source_name="Shareholders Agreement",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert "SHA-ANTI-001" in get_refs(
            result,
            "valuation_deal_terms",
        )

        assert "SHA-ANTI-001" in get_refs(
            result,
            "governance_cap_table",
        )


# ============================================================================
# Evidence integrity
# ============================================================================


    def test_preserves_canonical_evidence(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="E-001",
                field="pre_money_valuation",
                section="valuation",
                source_text="Exact source statement.",
                source_type="transaction_document",
                source_name="Shareholders Agreement",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        item = get_item(
            result,
            "valuation_deal_terms",
            "E-001",
        )

        assert item.evidence_ref == "E-001"
        assert item.observation == "Exact source statement."
        assert item.source_type == "transaction_document"

    def test_does_not_create_evidence(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="E-001",
                field="revenue",
            ),
            make_evidence(
                evidence_ref="E-002",
                field="cash",
            ),
        ]

        canonical_refs = {
            item.evidence_ref
            for item in evidence
        }

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        for dimension in (
            result.evidence_set.dimensions.values()
        ):
            for item in dimension.evidence:
                assert item.evidence_ref in canonical_refs

    def test_missing_dimension_evidence_is_allowed(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="FOUNDER-001",
                field="founder",
                section="founder_profile",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert get_refs(
            result,
            "founder_team",
        ) == ["FOUNDER-001"]

        assert get_refs(
            result,
            "technology_ip_moat",
        ) == []

        assert get_refs(
            result,
            "risk_exit_potential",
        ) == []


# ============================================================================
# Duplicate handling
# ============================================================================


    def test_duplicate_reference_within_dimension_is_removed(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
                source_text="Revenue was INR 2.68 Cr.",
            ),
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
                source_text="Revenue was INR 2.68 Cr.",
            ),
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert get_refs(
            result,
            "commercial_traction",
        ) == ["REV-001"]

        assert result.diagnostics.duplicate_evidence == 1

    def test_same_reference_can_appear_across_dimensions(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert get_refs(
            result,
            "commercial_traction",
        ) == ["REV-001"]

        assert get_refs(
            result,
            "financial_health",
        ) == ["REV-001"]


# ============================================================================
# Unrouted evidence
# ============================================================================


    def test_unrouted_evidence_is_reported_in_non_strict_mode(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="UNKNOWN-001",
                field="future_unknown_field",
                section="future_section",
            )
        ]

        result = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert result.diagnostics.total_evidence == 1
        assert result.diagnostics.routed_evidence == 0
        assert result.diagnostics.unrouted_evidence == 1
        assert result.diagnostics.unrouted_refs == (
            "UNKNOWN-001",
        )

    def test_strict_mode_rejects_unrouted_evidence(
        self,
        scorecard,
    ):
        builder = DimensionEvidenceBuilder(
            strict=True,
        )

        evidence = [
            make_evidence(
                evidence_ref="UNKNOWN-001",
                field="future_unknown_field",
                section=None,
            )
        ]

        with pytest.raises(
            ValueError,
            match="Unable to route evidence_ref",
        ):
            builder.build(
                startup_name="RestoMart",
                scorecard=scorecard,
                analysis_input=make_input(evidence),
            )


# ============================================================================
# Invalid routing
# ============================================================================


    def test_unknown_dimension_route_is_rejected(
        self,
        scorecard,
    ):
        builder = DimensionEvidenceBuilder(
            field_routing={
                "revenue": frozenset(
                    {
                        "commercial_traction",
                        "not_a_real_dimension",
                    }
                )
            },
            section_routing={},
        )

        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            )
        ]

        with pytest.raises(
            ValueError,
            match="unknown scorecard dimensions",
        ):
            builder.build(
                startup_name="RestoMart",
                scorecard=scorecard,
                analysis_input=make_input(evidence),
            )


# ============================================================================
# Input validation
# ============================================================================


    def test_blank_startup_name_is_rejected(
        self,
        builder,
        scorecard,
    ):
        with pytest.raises(
            ValueError,
            match="startup_name must not be blank",
        ):
            builder.build(
                startup_name=" ",
                scorecard=scorecard,
                analysis_input=make_input([]),
            )


# ============================================================================
# Determinism
# ============================================================================


    def test_builder_is_deterministic(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            ),
            make_evidence(
                evidence_ref="VAL-001",
                field="pre_money_valuation",
                section="valuation",
            ),
            make_evidence(
                evidence_ref="GOV-001",
                field="reserved_matters",
                section="governance",
            ),
        ]

        result1 = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        result2 = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        assert (
            result1.evidence_set.model_dump()
            == result2.evidence_set.model_dump()
        )

        assert result1.diagnostics == result2.diagnostics

    def test_input_order_does_not_change_output(
        self,
        builder,
        scorecard,
    ):
        evidence_a = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            ),
            make_evidence(
                evidence_ref="VAL-001",
                field="pre_money_valuation",
                section="valuation",
            ),
            make_evidence(
                evidence_ref="FOUNDER-001",
                field="founder",
                section="founder_profile",
            ),
        ]

        evidence_b = [
            evidence_a[2],
            evidence_a[0],
            evidence_a[1],
        ]

        result_a = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence_a),
        )

        result_b = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence_b),
        )

        assert (
            result_a.evidence_set.model_dump()
            == result_b.evidence_set.model_dump()
        )


# ============================================================================
# Architecture contracts
# ============================================================================


    def test_scorecard_weights_do_not_change_evidence(
        self,
        builder,
        scorecard,
    ):
        evidence = [
            make_evidence(
                evidence_ref="REV-001",
                field="revenue",
            ),
            make_evidence(
                evidence_ref="VAL-001",
                field="pre_money_valuation",
                section="valuation",
            ),
        ]

        result1 = builder.build(
            startup_name="RestoMart",
            scorecard=scorecard,
            analysis_input=make_input(evidence),
        )

        # Change only weights while keeping the required total at 100.
        updated_dimensions = tuple(
            dimension.model_copy(
                update={
                    "weight": (
                        Decimal("20")
                        if dimension.id == "commercial_traction"
                        else (
                            Decimal("0")
                            if dimension.id == "risk_exit_potential"
                            else Decimal("10")
                        )
                    )
                }
            )
            for dimension in scorecard.dimensions
        )

        weighted_scorecard = scorecard.model_copy(
            update={
                "dimensions": updated_dimensions,
            }
        )

        # The builder only routes evidence.
        # Scorecard weights must not influence evidence selection.
        result2 = builder.build(
            startup_name="RestoMart",
            scorecard=weighted_scorecard,
            analysis_input=make_input(evidence),
        )

        assert (
            result1.evidence_set.model_dump()
            == result2.evidence_set.model_dump()
        )
