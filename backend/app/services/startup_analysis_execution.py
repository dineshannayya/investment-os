"""
Startup analysis execution result.

This module defines the immutable application-level result of one
startup-analysis execution.

Responsibilities:
    - Capture all artifacts produced by one analysis execution.
    - Preserve the exact input, deterministic metrics, qualitative result,
      execution configuration, and raw LLM response.
    - Provide a stable boundary between analysis execution and persistence.

Non-responsibilities:
    - Financial calculations.
    - Prompt construction.
    - LLM invocation.
    - Response parsing.
    - Database persistence.
    - Repository access.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.models import LLMResponse
from app.schemas.analysis import (
    FinancialMetrics,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.startup_analysis_config import StartupAnalysisConfig


# ---------------------------------------------------------------------------
# Execution Status
# ---------------------------------------------------------------------------

EXECUTION_STATUS_COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Startup Analysis Execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StartupAnalysisExecution:
    """
    Immutable result of one startup-analysis execution.

    The execution contains the complete set of artifacts required by
    downstream persistence and audit layers.

    It intentionally contains no ORM or repository dependencies.
    """

    input: StartupAnalysisInput
    metrics: FinancialMetrics
    result: StartupAnalysisResult
    config: StartupAnalysisConfig
    response: LLMResponse

    status: str = EXECUTION_STATUS_COMPLETED

    def __post_init__(self) -> None:
        """Validate execution invariants."""

        if self.input is None:
            raise ValueError(
                "Startup analysis execution input must not be None."
            )

        if self.metrics is None:
            raise ValueError(
                "Startup analysis execution metrics must not be None."
            )

        if self.result is None:
            raise ValueError(
                "Startup analysis execution result must not be None."
            )

        if self.config is None:
            raise ValueError(
                "Startup analysis execution config must not be None."
            )

        if self.response is None:
            raise ValueError(
                "Startup analysis execution response must not be None."
            )

        if not self.status:
            raise ValueError(
                "Startup analysis execution status must not be empty."
            )

    @property
    def startup_id(self):
        """
        Return the startup identifier associated with this execution.

        The startup ID is sourced from the normalized analysis input.
        """

        return self.input.startup_id

    @property
    def mode(self):
        """Return the analysis mode used for this execution."""

        return self.config.mode

    @property
    def analysis_version(self) -> str:
        """Return the analysis version used for this execution."""

        return self.config.analysis_version

    @property
    def model_name(self) -> str:
        """Return the LLM model used for this execution."""

        return self.config.model_name

    @property
    def is_completed(self) -> bool:
        """Return True when the execution completed successfully."""

        return self.status == EXECUTION_STATUS_COMPLETED


__all__ = [
    "EXECUTION_STATUS_COMPLETED",
    "StartupAnalysisExecution",
]
