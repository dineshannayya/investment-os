from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.models.investment_scorecard import (
    DimensionEvaluation,
)


_THINK_BLOCK_RE = re.compile(
    r"<think>.*?</think>",
    flags=re.DOTALL | re.IGNORECASE,
)


class InvestmentScorecardParser:
    """
    Parse structured LLM output for one investment dimension.

    The parser is intentionally responsible only for:
        - removing the Qwen thinking wrapper
        - parsing JSON
        - validating DimensionEvaluation

    It does not:
        - calculate weights
        - calculate weighted scores
        - calculate overall score
        - generate recommendations
        - modify evidence
    """

    @staticmethod
    def _remove_thinking_block(
        response_text: str,
    ) -> str:
        return _THINK_BLOCK_RE.sub(
            "",
            response_text,
        ).strip()

    @classmethod
    def parse(
        cls,
        response_text: str,
    ) -> DimensionEvaluation:

        cleaned = cls._remove_thinking_block(
            response_text
        )

        try:
            payload = json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON returned by investment "
                "scorecard LLM."
            ) from exc

        try:
            return DimensionEvaluation.model_validate(
                payload
            )

        except ValidationError as exc:
            raise ValueError(
                "Invalid investment dimension evaluation: "
                f"{exc}"
            ) from exc
