"""
Startup analysis persistence mapper.

Responsibilities
----------------
Convert a completed structured startup analysis, its resolved execution
configuration, and the normalized LLM response into a StartupAnalysis ORM
object suitable for persistence.

This module is intentionally database-independent.

It does NOT:
    - access a SQLAlchemy Session
    - call a repository
    - commit or rollback
    - perform financial calculations
    - invoke an LLM
    - parse an LLM response

Persistence / transaction ownership belongs to
StartupAnalysisPersistenceService.
"""

from __future__ import annotations

from app.llm.models import LLMResponse
from app.models.analysis import (
    StartupAnalysis as StartupAnalysisModel,
    StartupAnalysisStatus,
)
from app.schemas.analysis import StartupAnalysis
from app.services.startup_analysis_config import StartupAnalysisConfig


def map_startup_analysis_to_model(
    *,
    analysis: StartupAnalysis,
    config: StartupAnalysisConfig,
    response: LLMResponse,
    inference_time_seconds: float | None = None,
) -> StartupAnalysisModel:
    """
    Map a structured startup analysis execution into the ORM model.

    Parameters
    ----------
    analysis:
        Structured startup analysis containing the startup identifier,
        normalized analysis input, deterministic financial metrics, and
        qualitative analysis result.

    config:
        Resolved configuration used for this analysis execution.

    response:
        Provider-neutral normalized LLM response containing model identity,
        finish reason, and token usage.

    inference_time_seconds:
        Optional wall-clock inference duration.

    Returns
    -------
    StartupAnalysisModel
        Detached SQLAlchemy ORM object ready for repository persistence.

    Raises
    ------
    ValueError
        If the analysis does not contain a startup_id.
    """

    # ------------------------------------------------------------------
    # 1. Persistence identity
    # ------------------------------------------------------------------

    if analysis.startup_id is None:
        raise ValueError(
            "Startup analysis persistence requires startup_id."
        )

    # ------------------------------------------------------------------
    # 2. Resolve model identity
    # ------------------------------------------------------------------
    #
    # The actual model reported by the provider is preferred.
    #
    # This is important because the configured model name may represent
    # an alias, configured path, or logical model name, while the runtime
    # response may contain the actual model identity.
    #
    # If the provider does not return a model name, fall back to the
    # configured model.
    # ------------------------------------------------------------------

    model_name = response.model or config.model_name

    # ------------------------------------------------------------------
    # 3. Extract normalized LLM usage
    # ------------------------------------------------------------------

    usage = response.usage

    # ------------------------------------------------------------------
    # 4. Create historical JSON snapshots
    # ------------------------------------------------------------------
    #
    # These snapshots deliberately capture the state used for this
    # analysis rather than references to mutable source objects.
    #
    # mode="json" converts UUIDs, enums, Decimal values, nested Pydantic
    # models, etc. into JSON-compatible representations.
    # ------------------------------------------------------------------

    input_snapshot = analysis.input.model_dump(
        mode="json",
    )

    metrics_snapshot = analysis.metrics.model_dump(
        mode="json",
    )

    result_snapshot = analysis.result.model_dump(
        mode="json",
    )

    # ------------------------------------------------------------------
    # 5. Construct detached ORM model
    # ------------------------------------------------------------------
    #
    # IMPORTANT:
    # Do not:
    #
    #   session.add(...)
    #   session.flush()
    #   session.commit()
    #
    # The mapper only constructs the persistence representation.
    # ------------------------------------------------------------------

    return StartupAnalysisModel(
        # --------------------------------------------------------------
        # Startup identity
        # --------------------------------------------------------------
        startup_id=analysis.startup_id,

        # --------------------------------------------------------------
        # Analysis execution identity
        # --------------------------------------------------------------
        mode=config.mode,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version=config.analysis_version,

        # --------------------------------------------------------------
        # LLM configuration
        # --------------------------------------------------------------
        model_name=model_name,
        thinking_enabled=config.thinking_enabled,
        max_tokens=config.max_tokens,
        temperature=config.temperature,

        # --------------------------------------------------------------
        # LLM execution metadata
        # --------------------------------------------------------------
        finish_reason=response.finish_reason,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,

        # --------------------------------------------------------------
        # Runtime metadata
        # --------------------------------------------------------------
        inference_time_seconds=inference_time_seconds,

        # --------------------------------------------------------------
        # Investment conclusion
        # --------------------------------------------------------------
        recommendation=analysis.result.preliminary_recommendation,
        investment_thesis=analysis.result.investment_thesis,

        # --------------------------------------------------------------
        # Historical snapshots
        # --------------------------------------------------------------
        input_snapshot=input_snapshot,
        metrics_snapshot=metrics_snapshot,
        result_snapshot=result_snapshot,

        # --------------------------------------------------------------
        # Successful execution
        # --------------------------------------------------------------
        error_message=None,
    )


__all__ = [
    "map_startup_analysis_to_model",
]
