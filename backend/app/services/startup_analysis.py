"""
Startup analysis service.

This service orchestrates deterministic and qualitative startup analysis.

The service:
    1. Calculates deterministic financial metrics.
    2. Builds the structured LLM analysis prompt.
    3. Invokes the configured LLM provider.
    4. Parses and validates the LLM response.
    5. Returns the complete startup analysis.
"""
from __future__ import annotations

from app.core.config import settings
from app.llm.models import LLMRequest, LLMResponse
from app.llm.providers.qwen import QwenProvider
from app.schemas.analysis import (
    FinancialMetrics,
    StartupAnalysis,
    StartupAnalysisInput,
    StartupAnalysisResult,
)

from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis_parser import StartupAnalysisParser
from app.prompt.startup_analysis import build_startup_analysis_messages
from app.models.analysis import StartupAnalysisMode
from app.services.startup_analysis_config import (
    get_startup_analysis_config,
)


class StartupAnalysisGenerationError(RuntimeError):
    """Raised when qualitative startup analysis cannot be generated."""

    def __init__(
        self,
        message: str,
        *,
        finish_reason: str | None = None,
        response_text: str | None = None,
        usage: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.finish_reason = finish_reason
        self.response_text = response_text
        self.usage = usage


class StartupAnalysisService:
    """Orchestrate deterministic and qualitative startup analysis."""

    def __init__(
        self,
        *,
        config=settings,
        financial_metrics_service=FinancialMetricsService,
        llm_provider=None,
        parser=None,
    ):
        self._config = config
        self._financial_metrics_service = financial_metrics_service
        self._llm_provider = (
            llm_provider
            or QwenProvider(config=config)
        )
        self._parser = parser or StartupAnalysisParser()

    def analyze(
        self,
        analysis_input: StartupAnalysisInput,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
    ) -> StartupAnalysis:
        """
        Analyze structured startup information.
    
        Compatibility facade for the legacy service contract.
    
        Production orchestration should use:
            StartupAnalysisOrchestrator
            -> FinancialMetricsService
            -> analyze_qualitative()
        """
    
        metrics = self._financial_metrics_service.calculate(
            financials=analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=analysis_input.business_model,
        )
    
        result, analysis_config, _response = self.analyze_qualitative(
            analysis_input=analysis_input,
            metrics=metrics,
            mode=mode,
        )
    
        return StartupAnalysis(
            startup_id=analysis_input.startup_id,
            input=analysis_input,
            metrics=metrics,
            result=result,
            mode=analysis_config.mode,
            analysis_version=analysis_config.analysis_version,
        )


    def analyze_qualitative(
        self,
        *,
        analysis_input: StartupAnalysisInput,
        metrics: FinancialMetrics,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
    ) -> tuple[
        StartupAnalysisResult,
        StartupAnalysisConfig,
        LLMResponse,
    ]:
        """Run qualitative startup analysis using supplied deterministic metrics."""
    
        analysis_config = get_startup_analysis_config(
            mode,
            config=self._config,
        )
    
        messages = build_startup_analysis_messages(
            analysis_input=analysis_input,
            metrics=metrics,
        )
    
        request = LLMRequest(
            messages=messages,
            model=analysis_config.model_name,
            temperature=analysis_config.temperature,
            max_tokens=analysis_config.max_tokens,
            metadata={
                "thinking_enabled": analysis_config.thinking_enabled,
            },
        )
    
        try:
            response = self._llm_provider.generate(request)
        except Exception as exc:
            raise StartupAnalysisGenerationError(
                "Failed to generate startup analysis."
            ) from exc
    
        if response.finish_reason == "length":
            raise StartupAnalysisGenerationError(
                "Startup analysis response was truncated.",
                finish_reason=response.finish_reason,
                response_text=response.text,
                usage=response.usage,
            )
    
        result = self._parser.parse(response.text)
    
        return result, analysis_config, response
    
