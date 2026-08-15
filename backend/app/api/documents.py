"""
Document API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
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

from app.core.config.settings import settings
from app.models.enums import DocumentType
from app.services.upload import (
    UploadRequest,
    UploadService,
)
from app.storage.local import LocalStorageProvider
from app.storage.service import StorageService


# -------------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------------
def create_storage_service() -> StorageService:
    provider = LocalStorageProvider(
        settings.storage_root,
    )
    return StorageService(provider)


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


def get_storage_service() -> StorageService:
    """
    Return StorageService.
    """
    return create_storage_service()


StorageServiceDep = Annotated[
    StorageService,
    Depends(get_storage_service),
]

def get_upload_service(
    documents: DocumentServiceDep,
    storage: StorageServiceDep,
) -> UploadService:
    """
    Return UploadService.
    """

    return UploadService(
        storage=storage,
        documents=documents,
    )

UploadServiceDep = Annotated[
    UploadService,
    Depends(get_upload_service),
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
# Upload
# -------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    startup_id: UUID = Form(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    *,
    service: UploadServiceDep,
    description: str | None = Form(default=None),
) -> DocumentResponse:
    """
    Upload a document.
    """

    data = await file.read()

    request = UploadRequest(
        startup_id=startup_id,
        document_type=document_type,
        title=title,
        filename=file.filename or "upload.bin",
        mime_type=file.content_type or "application/octet-stream",
        description=description,
        data=data,
    )

    try:
        return service.upload(request)

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
