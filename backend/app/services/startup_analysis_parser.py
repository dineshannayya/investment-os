"""
Parser for structured Qwen startup-analysis responses.

This module converts raw LLM text into the application-level
StartupAnalysisResult schema.

Responsibilities:
    - Remove Qwen thinking blocks.
    - Remove optional Markdown JSON fences.
    - Extract a JSON object from the response.
    - Parse JSON.
    - Validate against StartupAnalysisResult.

Non-responsibilities:
    - LLM invocation.
    - Prompt construction.
    - Financial calculations.
    - Automatic correction or repair of invalid LLM output.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.analysis import StartupAnalysisResult


class StartupAnalysisParseError(ValueError):
    """Raised when an LLM startup-analysis response cannot be parsed."""

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.cause = cause


class StartupAnalysisParser:
    """Parse and validate structured startup-analysis responses."""

    _THINK_BLOCK_PATTERN = re.compile(
        r"<think>.*?</think>",
        re.DOTALL | re.IGNORECASE,
    )

    _JSON_FENCE_PATTERN = re.compile(
        r"```(?:json)?\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE,
    )

    def parse(
        self,
        text: str,
    ) -> StartupAnalysisResult:
        """
        Parse raw LLM output into StartupAnalysisResult.

        The parser accepts:
            - plain JSON
            - JSON wrapped in Markdown fences
            - Qwen <think>...</think> followed by JSON
            - limited surrounding text containing a JSON object

        Invalid or incomplete responses raise StartupAnalysisParseError.
        """

        if not text or not text.strip():
            raise StartupAnalysisParseError(
                "Startup analysis response is empty."
            )

        cleaned = self._remove_thinking_blocks(text)
        cleaned = cleaned.strip()

        if not cleaned:
            raise StartupAnalysisParseError(
                "Startup analysis response contains no content "
                "after removing thinking blocks."
            )

        json_text = self._extract_json(cleaned)

        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise StartupAnalysisParseError(
                "Startup analysis response contains invalid JSON.",
                cause=exc,
            ) from exc

        if not isinstance(payload, dict):
            raise StartupAnalysisParseError(
                "Startup analysis JSON must be an object."
            )

        try:
            return StartupAnalysisResult.model_validate(
                payload,
            )
        except ValidationError as exc:
            raise StartupAnalysisParseError(
                "Startup analysis JSON does not match "
                "StartupAnalysisResult.",
                cause=exc,
            ) from exc

    @classmethod
    def _remove_thinking_blocks(
        cls,
        text: str,
    ) -> str:
        """Remove complete Qwen thinking blocks."""

        return cls._THINK_BLOCK_PATTERN.sub(
            "",
            text,
        )

    @classmethod
    def _extract_json(cls, text: str) -> str:
        """
        Extract a JSON object from model output.
    
        Prefer parsing the complete response first. This preserves the
        distinction between a JSON object and other valid JSON values
        such as arrays.
    
        If the complete response is not JSON, fall back to extracting
        an embedded JSON object from surrounding text.
        """
    
        stripped = text.strip()
    
        # First: complete JSON response.
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        else:
            if not isinstance(payload, dict):
                raise StartupAnalysisParseError(
                    "Startup analysis JSON must be an object."
                )
    
            return stripped
    
        # Second: Markdown JSON fence.
        fenced = cls._JSON_FENCE_PATTERN.search(stripped)
    
        if fenced:
            candidate = fenced.group(1).strip()
    
            if not candidate:
                raise StartupAnalysisParseError(
                    "Startup analysis JSON code fence is empty."
                )
    
            return candidate
    
        # Third: embedded JSON object in surrounding text.
        decoder = json.JSONDecoder()
    
        for index, character in enumerate(stripped):
            if character != "{":
                continue
    
            try:
                _, end = decoder.raw_decode(
                    stripped[index:],
                )
            except json.JSONDecodeError:
                continue
    
            return stripped[index:index + end]
    
        # A response that contains a JSON-looking object but cannot
        # actually decode it should be reported as invalid JSON.
        if "{" in stripped:
            raise StartupAnalysisParseError(
                "Startup analysis response contains invalid JSON."
            )
    
        raise StartupAnalysisParseError(
            "No JSON object found in startup analysis response."
        )

__all__ = [
    "StartupAnalysisParseError",
    "StartupAnalysisParser",
]
