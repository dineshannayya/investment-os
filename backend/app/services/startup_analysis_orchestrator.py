from __future__ import annotations

from app.models.analysis import StartupAnalysisMode
from app.models.startup import Startup
from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis import StartupAnalysisService
from app.services.startup_analysis_document_intelligence import (
    StartupAnalysisDocumentIntelligenceService,
)
from app.services.startup_analysis_execution import (
    StartupAnalysisExecution,
)
from app.services.startup_analysis_input_builder import (
    StartupAnalysisInputBuilder,
)


class StartupAnalysisOrchestrator:
    """Coordinate the complete startup-analysis workflow."""

    def __init__(
        self,
        *,
        input_builder: StartupAnalysisInputBuilder | None = None,
        document_intelligence_service: (
            StartupAnalysisDocumentIntelligenceService | None
        ) = None,
        financial_metrics_service=FinancialMetricsService,
        analysis_service: StartupAnalysisService | None = None,
    ) -> None:
        self._input_builder = (
            input_builder or StartupAnalysisInputBuilder()
        )

        self._document_intelligence_service = (
            document_intelligence_service
        )

        self._financial_metrics_service = (
            financial_metrics_service
        )

        self._analysis_service = (
            analysis_service or StartupAnalysisService()
        )

    def analyze(
        self,
        startup: Startup,
        *,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
    ) -> StartupAnalysisExecution:
        """Execute the complete startup-analysis workflow."""

        analysis_input = self._input_builder.build(startup)

        if self._document_intelligence_service is not None:
            analysis_input = (
                self._document_intelligence_service.enrich(
                    startup,
                    analysis_input,
                )
            )

        metrics = self._financial_metrics_service.calculate(
            financials=analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=analysis_input.business_model,
        )

        result, config, response = (
            self._analysis_service.analyze_qualitative(
                analysis_input=analysis_input,
                metrics=metrics,
                mode=mode,
            )
        )

        return StartupAnalysisExecution(
            input=analysis_input,
            metrics=metrics,
            result=result,
            config=config,
            response=response,
        )
