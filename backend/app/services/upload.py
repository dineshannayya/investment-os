"""
Document upload service.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4
from uuid import UUID
from app.models.enums import DocumentType

from app.models.document import Document
from app.models.enums import DocumentStatus
from app.schemas.document import DocumentCreate
from app.services.document import DocumentService
from app.storage.service import StorageService


@dataclass(slots=True)
class UploadRequest:
    """Input for document upload."""

    startup_id: UUID
    document_type: DocumentType
    title: str
    filename: str
    mime_type: str
    data: bytes
    description: str | None = None


class UploadService:
    """Coordinates document upload."""

    def __init__(
        self,
        storage: StorageService,
        documents: DocumentService,
    ) -> None:
        self._storage = storage
        self._documents = documents

    def upload(
        self,
        request: UploadRequest,
    ) -> Document:
        """
        Upload a document.

        Workflow

        Validate
            ↓
        Store file
            ↓
        Create document
            ↓
        Return document
        """

        document_id = uuid4()

        file_hash = self._storage.sha256(request.data)

        existing = self._documents.get_by_file_hash(file_hash)

        if existing is not None:
            raise ValueError("Document already exists.")

        storage = self._storage.save(
            startup_id=request.startup_id,
            document_id=document_id,
            filename=request.filename,
            mime_type=request.mime_type,
            data=request.data,
        )

        payload = DocumentCreate(
            startup_id=request.startup_id,
            document_type=request.document_type,
            title=request.title,
            description=request.description,
            filename=storage.filename,
            original_filename=request.filename,
            mime_type=storage.mime_type,
            file_size=storage.file_size,
            file_hash=storage.file_hash,
            storage_path=storage.storage_path,
        )

        document = self._documents.create_document(
            payload,
        )

        document.status = DocumentStatus.UPLOADED

        return document
