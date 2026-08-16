"""
Startup analysis execution configuration.

This module defines the production execution profiles used by
startup analysis.

Responsibilities:
    - Define immutable startup-analysis execution configuration.
    - Resolve STANDARD and DEEP analysis modes.
    - Keep mode-specific generation parameters centralized.

Non-responsibilities:
    - Financial calculations.
    - Prompt construction.
    - LLM invocation.
    - Response parsing.
    - Persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings
from app.models.analysis import StartupAnalysisMode


ANALYSIS_VERSION = "3.7.5"

STANDARD_MAX_TOKENS = 768
DEEP_MAX_TOKENS = 1024


@dataclass(frozen=True, slots=True)
class StartupAnalysisConfig:
    """
    Immutable execution configuration for one startup-analysis run.
    """

    mode: StartupAnalysisMode
    model_name: str
    thinking_enabled: bool
    max_tokens: int
    temperature: float
    analysis_version: str = ANALYSIS_VERSION

    def __post_init__(self) -> None:
        if not self.model_name:
            raise ValueError(
                "model_name must not be empty."
            )

        if self.max_tokens <= 0:
            raise ValueError(
                "max_tokens must be greater than zero."
            )

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0.0 and 2.0."
            )

        if not self.analysis_version:
            raise ValueError(
                "analysis_version must not be empty."
            )


def get_startup_analysis_config(
    mode: StartupAnalysisMode,
    *,
    config: Settings = settings,
) -> StartupAnalysisConfig:
    """
    Resolve the production execution configuration for an analysis mode.
    """

    if mode == StartupAnalysisMode.STANDARD:
        return StartupAnalysisConfig(
            mode=mode,
            model_name=config.llm_model,
            thinking_enabled=False,
            max_tokens=STANDARD_MAX_TOKENS,
            temperature=config.startup_analysis_temperature,
        )

    if mode == StartupAnalysisMode.DEEP:
        return StartupAnalysisConfig(
            mode=mode,
            model_name=config.llm_model,
            thinking_enabled=True,
            max_tokens=DEEP_MAX_TOKENS,
            temperature=config.startup_analysis_temperature,
        )

    raise ValueError(
        f"Unsupported startup analysis mode: {mode!r}"
    )


__all__ = [
    "ANALYSIS_VERSION",
    "DEEP_MAX_TOKENS",
    "STANDARD_MAX_TOKENS",
    "StartupAnalysisConfig",
    "get_startup_analysis_config",
]
