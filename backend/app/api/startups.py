"""
Startup API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database.dependencies import get_db
from app.schemas.startup import ( 
    StartupCreate, 
    StartupResponse,
    StartupSummary,
    StartupUpdate,
)
from app.services.startup import StartupService


router = APIRouter(
    prefix="/startups",
    tags=["Startups"],
)


# ---------------------------------
# Dependency
# ---------------------------------

def get_startup_service(
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> StartupService:
    return StartupService(db)


StartupServiceDep = Annotated[
    StartupService,
    Depends(get_startup_service),
]

# ---------------------------------
# POST
# ---------------------------------
@router.post(
    "",
    response_model=StartupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_startup(
    payload: StartupCreate,
    service: StartupServiceDep,
)-> StartupResponse:
    """Create startup."""

    try:
        return service.create_startup(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------
# GET (List)
# ---------------------------------
@router.get(
    "",
    response_model=list[StartupSummary],
)
def list_startups(
    service: StartupServiceDep,
)-> list[StartupSummary]:
    """List startups."""

    return service.list_startups()

@router.get(
    "/{startup_id}",
    response_model=StartupResponse,
)
def get_startup(
    startup_id: UUID,
    service: StartupServiceDep,
)-> StartupResponse:
    """Return startup."""

    startup = service.get_startup(startup_id)

    if startup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )

    return startup

# ---------------------------------
# PATCH
# ---------------------------------
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

    try:
        return service.update_startup(
            startup_id,
            payload,
        )
    except ValueError as exc:
        message = str(exc)

        if "not found" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

# ---------------------------------
# DELETE
# ---------------------------------
@router.delete(
    "/{startup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_startup(
    startup_id: UUID,
    service: StartupServiceDep,
) -> Response:
    """Delete startup."""

    try:
        service.delete_startup(startup_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response( 
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ------------------------------


