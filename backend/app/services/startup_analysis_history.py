"""
Startup analysis history service.

Read-only application service for retrieving persisted startup-analysis
history.

Responsibilities:
    - Retrieve startup-analysis history for a startup.
    - Retrieve one historical analysis belonging to a startup.
    - Delegate database access to StartupAnalysisRepository.
    - Preserve repository pagination information.

Non-responsibilities:
    - Startup analysis execution.
    - Financial calculations.
    - Analysis input construction.
    - Prompt construction.
    - LLM invocation.
    - Response parsing.
    - Persistence.
    - Transaction management.
    - API response/schema construction.
"""

from __future__ import annotations

from uuid import UUID

from app.models.analysis import StartupAnalysis
from app.repositories.startup_analysis import StartupAnalysisRepository


class StartupAnalysisHistoryService:
    """Read-only service for persisted startup-analysis history."""

    def __init__(
        self,
        *,
        repository: StartupAnalysisRepository,
    ) -> None:
        self._repository = repository

    def list_history(
        self,
        startup_id: UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[StartupAnalysis], int]:
        """
        Return paginated analysis history for a startup.

        Parameters
        ----------
        startup_id:
            Startup whose historical analyses should be returned.

        page:
            One-based page number.

        per_page:
            Maximum number of analyses returned for the page.

        Returns
        -------
        tuple[list[StartupAnalysis], int]
            The requested history page and total number of matching
            analyses.

        Notes
        -----
        Ordering and pagination are owned by the repository.
        This service does not perform in-memory sorting or slicing.
        """

        return self._repository.list_by_startup(
            startup_id,
            page=page,
            per_page=per_page,
        )

    def get_history(
        self,
        startup_id: UUID,
        analysis_id: UUID,
    ) -> StartupAnalysis | None:
        """
        Return one historical analysis belonging to a startup.

        The startup_id constraint is deliberately passed to the
        repository so that cross-startup analysis access is prevented
        at the query boundary.
        """

        return self._repository.get_by_startup_and_id(
            startup_id,
            analysis_id,
        )


__all__ = [
    "StartupAnalysisHistoryService",
]
