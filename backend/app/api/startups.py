"""
Startup API endpoints.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from fastapi import status
from sqlalchemy.orm import Session

from app.core.database.dependencies import get_db
from app.repositories.startup import StartupRepository
from app.schemas.startup import StartupCreate
from app.schemas.startup import StartupResponse
from app.schemas.startup import StartupSummary
from app.schemas.startup import StartupUpdate
from app.services.startup import StartupService

from typing import Annotated

router = APIRouter(
    prefix="/startups",
    tags=["Startups"],
)


# Dependency

def get_startup_service(
    db: Session = Depends(get_db),
) -> StartupService:
    """Return StartupService."""

    repository = StartupRepository(db)

    return StartupService(
        repository=repository,
        session=db,
    )

StartupServiceDep = Annotated[
    StartupService,
    Depends(get_startup_service),
]

# POST
@router.post(
    "",
    response_model=StartupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_startup(
    payload: StartupCreate,
    service: StartupServiceDep,
):
    """Create startup."""

    try:
        return service.create_startup(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


#GET (List)
@router.get(
    "",
    response_model=list[StartupSummary],
)
def list_startups(
    service: StartupServiceDep,
):
    """List startups."""

    return service.list_startups()

@router.get(
    "/{startup_id}",
    response_model=StartupResponse,
)
def get_startup(
    startup_id: UUID,
    service: StartupServiceDep,
):
    """Return startup."""

    startup = service.get_startup(startup_id)

    if startup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )

    return startup

# PATCH
@router.patch(
    "/{startup_id}",
    response_model=StartupResponse,
)
def update_startup(
    startup_id: UUID,
    payload: StartupUpdate,
    service: StartupServiceDep,
):
    """Update startup."""

    return service.update_startup(
        startup_id,
        payload,
    )

#DELETE
@router.delete(
    "/{startup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_startup(
    startup_id: UUID,
    service: StartupServiceDep,
):
    """Delete startup."""

    try:
        service.delete_startup(startup_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ------------------------------


