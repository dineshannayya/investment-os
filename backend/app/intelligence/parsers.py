"""
Reusable parsers for Investment Intelligence.
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
    """
    Parsed monetary value.
    """

    amount: Decimal

    currency: str

@dataclass(slots=True, frozen=True)
class MoneyOccurrence:
    """
    A monetary value together with its location
    inside the source text.
    """

    money: Money

    text: str

    start: int

    end: int

class MoneyParser:
    """
    Parse monetary values from text.
    """

    _PATTERN = re.compile(
        r"""
        (?P<currency>₹|\$|USD|INR|EUR)?
        \s*
        (?P<value>\d+(?:,\d{2,3})*(?:\.\d+)?)
        \s*
        (?P<unit>
            Cr|Crore|Crores|
            L|Lakh|Lakhs|
            M|Million|
            B|Billion|
            K|Thousand
        )?
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

        "m": Decimal("1000000"),
        "million": Decimal("1000000"),

        "b": Decimal("1000000000"),
        "billion": Decimal("1000000000"),
    }

    _CURRENCIES = {
        "₹": "INR",
        "INR": "INR",

        "$": "USD",
        "USD": "USD",

        "EUR": "EUR",
    }

    @classmethod
    def _build_match(
        cls,
        match: re.Match[str],
    ) -> Money:
        """
        Convert a regex match into a Money object.
        """
    
        value = Decimal(
            match.group("value").replace(",", "")
        )
    
        unit = match.group("unit")
    
        if unit:
            value *= cls._MULTIPLIERS[
                unit.lower()
            ]
    
        currency = cls._CURRENCIES.get(
            match.group("currency") or "",
            "",
        )

        money = Money(
            amount=value,
            currency=currency,
        )
    
        return MoneyOccurrence(
            money=money,
            text=match.group(0),
            start=match.start(),
            end=match.end(),
        )

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Money | None:
    
        matches = cls.find_all(text)
    
        if not matches:
            return None
    
        return matches[0].money


    @classmethod
    def find_all(
        cls,
        text: str,
    ) -> list[MoneyOccurrence]:
    
        return [
            cls._build_match(match)
            for match in cls._PATTERN.finditer(text)
        ]

# ============================================================================
# Percentage
# ============================================================================


class PercentageParser:
    """
    Parse percentages.
    """

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
    """
    Parse durations expressed in months or years.
    """

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
