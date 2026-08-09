"""
Tests for Document API.
"""

from __future__ import annotations

from uuid import uuid4

from starlette import status

from app.models.enums import (
    DocumentStatus,
    DocumentType,
)


class TestDocumentAPI:
    """Test Document API."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def test_create_document(
        self,
        client,
        startup_factory,
    ) -> None:
        startup = startup_factory()

        payload = {
            "startup_id": str(startup.id),
            "document_type": DocumentType.PITCH_DECK.value,
            "title": "Pitch Deck",
            "description": "Seed presentation",
            "filename": "pitch.pdf",
            "original_filename": "pitch.pdf",
            "mime_type": "application/pdf",
            "file_size": 12345,
            "file_hash": "hash-001",
            "storage_path": "/tmp/pitch.pdf",
        }

        response = client.post(
            "/api/v1/documents",
            json=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED

        body = response.json()

        assert body["title"] == payload["title"]
        assert body["document_type"] == payload["document_type"]
        assert body["startup_id"] == str(startup.id)
        assert body["file_hash"] == payload["file_hash"]
        assert "id" in body

    def test_create_duplicate_hash(
        self,
        client,
        startup_factory,
        document_factory,
    ) -> None:
        startup = startup_factory()

        document_factory(
            startup=startup,
            file_hash="duplicate-hash",
        )

        payload = {
            "startup_id": str(startup.id),
            "document_type": DocumentType.PITCH_DECK.value,
            "title": "Pitch Deck",
            "filename": "pitch.pdf",
            "original_filename": "pitch.pdf",
            "mime_type": "application/pdf",
            "file_size": 100,
            "file_hash": "duplicate-hash",
            "storage_path": "/tmp/pitch.pdf",
        }

        response = client.post(
            "/api/v1/documents",
            json=payload,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unknown_startup(
        self,
        client,
    ) -> None:
        payload = {
            "startup_id": str(uuid4()),
            "document_type": DocumentType.PITCH_DECK.value,
            "title": "Pitch Deck",
            "filename": "pitch.pdf",
            "original_filename": "pitch.pdf",
            "mime_type": "application/pdf",
            "file_size": 100,
            "file_hash": "hash-001",
            "storage_path": "/tmp/pitch.pdf",
        }

        response = client.post(
            "/api/v1/documents",
            json=payload,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_document_invalid_payload(
        self,
        client,
    ) -> None:
        response = client.post(
            "/api/v1/documents",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def test_list_documents(
        self,
        client,
        document_factory,
    ) -> None:
        document_factory()
        document_factory()

        response = client.get("/api/v1/documents")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_list_documents_by_startup(
        self,
        client,
        startup_factory,
        document_factory,
    ) -> None:
        startup1 = startup_factory()
        startup2 = startup_factory()

        document_factory(startup=startup1)
        document_factory(startup=startup1)
        document_factory(startup=startup2)

        response = client.get(
            f"/api/v1/documents?startup_id={startup1.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

    def test_search_documents(
        self,
        client,
        document_factory,
    ) -> None:
        document_factory(title="Pitch Deck")
        document_factory(title="Financial Model")

        response = client.get(
            "/api/v1/documents?search=Pitch"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_get_document(
        self,
        client,
        document_factory,
    ) -> None:
        document = document_factory()

        response = client.get(
            f"/api/v1/documents/{document.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(document.id)

    def test_get_unknown_document(
        self,
        client,
    ) -> None:
        response = client.get(
            f"/api/v1/documents/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def test_update_document(
        self,
        client,
        document_factory,
    ) -> None:
        document = document_factory()

        response = client.patch(
            f"/api/v1/documents/{document.id}",
            json={
                "title": "Updated Pitch Deck",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Pitch Deck"

    def test_update_duplicate_hash(
        self,
        client,
        document_factory,
    ) -> None:
        doc1 = document_factory(file_hash="hash-001")
        doc2 = document_factory(file_hash="hash-002")

        response = client.patch(
            f"/api/v1/documents/{doc2.id}",
            json={
                "file_hash": doc1.file_hash,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_unknown_document(
        self,
        client,
    ) -> None:
        response = client.patch(
            f"/api/v1/documents/{uuid4()}",
            json={
                "title": "Updated",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_delete_document(
        self,
        client,
        document_factory,
    ) -> None:
        document = document_factory()

        response = client.delete(
            f"/api/v1/documents/{document.id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = client.get(
            f"/api/v1/documents/{document.id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_unknown_document(
        self,
        client,
    ) -> None:
        response = client.delete(
            f"/api/v1/documents/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
