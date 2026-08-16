"""Map startup-analysis execution artifacts to the persistence model."""

from __future__ import annotations

from app.llm.models import LLMResponse
from app.models.analysis import (
    StartupAnalysis as StartupAnalysisModel,
    StartupAnalysisStatus,
)
from app.schemas.analysis import StartupAnalysis as StartupAnalysisSchema
from app.services.startup_analysis_config import StartupAnalysisConfig


def map_startup_analysis_to_model(
    *,
    analysis: StartupAnalysisSchema,
    config: StartupAnalysisConfig,
    response: LLMResponse,
    inference_time_seconds: float | None = None,
) -> StartupAnalysisModel:
    """Map a completed analysis execution to its historical ORM record.

    The mapper is deliberately database-independent. It combines the
    structured analysis result, the resolved execution configuration, and the
    normalized LLM response into one immutable historical representation.

    ``inference_time_seconds`` is supplied separately because the current
    provider-neutral ``LLMResponse`` contract does not include wall-clock
    timing. It remains optional until the production orchestration layer
    measures and supplies it.
    """

    if analysis.startup_id is None:
        raise ValueError(
            "Startup analysis persistence requires startup_id."
        )

    return StartupAnalysisModel(
        startup_id=analysis.startup_id,
        mode=analysis.mode,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version=config.analysis_version,
        model_name=response.model or config.model_name,
        thinking_enabled=config.thinking_enabled,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        finish_reason=response.finish_reason,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
        inference_time_seconds=inference_time_seconds,
        recommendation=analysis.result.preliminary_recommendation,
        investment_thesis=analysis.result.investment_thesis,
        input_snapshot=analysis.input.model_dump(mode="json"),
        metrics_snapshot=analysis.metrics.model_dump(mode="json"),
        result_snapshot=analysis.result.model_dump(mode="json"),
        error_message=None,
    )


__all__ = ["map_startup_analysis_to_model"]
