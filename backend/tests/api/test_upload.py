"""
Tests for document upload API.
"""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from uuid import uuid4

from starlette import status

from app.models.enums import DocumentStatus, DocumentType


class TestUploadAPI:
    """Tests for document upload endpoint."""

    # ---------------------------------------------------------------------
    # Upload
    # ---------------------------------------------------------------------

    def test_upload_document(
        self,
        client,
        startup_factory,
    ) -> None:
        """Upload a PDF."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
                "description": "Seed round deck",
            },
            files={
                "file": (
                    "pitch.pdf",
                    BytesIO(b"Investment OS"),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        body = response.json()

        assert body["startup_id"] == str(startup.id)
        assert body["title"] == "Pitch Deck"
        assert body["filename"] == "pitch.pdf"
        assert body["original_filename"] == "pitch.pdf"
        assert body["mime_type"] == "application/pdf"
        assert body["status"] == DocumentStatus.UPLOADED.value

    def test_upload_without_description(
        self,
        client,
        startup_factory,
    ) -> None:
        """Description is optional."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
            },
            files={
                "file": (
                    "pitch.pdf",
                    BytesIO(b"123"),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_unknown_startup(
        self,
        client,
    ) -> None:
        """Unknown startup."""

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(uuid4()),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
            },
            files={
                "file": (
                    "pitch.pdf",
                    BytesIO(b"123"),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_duplicate_file(
        self,
        client,
        startup_factory,
        document_factory,
    ) -> None:
        """Duplicate SHA256."""

        startup = startup_factory()

        payload = b"Investment OS"
        
        document_factory(
            startup=startup,
            file_hash=sha256(payload).hexdigest(),
        )

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
            },
            files={
                "file": (
                    "pitch.pdf",
                    BytesIO(b"Investment OS"),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_missing_file(
        self,
        client,
        startup_factory,
    ) -> None:
        """Multipart file missing."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_missing_title(
        self,
        client,
        startup_factory,
    ) -> None:
        """Title missing."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
            },
            files={
                "file": (
                    "pitch.pdf",
                    BytesIO(b"123"),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_empty_file(
        self,
        client,
        startup_factory,
    ) -> None:
        """Reject empty upload."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.PITCH_DECK.value,
                "title": "Pitch Deck",
            },
            files={
                "file": (
                    "empty.pdf",
                    BytesIO(b""),
                    "application/pdf",
                ),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_text_file(
        self,
        client,
        startup_factory,
    ) -> None:
        """Upload plain text."""

        startup = startup_factory()

        response = client.post(
            "/api/v1/documents/upload",
            data={
                "startup_id": str(startup.id),
                "document_type": DocumentType.OTHER.value,
                "title": "Notes",
            },
            files={
                "file": (
                    "notes.txt",
                    BytesIO(b"hello"),
                    "text/plain",
                ),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
