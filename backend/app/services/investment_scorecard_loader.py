"""
Investment scorecard configuration loader.

Loads and validates an InvestmentScorecard definition from JSON.

The loader is intentionally responsible only for configuration loading
and schema validation. It does not evaluate dimensions, calculate
weighted scores, or make investment decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.investment_scorecard import InvestmentScorecard


class InvestmentScorecardLoader:
    """Load and validate investment scorecard configuration."""

    @staticmethod
    def load(
        path: str | Path,
    ) -> InvestmentScorecard:
        """
        Load an investment scorecard from a JSON file.

        Parameters
        ----------
        path:
            Path to investment_scorecard.json.

        Returns
        -------
        InvestmentScorecard
            Validated scorecard configuration.

        Raises
        ------
        FileNotFoundError
            If the scorecard file does not exist.
        ValueError
            If the JSON is invalid or does not satisfy the
            InvestmentScorecard schema.
        """
        scorecard_path = Path(path)

        with scorecard_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid investment scorecard JSON: "
                    f"{scorecard_path}"
                ) from exc

        try:
            return InvestmentScorecard.model_validate(
                payload,
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid investment scorecard configuration: "
                f"{scorecard_path}"
            ) from exc


__all__ = [
    "InvestmentScorecardLoader",
]
