"""
Shared ORM enums.
"""

from enum import Enum

# ============================================================================
# Startup
# ============================================================================

class StartupStage(str, Enum):
    """Startup lifecycle stage."""

    IDEA = "idea"
    MVP = "mvp"
    EARLY_REVENUE = "early_revenue"
    GROWTH = "growth"
    SCALE = "scale"


class StartupStatus(str, Enum):
    """Startup operational status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


# ============================================================================
# Founder
# ============================================================================

class FounderRole(str, Enum):
    """Founder designation."""

    CEO = "CEO"
    CTO = "CTO"
    COO = "COO"
    CFO = "CFO"
    CMO = "CMO"
    CPO = "CPO"
    CHAIRMAN = "CHAIRMAN"
    DIRECTOR = "DIRECTOR"
    ADVISOR = "ADVISOR"
    OTHER = "OTHER"


# ============================================================================
# Opportunity
# ============================================================================

class InvestmentInstrument(str, Enum):
    """Fundraising instrument."""

    EQUITY = "EQUITY"
    CCPS = "CCPS"
    CCD = "CCD"
    SAFE = "SAFE"
    CONVERTIBLE_NOTE = "CONVERTIBLE_NOTE"


class OpportunityStatus(str, Enum):
    """Fundraising opportunity status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FULLY_SUBSCRIBED = "FULLY_SUBSCRIBED"
    CANCELLED = "CANCELLED"


# ============================================================================
# Investment
# ============================================================================

class InvestmentDecision(str, Enum):
    """Investment committee decision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WATCHLIST = "watchlist"


class InvestmentStatus(str, Enum):
    """Investment workflow status."""

    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    DECLINED = "DECLINED"
    EXITED = "EXITED"


# ============================================================================
# Documents
# ============================================================================

class DocumentType(str, Enum):
    """Supported startup documents."""

    PITCH_DECK = "PITCH_DECK"
    FINANCIAL_MODEL = "FINANCIAL_MODEL"
    BUSINESS_PLAN = "BUSINESS_PLAN"
    TERM_SHEET = "TERM_SHEET"
    SHA = "SHA"
    CAP_TABLE = "CAP_TABLE"
    BANK_STATEMENT = "BANK_STATEMENT"
    GST = "GST"
    ROC = "ROC"
    PATENT = "PATENT"
    PRODUCT_DEMO = "PRODUCT_DEMO"
    OTHER = "OTHER"


class DocumentStatus(str, Enum):
    """Document processing status."""

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"
