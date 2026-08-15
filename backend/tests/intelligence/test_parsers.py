"""
Tests for Investment Intelligence parsers.
"""

from __future__ import annotations

from decimal import Decimal

from app.intelligence.parsers import (
    DurationParser,
    Money,
    MoneyParser,
    PercentageParser,
)

# ============================================================================
# MoneyParser
# ============================================================================


class TestMoneyParser:
    """Tests for MoneyParser."""

    def test_parse_rupee_symbol(self):
        money = MoneyParser.parse("₹5 Cr")

        assert money == Money(
            amount=Decimal("50000000"),
            currency="INR",
        )

    def test_parse_inr_prefix(self):
        money = MoneyParser.parse("INR 10 Cr")

        assert money == Money(
            amount=Decimal("100000000"),
            currency="INR",
        )

    def test_parse_usd_symbol(self):
        money = MoneyParser.parse("$2 Million")

        assert money == Money(
            amount=Decimal("2000000"),
            currency="USD",
        )

    def test_parse_usd_prefix(self):
        money = MoneyParser.parse("USD 3 Million")

        assert money == Money(
            amount=Decimal("3000000"),
            currency="USD",
        )

    def test_parse_eur(self):
        money = MoneyParser.parse("EUR 1.5 Million")

        assert money == Money(
            amount=Decimal("1500000"),
            currency="EUR",
        )

    def test_parse_lakhs(self):
        money = MoneyParser.parse("₹45 Lakhs")

        assert money == Money(
            amount=Decimal("4500000"),
            currency="INR",
        )

    def test_parse_lakh_short(self):
        money = MoneyParser.parse("₹25 L")

        assert money == Money(
            amount=Decimal("2500000"),
            currency="INR",
        )

    def test_parse_crore_decimal(self):
        money = MoneyParser.parse("₹5.5 Cr")

        assert money == Money(
            amount=Decimal("55000000"),
            currency="INR",
        )

    def test_parse_commas(self):
        money = MoneyParser.parse("₹5,50,00,000")

        assert money == Money(
            amount=Decimal("55000000"),
            currency="INR",
        )

    def test_parse_billion(self):
        money = MoneyParser.parse("$1.2 Billion")

        assert money == Money(
            amount=Decimal("1200000000"),
            currency="USD",
        )

    def test_parse_thousand(self):
        money = MoneyParser.parse("USD 250 Thousand")

        assert money == Money(
            amount=Decimal("250000"),
            currency="USD",
        )

    def test_parse_without_currency(self):
        money = MoneyParser.parse("5 Cr")

        assert money == Money(
            amount=Decimal("50000000"),
            currency="",
        )

    def test_parse_invalid(self):
        assert MoneyParser.parse("No money here") is None

    def test_parse_empty(self):
        assert MoneyParser.parse("") is None

    def test_parse_first_match(self):
        money = MoneyParser.parse(
            "Raised ₹5 Cr at ₹25 Cr valuation"
        )
    
        assert money == Money(
            amount=Decimal("50000000"),
            currency="INR",
        )

    def test_parse_returns_first_money(self):
        money = MoneyParser.parse(
            "Raised ₹5 Cr at ₹25 Cr valuation."
        )
    
        assert money == Money(
            amount=Decimal("50000000"),
            currency="INR",
        )
    # ============================================================================
    # find_all()
    # ============================================================================
    def test_find_all_single(self):
        matches = MoneyParser.find_all(
            "Raised ₹5 Cr."
        )
    
        assert len(matches) == 1
    
        assert matches[0].money == Money(
            amount=Decimal("50000000"),
            currency="INR",
        )
    
    # Multiple amounts
    def test_find_all_multiple(self):
        matches = MoneyParser.find_all(
            "Raised ₹5 Cr at ₹25 Cr valuation."
        )
    
        assert len(matches) == 2
    
        assert matches[0].money.amount == Decimal("50000000")
        assert matches[1].money.amount == Decimal("250000000")
    
    # Preserve order
    def test_find_all_preserves_order(self):
        matches = MoneyParser.find_all(
            "Revenue ₹2 Cr. Raised ₹5 Cr. Valuation ₹25 Cr."
        )
    
        assert [
            m.money.amount
            for m in matches
        ] == [
            Decimal("20000000"),
            Decimal("50000000"),
            Decimal("250000000"),
        ]
    
    # Currency mix
    def test_find_all_mixed_currency(self):
        matches = MoneyParser.find_all(
            "Raised ₹5 Cr and USD 2 Million."
        )
    
        assert matches[0].money.currency == "INR"
        assert matches[1].money.currency == "USD"
    
    # Empty
    def test_find_all_empty(self):
        assert MoneyParser.find_all("") == []
    
    # No money
    def test_find_all_none(self):
        assert MoneyParser.find_all(
            "No financial information."
        ) == []

# ============================================================================
# PercentageParser
# ============================================================================


class TestPercentageParser:
    """Tests for PercentageParser."""

    def test_integer(self):
        assert PercentageParser.parse(
            "15%"
        ) == Decimal("15")

    def test_decimal(self):
        assert PercentageParser.parse(
            "12.75%"
        ) == Decimal("12.75")

    def test_sentence(self):
        assert PercentageParser.parse(
            "EBITDA margin is 28.4%"
        ) == Decimal("28.4")

    def test_invalid(self):
        assert PercentageParser.parse(
            "None"
        ) is None

    def test_empty(self):
        assert PercentageParser.parse(
            ""
        ) is None


# ============================================================================
# DurationParser
# ============================================================================


class TestDurationParser:
    """Tests for DurationParser."""

    def test_month(self):
        assert (
            DurationParser.parse_months(
                "18 months"
            )
            == 18
        )

    def test_single_month(self):
        assert (
            DurationParser.parse_months(
                "1 month"
            )
            == 1
        )

    def test_year(self):
        assert (
            DurationParser.parse_months(
                "2 years"
            )
            == 24
        )

    def test_single_year(self):
        assert (
            DurationParser.parse_months(
                "1 year"
            )
            == 12
        )

    def test_sentence(self):
        assert (
            DurationParser.parse_months(
                "Runway is 24 months."
            )
            == 24
        )

    def test_invalid(self):
        assert (
            DurationParser.parse_months(
                "No duration"
            )
            is None
        )

    def test_empty(self):
        assert (
            DurationParser.parse_months("")
            is None
        )

