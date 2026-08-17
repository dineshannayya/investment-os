"""
Startup analysis persistence service.

Persists a completed StartupAnalysisExecution as a historical
StartupAnalysis ORM record.

Responsibilities:
    - Map execution artifacts into the persistence model.
    - Persist through StartupAnalysisRepository.
    - Own the transaction boundary.
    - Commit on success.
    - Roll back on persistence failure.

Non-responsibilities:
    - Financial calculations.
    - Prompt construction.
    - LLM invocation.
    - Response parsing.
    - Analysis orchestration.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.analysis import StartupAnalysis
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.services.startup_analysis_execution import StartupAnalysisExecution
from app.services.startup_analysis_mapper import (
    map_startup_analysis_to_model,
)

from app.schemas.analysis import StartupAnalysis as StartupAnalysisSchema


StartupAnalysisMapper = Callable[
    [StartupAnalysisExecution],
    StartupAnalysis,
]


class StartupAnalysisPersistenceService:
    """Persist startup analysis execution results."""

    def __init__(
        self,
        *,
        session: Session,
        mapper: StartupAnalysisMapper | None = None,
        repository: StartupAnalysisRepository | None = None,
    ) -> None:
        self._session = session

        self._mapper = mapper or self._map_execution

        self._repository = (
            repository
            or StartupAnalysisRepository(session)
        )

    def persist(
        self,
        execution: StartupAnalysisExecution,
    ) -> StartupAnalysis:
        """
        Persist a completed startup-analysis execution.

        The service owns the transaction boundary:

            mapper
              ->
            repository.create
              ->
            session.commit

        On any failure:

            session.rollback()
              ->
            re-raise original exception
        """

        try:
            analysis = self._mapper(execution)

            analysis = self._repository.create(analysis)

            self._session.commit()

            return analysis

        except Exception:
            self._session.rollback()
            raise

    @staticmethod
    def _map_execution(
        execution: StartupAnalysisExecution,
    ) -> StartupAnalysis:
        """
        Adapt StartupAnalysisExecution to the existing pure mapper.

        StartupAnalysisExecution is the production execution envelope,
        while map_startup_analysis_to_model() intentionally accepts the
        structured analysis, resolved configuration, and normalized
        LLM response separately.
        """

        analysis = StartupAnalysisSchema(
            startup_id=execution.input.startup_id,
            input=execution.input,
            metrics=execution.metrics,
            result=execution.result,
        )

        return map_startup_analysis_to_model(
            analysis=analysis,
            config=execution.config,
            response=execution.response,
        )
