"""
Application service for production startup analysis.

This service is the application-layer entry point used by the API.

Responsibilities
----------------
- Resolve the requested Startup.
- Invoke StartupAnalysisOrchestrator.
- Persist the resulting StartupAnalysisExecution.
- Return the persisted StartupAnalysis.

Non-responsibilities
--------------------
- Financial calculations.
- Analysis input construction.
- Prompt construction.
- LLM invocation.
- Structured response parsing.
- Persistence mapping.
- Transaction management.

Those responsibilities remain in their respective services.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.analysis import StartupAnalysis, StartupAnalysisMode
from app.services.startup import StartupService
from app.services.startup_analysis_orchestrator import (
    StartupAnalysisOrchestrator,
)
from app.services.startup_analysis_persistence import (
    StartupAnalysisPersistenceService,
)


class StartupAnalysisApplicationService:
    """
    Application-level coordinator for production startup analysis.

    The API calls this service rather than coordinating the analysis
    orchestrator and persistence service directly.
    """

    def __init__(
        self,
        session: Session,
        *,
        startup_service: StartupService | None = None,
        orchestrator: StartupAnalysisOrchestrator | None = None,
        persistence_service: StartupAnalysisPersistenceService | None = None,
    ) -> None:
        self._startup_service = (
            startup_service
            if startup_service is not None
            else StartupService(session)
        )

        self._orchestrator = (
            orchestrator
            if orchestrator is not None
            else StartupAnalysisOrchestrator()
        )

        self._persistence_service = (
            persistence_service
            if persistence_service is not None
            else StartupAnalysisPersistenceService(
                session=session,
            )
        )

    def analyze(
        self,
        startup_id: UUID,
        *,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
    ) -> StartupAnalysis:
        """
        Execute and persist a startup analysis.

        Flow
        ----
        1. Resolve startup.
        2. Execute the production analysis orchestration.
        3. Persist StartupAnalysisExecution.
        4. Return the persisted StartupAnalysis.

        Raises
        ------
        ValueError
            If the startup does not exist.

        Any exception raised by the orchestrator or persistence service
        is intentionally propagated to the API error boundary.
        """

        # --------------------------------------------------------------
        # 1. Resolve startup BEFORE starting expensive LLM execution.
        # --------------------------------------------------------------

        startup = self._startup_service.get_startup(startup_id)

        if startup is None:
            raise ValueError("Startup not found.")

        # --------------------------------------------------------------
        # 2. Execute complete production analysis.
        # --------------------------------------------------------------

        execution = self._orchestrator.analyze(
            startup,
            mode=mode,
        )

        # --------------------------------------------------------------
        # 3. Persist execution.
        #
        # Transaction ownership remains inside
        # StartupAnalysisPersistenceService.
        # --------------------------------------------------------------

        analysis = self._persistence_service.persist(
            execution,
        )

        # --------------------------------------------------------------
        # 4. Return persisted historical analysis.
        # --------------------------------------------------------------

        return analysis


__all__ = [
    "StartupAnalysisApplicationService",
]
