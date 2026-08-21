"""
Deterministic financial metrics for startup analysis.

This module contains no LLM logic. All metrics are calculated from
structured startup financial and fundraising data.

Missing or non-computable inputs result in None rather than an
exception.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from app.schemas.analysis import (
    BusinessModelAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
    FinancialMetrics,
)


ZERO: Final[Decimal] = Decimal("0")


class FinancialMetricsService:
    """Calculate deterministic financial metrics."""

    @staticmethod
    def _safe_divide(
        numerator: Decimal | None,
        denominator: Decimal | None,
    ) -> Decimal | None:
        """Safely divide two Decimal values."""

        if numerator is None or denominator is None:
            return None

        if denominator == ZERO:
            return None

        return numerator / denominator

    @classmethod
    def calculate(
        cls,
        financials: FinancialAnalysis | None = None,
        fundraising: FundraisingAnalysis | None = None,
        business_model: BusinessModelAnalysis | None = None,
    ) -> FinancialMetrics:
        """
        Calculate deterministic startup financial metrics.

        Metrics currently calculated:

        - EBITDA margin
        - Gross margin
        - Revenue multiple
        - EBITDA multiple
        - LTV/CAC
        - Runway
        - Valuation-to-growth

        Missing or non-computable inputs produce None.
        """

        revenue = (
            financials.revenue
            if financials is not None
            else None
        )

        ebitda = (
            financials.ebitda
            if financials is not None
            else None
        )

        gross_profit = (
            financials.gross_profit
            if financials is not None
            else None
        )

        cash = (
            financials.cash
            if financials is not None
            else None
        )

        burn_rate = (
            financials.burn_rate
            if financials is not None
            else None
        )

        valuation = None

        if fundraising is not None:
            valuation = (
                fundraising.post_money_valuation
                or fundraising.pre_money_valuation
                or fundraising.valuation_cap
            )

        ltv = (
            business_model.lifetime_value
            if business_model is not None
            else None
        )

        cac = (
            business_model.customer_acquisition_cost
            if business_model is not None
            else None
        )

        revenue_growth = (
            financials.revenue_growth_yoy
            if financials is not None
            else None
        )

        ebitda_margin = (
            financials.ebitda_margin
            if financials is not None
            and financials.ebitda_margin is not None
            else cls._safe_divide(ebitda, revenue)
        )

        gross_margin = (
            financials.gross_margin
            if financials is not None
            and financials.gross_margin is not None
            else cls._safe_divide(gross_profit, revenue)
        )


        revenue_multiple = cls._safe_divide(
            valuation,
            revenue,
        )

        ebitda_multiple = cls._safe_divide(
            valuation,
            ebitda,
        )

        ltv_to_cac = cls._safe_divide(
            ltv,
            cac,
        )

        runway_months = (
            financials.runway_months
            if financials is not None
            and financials.runway_months is not None
            else cls._safe_divide(cash, burn_rate)
        )


        valuation_to_growth = cls._safe_divide(
            revenue_multiple,
            revenue_growth,
        )

        return FinancialMetrics(
            revenue_multiple=revenue_multiple,
            ebitda_multiple=ebitda_multiple,
            valuation_to_growth=valuation_to_growth,
            ebitda_margin=ebitda_margin,
            gross_margin=gross_margin,
            ltv_to_cac=ltv_to_cac,
            runway_months=runway_months,
        )


