"""
Startup analysis service.

This service orchestrates deterministic startup analysis.

LLM-based qualitative analysis is intentionally not performed here yet.
That will be added in a later milestone.
"""

from __future__ import annotations

from app.schemas.analysis import (
    StartupAnalysis,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.financial_metrics import FinancialMetricsService


class StartupAnalysisService:
    """Build a deterministic startup analysis."""

    def __init__(
        self,
        financial_metrics_service: type[
            FinancialMetricsService
        ] = FinancialMetricsService,
    ) -> None:
        self._financial_metrics_service = financial_metrics_service

    def analyze(
        self,
        analysis_input: StartupAnalysisInput,
    ) -> StartupAnalysis:
        """
        Analyze structured startup information.

        Currently this performs deterministic financial metric
        calculation only. Qualitative LLM analysis will be added
        in a later milestone.
        """

        metrics = self._financial_metrics_service.calculate(
            financials=analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=analysis_input.business_model,
        )

        result = StartupAnalysisResult()

        return StartupAnalysis(
            startup_id=analysis_input.startup_id,
            input=analysis_input,
            metrics=metrics,
            result=result,
        )
