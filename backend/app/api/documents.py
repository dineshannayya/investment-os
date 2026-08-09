"""
Document API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database.dependencies import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
)
from app.services.document import DocumentService

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# -------------------------------------------------------------------------
# Dependency Injection
# -------------------------------------------------------------------------


def get_document_service(
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> DocumentService:
    """Return DocumentService."""

    return DocumentService(db)


DocumentServiceDep = Annotated[
    DocumentService,
    Depends(get_document_service),
]


# -------------------------------------------------------------------------
# Create
# -------------------------------------------------------------------------


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    payload: DocumentCreate,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Create a document."""

    try:
        return service.create_document(payload)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# -------------------------------------------------------------------------
# Read
# -------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[DocumentSummary],
)
def list_documents(
    service: DocumentServiceDep,
    startup_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[DocumentSummary]:
    """List documents."""

    if startup_id is not None:
        return service.list_documents_by_startup(startup_id)

    if search:
        return service.search_documents(search)

    return service.list_documents()


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Return document."""

    document = service.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


# -------------------------------------------------------------------------
# Update
# -------------------------------------------------------------------------


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
)
def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Update document."""

    try:
        return service.update_document(
            document_id,
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


# -------------------------------------------------------------------------
# Delete
# -------------------------------------------------------------------------


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> Response:
    """Delete document."""

    try:
        service.delete_document(document_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
