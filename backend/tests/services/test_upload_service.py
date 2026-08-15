"""
Tests for UploadService.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.document import Document
from app.models.enums import (
    DocumentStatus,
    DocumentType,
)
from app.schemas.document import DocumentCreate
from app.services.upload import (
    UploadRequest,
    UploadService,
)
from app.storage.base import StorageResult

# ============================================================================
# Fake Storage Service
# ============================================================================


class FakeStorageService:
    """Fake StorageService."""

    def __init__(self) -> None:
        self.saved = None


    def sha256(self, data: bytes) -> str:
        return "sha256-test"

    def save(
        self,
        *,
        startup_id,
        document_id,
        filename,
        mime_type,
        data,
    ) -> StorageResult:
        self.saved = {
            "startup_id": startup_id,
            "document_id": document_id,
            "filename": filename,
            "mime_type": mime_type,
            "data": data,
        }

        return StorageResult(
            filename=filename,
            storage_path=f"{startup_id}/{document_id}/{filename}",
            file_size=len(data),
            file_hash="sha256-test",
            mime_type=mime_type,
        )


# ============================================================================
# Fake Document Service
# ============================================================================


class FakeDocumentService:
    """Fake DocumentService."""

    def __init__(self) -> None:
        self.payload: DocumentCreate | None = None

    def get_by_file_hash(self, file_hash: str):
        return None

    def create_document(
        self,
        payload: DocumentCreate,
    ) -> Document:
        self.payload = payload

        document = Document(
            startup_id=payload.startup_id,
            document_type=payload.document_type,
            title=payload.title,
            description=payload.description,
            filename=payload.filename,
            original_filename=payload.original_filename,
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            file_hash=payload.file_hash,
            storage_path=payload.storage_path,
        )

        document.id = uuid4()
        document.version = 1
        document.status = DocumentStatus.UPLOADED

        return document


# ============================================================================
# Tests
# ============================================================================


class TestUploadService:
    """Tests for UploadService."""

    @staticmethod
    def _create_service():
        storage = FakeStorageService()
        documents = FakeDocumentService()

        service = UploadService(
            storage=storage,
            documents=documents,
        )

        return service, storage, documents

    # ---------------------------------------------------------------------
    # Upload
    # ---------------------------------------------------------------------

    def test_upload_document(self):
        """Upload a document."""

        service, storage, documents = self._create_service()

        startup_id = uuid4()

        request = UploadRequest(
            startup_id=startup_id,
            document_type=DocumentType.PITCH_DECK,
            title="Pitch Deck",
            filename="pitch.pdf",
            mime_type="application/pdf",
            data=b"Investment OS",
        )

        document = service.upload(request)

        assert document.title == "Pitch Deck"
        assert document.status == DocumentStatus.UPLOADED

        assert storage.saved is not None
        assert storage.saved["startup_id"] == startup_id

        assert documents.payload is not None
        assert documents.payload.file_hash == "sha256-test"

    def test_upload_preserves_filename(self):
        """Original filename is preserved."""

        service, _, documents = self._create_service()

        startup_id = uuid4()

        request = UploadRequest(
            startup_id=startup_id,
            document_type=DocumentType.PITCH_DECK,
            title="Deck",
            filename="company_pitch.pdf",
            mime_type="application/pdf",
            data=b"123",
        )

        service.upload(request)

        assert documents.payload is not None
        assert documents.payload.filename == "company_pitch.pdf"
        assert (
            documents.payload.original_filename
            == "company_pitch.pdf"
        )

    def test_upload_description(self):
        """Description is propagated."""

        service, _, documents = self._create_service()

        request = UploadRequest(
            startup_id=uuid4(),
            document_type=DocumentType.PITCH_DECK,
            title="Pitch",
            filename="pitch.pdf",
            mime_type="application/pdf",
            description="Seed round deck",
            data=b"abc",
        )

        service.upload(request)

        assert documents.payload is not None
        assert (
            documents.payload.description
            == "Seed round deck"
        )

    def test_storage_path_is_forwarded(self):
        """Storage path returned by storage service is used."""

        service, storage, documents = self._create_service()

        startup_id = uuid4()

        request = UploadRequest(
            startup_id=startup_id,
            document_type=DocumentType.PITCH_DECK,
            title="Pitch",
            filename="deck.pdf",
            mime_type="application/pdf",
            data=b"abc",
        )

        service.upload(request)

        assert documents.payload is not None

        assert (
            documents.payload.storage_path
            == f"{startup_id}/{storage.saved['document_id']}/deck.pdf"
        )

    def test_storage_failure_propagates(self):
        """Storage failures are propagated."""

        class BrokenStorage(FakeStorageService):
            def save(self, **kwargs):
                raise RuntimeError("storage failed")

        service = UploadService(
            storage=BrokenStorage(),
            documents=FakeDocumentService(),
        )

        request = UploadRequest(
            startup_id=uuid4(),
            document_type=DocumentType.PITCH_DECK,
            title="Pitch",
            filename="deck.pdf",
            mime_type="application/pdf",
            data=b"abc",
        )

        with pytest.raises(RuntimeError):
            service.upload(request)

    def test_document_creation_failure_propagates(self):
        """Document service failures are propagated."""

        class BrokenDocumentService(FakeDocumentService):
            def create_document(self, payload):
                raise ValueError("duplicate document")

        service = UploadService(
            storage=FakeStorageService(),
            documents=BrokenDocumentService(),
        )

        request = UploadRequest(
            startup_id=uuid4(),
            document_type=DocumentType.PITCH_DECK,
            title="Pitch",
            filename="deck.pdf",
            mime_type="application/pdf",
            data=b"abc",
        )

        with pytest.raises(ValueError):
            service.upload(request)
