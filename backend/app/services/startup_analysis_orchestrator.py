"""
Startup analysis orchestration.

Coordinates:

    Startup
        ↓
    StartupAnalysisInputBuilder
        ↓
    Document Intelligence
        ↓
    Financial Metrics
        ↓
    Qualitative Startup Analysis
        ↓
    StartupAnalysisExecution

Source extraction is intentionally not performed here.

Persisted SourceExtractionRecord objects may be supplied by the
upstream source-extraction workflow and are forwarded to the
document-intelligence layer.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.models.analysis import StartupAnalysisMode
from app.models.source_extraction_record import SourceExtractionRecord
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

    # -------------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------------

    def analyze(
        self,
        startup: Startup,
        *,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
        source_extractions: Iterable[
            SourceExtractionRecord
        ] = (),
    ) -> StartupAnalysisExecution:
        """
        Execute the complete startup-analysis workflow.

        Parameters
        ----------
        startup:
            Startup domain/ORM object used to construct the initial
            StartupAnalysisInput.

        mode:
            Qualitative analysis mode.

        source_extractions:
            Already-persisted source extraction records.

            These records are NOT discovered or extracted here.
            They are simply forwarded to
            StartupAnalysisDocumentIntelligenceService.

        This keeps source extraction and startup analysis as two
        separate production stages:

            Source Discovery / Extraction
                    ↓
            persisted SourceExtractionRecord
                    ↓
            Startup Analysis
        """

        analysis_input = self._input_builder.build(
            startup,
        )

        # ---------------------------------------------------------------------
        # Document intelligence
        # ---------------------------------------------------------------------

        if self._document_intelligence_service is not None:
            analysis_input = (
                self._document_intelligence_service.enrich(
                    startup,
                    analysis_input,
                    source_extractions=source_extractions,
                )
            )

        # ---------------------------------------------------------------------
        # Deterministic financial metrics
        # ---------------------------------------------------------------------

        metrics = self._financial_metrics_service.calculate(
            financials=analysis_input.financials,
            fundraising=analysis_input.fundraising,
            business_model=analysis_input.business_model,
        )

        # ---------------------------------------------------------------------
        # Qualitative startup analysis
        # ---------------------------------------------------------------------

        result, config, response = (
            self._analysis_service.analyze_qualitative(
                analysis_input=analysis_input,
                metrics=metrics,
                mode=mode,
            )
        )

        # ---------------------------------------------------------------------
        # Execution result
        # ---------------------------------------------------------------------

        return StartupAnalysisExecution(
            input=analysis_input,
            metrics=metrics,
            result=result,
            config=config,
            response=response,
        )


__all__ = [
    "StartupAnalysisOrchestrator",
]
