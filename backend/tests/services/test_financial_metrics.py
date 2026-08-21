"""Tests for deterministic startup financial metrics."""

from decimal import Decimal

import pytest

from app.schemas.analysis import (
    BusinessModelAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
)
from app.services.financial_metrics import FinancialMetricsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def calculate(
    *,
    financials=None,
    fundraising=None,
    business_model=None,
):
    return FinancialMetricsService.calculate(
        financials=financials,
        fundraising=fundraising,
        business_model=business_model,
    )


# ---------------------------------------------------------------------------
# Empty / missing input
# ---------------------------------------------------------------------------


def test_calculate_with_no_inputs_returns_empty_metrics():
    result = calculate()

    assert result.revenue_multiple is None
    assert result.ebitda_multiple is None
    assert result.valuation_to_growth is None


def test_calculate_with_no_financials():
    result = calculate(
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple is None
    assert result.ebitda_multiple is None
    assert result.valuation_to_growth is None


def test_calculate_with_no_fundraising():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
        ),
    )

    assert result.revenue_multiple is None
    assert result.ebitda_multiple is None


def test_calculate_with_no_business_model():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.ebitda_multiple == Decimal("20")


# ---------------------------------------------------------------------------
# Revenue multiple
# ---------------------------------------------------------------------------


def test_revenue_multiple():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")


def test_revenue_multiple_with_fractional_result():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("30000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("100000000"),
        ),
    )

    assert result.revenue_multiple == (
        Decimal("100000000") / Decimal("30000000")
    )


def test_revenue_multiple_missing_revenue():
    result = calculate(
        financials=FinancialAnalysis(),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple is None


def test_revenue_multiple_zero_revenue():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("0"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple is None


# ---------------------------------------------------------------------------
# EBITDA multiple
# ---------------------------------------------------------------------------


def test_ebitda_multiple():
    result = calculate(
        financials=FinancialAnalysis(
            ebitda=Decimal("20000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.ebitda_multiple == Decimal("20")


def test_ebitda_multiple_fractional_result():
    result = calculate(
        financials=FinancialAnalysis(
            ebitda=Decimal("15000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.ebitda_multiple == (
        Decimal("400000000") / Decimal("15000000")
    )


def test_ebitda_multiple_missing_ebitda():
    result = calculate(
        financials=FinancialAnalysis(),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.ebitda_multiple is None


def test_ebitda_multiple_zero_ebitda():
    result = calculate(
        financials=FinancialAnalysis(
            ebitda=Decimal("0"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.ebitda_multiple is None


def test_ebitda_multiple_negative_ebitda():
    result = calculate(
        financials=FinancialAnalysis(
            ebitda=Decimal("-20000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.ebitda_multiple == Decimal("-20")


# ---------------------------------------------------------------------------
# Valuation precedence
# ---------------------------------------------------------------------------


def test_post_money_valuation_has_priority():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            pre_money_valuation=Decimal("300000000"),
            post_money_valuation=Decimal("400000000"),
            valuation_cap=Decimal("250000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")


def test_pre_money_valuation_used_when_post_money_missing():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            pre_money_valuation=Decimal("300000000"),
            valuation_cap=Decimal("250000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("3")


def test_valuation_cap_used_when_other_valuations_missing():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            valuation_cap=Decimal("250000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("2.5")


def test_no_valuation_returns_no_multiples():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
        ),
        fundraising=FundraisingAnalysis(),
    )

    assert result.revenue_multiple is None
    assert result.ebitda_multiple is None


# ---------------------------------------------------------------------------
# Valuation-to-growth
# ---------------------------------------------------------------------------


def test_valuation_to_growth():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("40"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.valuation_to_growth == Decimal("0.1")


def test_valuation_to_growth_missing_growth():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.valuation_to_growth is None


def test_valuation_to_growth_zero_growth():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("0"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.valuation_to_growth is None


def test_valuation_to_growth_negative_growth():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("-10"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.valuation_to_growth == Decimal("-0.4")


# ---------------------------------------------------------------------------
# Combined startup example
# ---------------------------------------------------------------------------


def test_realistic_startup_financial_case():
    """
    Example:

        Revenue       = ₹10 Cr
        EBITDA        = ₹2 Cr
        Growth        = 40%
        Valuation     = ₹40 Cr

    Expected:

        Revenue multiple = 4x
        EBITDA multiple  = 20x
        Valuation/growth = 0.1
    """

    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
            revenue_growth_yoy=Decimal("40"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.ebitda_multiple == Decimal("20")
    assert result.valuation_to_growth == Decimal("0.1")


# ---------------------------------------------------------------------------
# Business model input
# ---------------------------------------------------------------------------


def test_business_model_does_not_affect_current_returned_metrics():
    """
    Business-model metrics are not yet represented in ValuationMetrics.

    This test documents that passing business-model data does not alter
    the currently exposed valuation metrics.
    """

    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
        ),
        fundraising=FundraisingAnalysis(
            post_money_valuation=Decimal("400000000"),
        ),
        business_model=BusinessModelAnalysis(
            customer_acquisition_cost=Decimal("10000"),
            lifetime_value=Decimal("50000"),
            ltv_to_cac=Decimal("5"),
        ),
    )

    assert result.revenue_multiple == Decimal("4")
    assert result.ebitda_multiple is None
    assert result.valuation_to_growth is None

# ---------------------------------------------------------------------------
# Source-provided financial metrics
# ---------------------------------------------------------------------------


def test_source_provided_ebitda_margin_is_preserved():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("26800000"),
            ebitda_margin=Decimal("95"),
        ),
    )

    assert result.ebitda_margin == Decimal("95")


def test_source_provided_runway_is_preserved():
    result = calculate(
        financials=FinancialAnalysis(
            runway_months=Decimal("24"),
        ),
    )

    assert result.runway_months == Decimal("24")


def test_ebitda_margin_is_derived_when_source_value_missing():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            ebitda=Decimal("20000000"),
        ),
    )

    assert result.ebitda_margin == Decimal("0.2")


def test_runway_is_derived_when_source_value_missing():
    result = calculate(
        financials=FinancialAnalysis(
            cash=Decimal("120000000"),
            burn_rate=Decimal("10000000"),
        ),
    )

    assert result.runway_months == Decimal("12")

def test_source_provided_gross_margin_is_preserved():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            gross_margin=Decimal("35"),
        ),
    )

    assert result.gross_margin == Decimal("35")

def test_gross_margin_is_derived_when_source_value_missing():
    result = calculate(
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            gross_profit=Decimal("30000000"),
        ),
    )

    assert result.gross_margin == Decimal("0.3")

