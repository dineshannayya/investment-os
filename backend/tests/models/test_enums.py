# ------------------------------------------------
#  | Area                    | Coverage |
#  | ----------------------- | -------: |
#  | StartupStage            |     100% |
#  | StartupStatus           |     100% |
#  | FounderRole             |     100% |
#  | InvestmentInstrument    |     100% |
#  | OpportunityStatus       |     100% |
#  | InvestmentDecision      |     100% |
#  | InvestmentStatus        |     100% |
#  | DocumentType            |     100% |
#  | DocumentStatus          |     100% |
#  | Generic Enum Validation |     100% |
# --------------------------------------------


"""
Unit tests for ORM enums.

These tests verify:

- Enum values
- Enum membership
- Enum counts
- Enum uniqueness
"""

from app.models.enums import (
    DocumentStatus,
    DocumentType,
    FounderRole,
    InvestmentDecision,
    InvestmentInstrument,
    InvestmentStatus,
    OpportunityStatus,
    StartupStage,
    StartupStatus,
)

# =============================================================================
# StartupStage
# =============================================================================


def test_startup_stage_values():
    assert StartupStage.IDEA.value == "idea"
    assert StartupStage.MVP.value == "mvp"
    assert StartupStage.EARLY_REVENUE.value == "early_revenue"
    assert StartupStage.GROWTH.value == "growth"
    assert StartupStage.SCALE.value == "scale"


def test_startup_stage_count():
    assert len(StartupStage) == 5


# =============================================================================
# StartupStatus
# =============================================================================


def test_startup_status_values():
    assert StartupStatus.ACTIVE.value == "active"
    assert StartupStatus.INACTIVE.value == "inactive"
    assert StartupStatus.ARCHIVED.value == "archived"


def test_startup_status_count():
    assert len(StartupStatus) == 3


# =============================================================================
# FounderRole
# =============================================================================


def test_founder_role_values():
    assert FounderRole.CEO.value == "CEO"
    assert FounderRole.CTO.value == "CTO"
    assert FounderRole.COO.value == "COO"
    assert FounderRole.CFO.value == "CFO"
    assert FounderRole.CMO.value == "CMO"
    assert FounderRole.CPO.value == "CPO"
    assert FounderRole.CHAIRMAN.value == "CHAIRMAN"
    assert FounderRole.DIRECTOR.value == "DIRECTOR"
    assert FounderRole.ADVISOR.value == "ADVISOR"
    assert FounderRole.OTHER.value == "OTHER"


def test_founder_role_count():
    assert len(FounderRole) == 10


# =============================================================================
# InvestmentInstrument
# =============================================================================


def test_investment_instrument_values():
    assert InvestmentInstrument.EQUITY.value == "EQUITY"
    assert InvestmentInstrument.CCPS.value == "CCPS"
    assert InvestmentInstrument.CCD.value == "CCD"
    assert InvestmentInstrument.SAFE.value == "SAFE"
    assert InvestmentInstrument.CONVERTIBLE_NOTE.value == "CONVERTIBLE_NOTE"


def test_investment_instrument_count():
    assert len(InvestmentInstrument) == 5


# =============================================================================
# OpportunityStatus
# =============================================================================


def test_opportunity_status_values():
    assert OpportunityStatus.OPEN.value == "OPEN"
    assert OpportunityStatus.CLOSED.value == "CLOSED"
    assert OpportunityStatus.FULLY_SUBSCRIBED.value == "FULLY_SUBSCRIBED"
    assert OpportunityStatus.CANCELLED.value == "CANCELLED"


def test_opportunity_status_count():
    assert len(OpportunityStatus) == 4


# =============================================================================
# InvestmentDecision
# =============================================================================


def test_investment_decision_values():
    assert InvestmentDecision.PENDING.value == "pending"
    assert InvestmentDecision.APPROVED.value == "approved"
    assert InvestmentDecision.REJECTED.value == "rejected"
    assert InvestmentDecision.WATCHLIST.value == "watchlist"


def test_investment_decision_count():
    assert len(InvestmentDecision) == 4


# =============================================================================
# InvestmentStatus
# =============================================================================


def test_investment_status_values():
    assert InvestmentStatus.DRAFT.value == "DRAFT"
    assert InvestmentStatus.UNDER_REVIEW.value == "UNDER_REVIEW"
    assert InvestmentStatus.APPROVED.value == "APPROVED"
    assert InvestmentStatus.EXECUTED.value == "EXECUTED"
    assert InvestmentStatus.DECLINED.value == "DECLINED"
    assert InvestmentStatus.EXITED.value == "EXITED"


def test_investment_status_count():
    assert len(InvestmentStatus) == 6


# =============================================================================
# DocumentType
# =============================================================================


def test_document_type_values():
    assert DocumentType.PITCH_DECK.value == "PITCH_DECK"
    assert DocumentType.FINANCIAL_MODEL.value == "FINANCIAL_MODEL"
    assert DocumentType.BUSINESS_PLAN.value == "BUSINESS_PLAN"
    assert DocumentType.TERM_SHEET.value == "TERM_SHEET"
    assert DocumentType.SHA.value == "SHA"
    assert DocumentType.CAP_TABLE.value == "CAP_TABLE"
    assert DocumentType.BANK_STATEMENT.value == "BANK_STATEMENT"
    assert DocumentType.GST.value == "GST"
    assert DocumentType.ROC.value == "ROC"
    assert DocumentType.PATENT.value == "PATENT"
    assert DocumentType.PRODUCT_DEMO.value == "PRODUCT_DEMO"
    assert DocumentType.OTHER.value == "OTHER"


def test_document_type_count():
    assert len(DocumentType) == 12


# =============================================================================
# DocumentStatus
# =============================================================================


def test_document_status_values():
    assert DocumentStatus.UPLOADED.value == "UPLOADED"
    assert DocumentStatus.PROCESSING.value == "PROCESSING"
    assert DocumentStatus.PROCESSED.value == "PROCESSED"
    assert DocumentStatus.FAILED.value == "FAILED"
    assert DocumentStatus.ARCHIVED.value == "ARCHIVED"


def test_document_status_count():
    assert len(DocumentStatus) == 5


def test_all_enum_values_are_unique():
    enums = [
        StartupStage,
        StartupStatus,
        FounderRole,
        InvestmentInstrument,
        OpportunityStatus,
        InvestmentDecision,
        InvestmentStatus,
        DocumentType,
        DocumentStatus,
    ]

    for enum_cls in enums:
        values = [member.value for member in enum_cls]
        assert len(values) == len(set(values))


def test_all_enum_names_are_unique():
    enums = [
        StartupStage,
        StartupStatus,
        FounderRole,
        InvestmentInstrument,
        OpportunityStatus,
        InvestmentDecision,
        InvestmentStatus,
        DocumentType,
        DocumentStatus,
    ]

    for enum_cls in enums:
        names = [member.name for member in enum_cls]
        assert len(names) == len(set(names))
