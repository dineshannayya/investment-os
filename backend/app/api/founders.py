"""
Founder API endpoints.
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
from app.schemas.founder import (
    FounderCreate,
    FounderResponse,
    FounderUpdate,
)
from app.services.founder import FounderService

router = APIRouter(
    prefix="/founders",
    tags=["Founders"],
)


# ---------------------------------------------------------------------
# Dependency Injection
# ---------------------------------------------------------------------


def get_founder_service(
    db: Annotated[Session, Depends(get_db)],
) -> FounderService:
    """Return FounderService instance."""

    return FounderService(db)


FounderServiceDep = Annotated[
    FounderService,
    Depends(get_founder_service),
]


# ---------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------


@router.post(
    "",
    response_model=FounderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_founder(
    payload: FounderCreate,
    service: FounderServiceDep,
) -> FounderResponse:
    """Create a founder."""

    try:
        return service.create_founder(payload)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------


@router.get(
    "",
    response_model=list[FounderResponse],
)
def list_founders(
    service: FounderServiceDep,
) -> list[FounderResponse]:
    """List all founders."""

    return service.list_founders()


@router.get(
    "/{founder_id}",
    response_model=FounderResponse,
)
def get_founder(
    founder_id: UUID,
    service: FounderServiceDep,
) -> FounderResponse:
    """Return founder."""

    founder = service.get_founder(founder_id)

    if founder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Founder not found.",
        )

    return founder


# ---------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------


@router.patch(
    "/{founder_id}",
    response_model=FounderResponse,
)
def update_founder(
    founder_id: UUID,
    payload: FounderUpdate,
    service: FounderServiceDep,
) -> FounderResponse:
    """Update founder."""

    try:
        return service.update_founder(
            founder_id,
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


# ---------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------


@router.delete(
    "/{founder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_founder(
    founder_id: UUID,
    service: FounderServiceDep,
) -> Response:
    """Delete founder."""

    try:
        service.delete_founder(founder_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
