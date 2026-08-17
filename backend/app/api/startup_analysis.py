"""
Startup Analysis API.

HTTP endpoints for executing and retrieving startup analysis.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config.status_codes import HTTP_CREATED
from app.core.database.dependencies import get_db
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.schemas.response import ApiResponse
from app.schemas.startup_analysis import (
    StartupAnalysisHistoryPage,
    StartupAnalysisHistoryResponse,
    StartupAnalysisRequest,
    StartupAnalysisResponse,
    StartupAnalysisHistoryItem,
)
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)
from app.services.startup_analysis_history import (
    StartupAnalysisHistoryService,
)


# =============================================================================
# Router
# =============================================================================


router = APIRouter(
    prefix="/startups",
    tags=["Startup Analysis"],
)


# =============================================================================
# Execution Service Dependency
# =============================================================================


def get_startup_analysis_application_service(
    db: Annotated[Session, Depends(get_db)],
) -> StartupAnalysisApplicationService:
    """
    Return StartupAnalysisApplicationService.

    The database session is owned by the request dependency and injected
    into the application service.

    The application service then constructs/injects:
        - StartupService
        - StartupAnalysisOrchestrator
        - StartupAnalysisPersistenceService

    Transaction ownership remains inside
    StartupAnalysisPersistenceService.
    """

    return StartupAnalysisApplicationService(
        session=db,
    )


StartupAnalysisApplicationServiceDep = Annotated[
    StartupAnalysisApplicationService,
    Depends(get_startup_analysis_application_service),
]


# =============================================================================
# History Service Dependency
# =============================================================================


def get_startup_analysis_history_service(
    db: Annotated[Session, Depends(get_db)],
) -> StartupAnalysisHistoryService:
    """
    Return StartupAnalysisHistoryService.

    History is a read-only use case. The service receives a repository
    explicitly and does not own transaction management.
    """

    repository = StartupAnalysisRepository(db)

    return StartupAnalysisHistoryService(
        repository=repository,
    )


StartupAnalysisHistoryServiceDep = Annotated[
    StartupAnalysisHistoryService,
    Depends(get_startup_analysis_history_service),
]


# =============================================================================
# Execute Startup Analysis
# =============================================================================


@router.post(
    "/{startup_id}/analysis",
    response_model=ApiResponse[StartupAnalysisResponse],
    status_code=HTTP_CREATED,
    summary="Analyze Startup",
)
def analyze_startup(
    startup_id: UUID,
    request: StartupAnalysisRequest,
    service: StartupAnalysisApplicationServiceDep,
) -> ApiResponse[StartupAnalysisResponse]:
    """
    Execute and persist startup analysis.

    The API exposes only the requested analysis mode.

    Model selection, thinking configuration, token limits,
    temperature, and analysis version are resolved internally.
    """

    analysis = service.analyze(
        startup_id=startup_id,
        mode=request.mode,
    )

    return ApiResponse.ok(
        data=StartupAnalysisResponse.model_validate(
            analysis,
            from_attributes=True,
        ),
        message="Startup analysis completed",
    )


# =============================================================================
# Analysis History
# =============================================================================

@router.get(
    "/{startup_id}/analysis",
    response_model=ApiResponse[StartupAnalysisHistoryPage],
    summary="List Startup Analysis History",
)
def list_startup_analysis_history(
    startup_id: UUID,
    service: StartupAnalysisHistoryServiceDep,
    page: Annotated[
        int,
        Query(
            ge=1,
            description="One-based history page number.",
        ),
    ] = 1,
    per_page: Annotated[
        int,
        Query(
            ge=1,
            description="Number of history records per page.",
        ),
    ] = 20,
) -> ApiResponse[StartupAnalysisHistoryPage]:
    """
    Return paginated analysis history for a startup.

    Results are returned newest first by the repository.
    """

    analyses, total_items = service.list_history(
        startup_id,
        page=page,
        per_page=per_page,
    )

    total_pages = (
        (total_items + per_page - 1) // per_page
        if total_items > 0
        else 0
    )

    history_items = [
        StartupAnalysisHistoryItem.model_validate(
            analysis,
            from_attributes=True,
        )
        for analysis in analyses
    ]

    return ApiResponse.ok(
        data=StartupAnalysisHistoryPage(
            items=history_items,
            pagination={
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages,
            },
        ),
        message="Startup analysis history retrieved",
    )



# =============================================================================
# Analysis History Detail
# =============================================================================


@router.get(
    "/{startup_id}/analysis/{analysis_id}",
    response_model=ApiResponse[StartupAnalysisHistoryResponse],
    summary="Get Startup Analysis History",
)
def get_startup_analysis_history(
    startup_id: UUID,
    analysis_id: UUID,
    service: StartupAnalysisHistoryServiceDep,
) -> ApiResponse[StartupAnalysisHistoryResponse]:
    """
    Return one historical startup-analysis execution.

    The repository performs startup-scoped lookup, so an analysis
    belonging to another startup is treated as not found.
    """

    analysis = service.get_history(
        startup_id,
        analysis_id,
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Startup analysis not found",
        )

    return ApiResponse.ok(
        data=StartupAnalysisHistoryResponse.model_validate(
            analysis,
            from_attributes=True,
        ),
        message="Startup analysis history retrieved",
    )


__all__ = [
    "router",
    "get_startup_analysis_application_service",
    "get_startup_analysis_history_service",
]
