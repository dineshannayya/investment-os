"""
Reusable parsers for Investment Intelligence.

MoneyParser is the canonical monetary syntax/normalization boundary used by
financial intelligence extractors. Higher-level extractors should classify
MoneyOccurrence objects semantically rather than reimplement monetary parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


# ============================================================================
# Money
# ============================================================================


@dataclass(slots=True, frozen=True)
class Money:
    """Parsed monetary value."""

    amount: Decimal
    currency: str


@dataclass(slots=True, frozen=True)
class MoneyOccurrence:
    """A monetary value together with its location inside source text."""

    money: Money
    text: str
    start: int
    end: int


class MoneyParser:
    """Parse and normalize monetary values from text."""

    # Keep monetary syntax in exactly one place.
    #
    # The unit boundary is important:
    #   "24 months" must NOT be interpreted as "24 m".
    _PATTERN = re.compile(
        r"""
        (?:
            (?P<currency>₹|\$|USD|INR|EUR|GBP|£|€)
            \s*
            (?P<value>\d+(?:,\d{2,3})*(?:\.\d+)?)
            \s*
            (?P<unit>
                Cr|Crore|Crores|
                L|Lakh|Lakhs|
                M|Million|Millions|
                B|Billion|Billions|
                K|Thousand|Thousands
            )?
            \b
        |
            (?P<value_unit>\d+(?:,\d{2,3})*(?:\.\d+)?)
            \s*
            (?P<unit_only>
                Cr|Crores?|Lakhs?|Millions?|Billions?|Thousands?|
                [LBK]
            )\b
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _MULTIPLIERS = {
        "cr": Decimal("10000000"),
        "crore": Decimal("10000000"),
        "crores": Decimal("10000000"),
        "l": Decimal("100000"),
        "lakh": Decimal("100000"),
        "lakhs": Decimal("100000"),
        "k": Decimal("1000"),
        "thousand": Decimal("1000"),
        "thousands": Decimal("1000"),
        "m": Decimal("1000000"),
        "million": Decimal("1000000"),
        "millions": Decimal("1000000"),
        "b": Decimal("1000000000"),
        "billion": Decimal("1000000000"),
        "billions": Decimal("1000000000"),
    }

    _CURRENCIES = {
        "₹": "INR",
        "INR": "INR",
        "$": "USD",
        "USD": "USD",
        "EUR": "EUR",
        "€": "EUR",
        "GBP": "GBP",
        "£": "GBP",
    }

    @classmethod
    def _build_match(
        cls,
        match: re.Match[str],
    ) -> MoneyOccurrence:
        """Convert a regex match into a normalized money occurrence."""

        raw_value = (
            match.group("value")
            or match.group("value_unit")
        )

        if raw_value is None:
            raise ValueError(
                "MoneyParser matched without a numeric value"
            )

        value = Decimal(raw_value.replace(",", ""))

        unit = (
            match.group("unit")
            or match.group("unit_only")
        )

        if unit:
            value *= cls._MULTIPLIERS[unit.lower()]

        currency = cls._CURRENCIES.get(
            match.group("currency") or "",
            "",
        )

        return MoneyOccurrence(
            money=Money(
                amount=value,
                currency=currency,
            ),
            text=match.group(0),
            start=match.start(),
            end=match.end(),
        )

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Money | None:
        """Return the first normalized monetary value in text."""

        matches = cls.find_all(text)

        if not matches:
            return None

        return matches[0].money

    @classmethod
    def find_all(
        cls,
        text: str,
    ) -> list[MoneyOccurrence]:
        """Return all normalized monetary occurrences in source order."""

        return [
            cls._build_match(match)
            for match in cls._PATTERN.finditer(text)
        ]


# ============================================================================
# Percentage
# ============================================================================


class PercentageParser:
    """Parse percentages."""

    _PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*%"
    )

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Decimal | None:
        match = cls._PATTERN.search(text)

        if match is None:
            return None

        return Decimal(match.group(1))


# ============================================================================
# Duration
# ============================================================================


class DurationParser:
    """Parse durations expressed in months or years."""

    _PATTERN = re.compile(
        r"""
        (\d+)
        \s*
        (
            month|
            months|
            year|
            years
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    @classmethod
    def parse_months(
        cls,
        text: str,
    ) -> int | None:
        match = cls._PATTERN.search(text)

        if match is None:
            return None

        value = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("year"):
            return value * 12

        return value
