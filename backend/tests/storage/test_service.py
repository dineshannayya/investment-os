"""
Tests for StorageService.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from app.storage.service import StorageService
from tests.storage.fake_provider import FakeStorageProvider


class TestStorageService:
    """Tests for StorageService."""

    @staticmethod
    def _create_service():
        provider = FakeStorageProvider()
        service = StorageService(provider)
        return service, provider

    # ------------------------------------------------------------------
    # Hash
    # ------------------------------------------------------------------

    def test_sha256(self):
        """SHA256 digest."""

        digest = StorageService.sha256(b"abc")

        assert digest == hashlib.sha256(b"abc").hexdigest()

    # ------------------------------------------------------------------
    # Path
    # ------------------------------------------------------------------

    def test_build_storage_path(self):
        """Storage path."""

        startup_id = uuid4()
        document_id = uuid4()

        path = StorageService.build_storage_path(
            startup_id,
            document_id,
            "pitch.pdf",
        )

        assert str(startup_id) in path
        assert str(document_id) in path
        assert path.endswith("pitch.pdf")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def test_save(self):
        """Save document."""

        service, provider = self._create_service()

        startup_id = uuid4()
        document_id = uuid4()

        data = b"Investment OS"

        result = service.save(
            startup_id=startup_id,
            document_id=document_id,
            filename="pitch.pdf",
            mime_type="application/pdf",
            data=data,
        )

        assert provider.saved_args is not None
        assert result.file_size == len(data)
        assert result.file_hash == hashlib.sha256(data).hexdigest()

    def test_save_empty_file(self):
        """Reject empty file."""

        service, _ = self._create_service()

        with pytest.raises(ValueError):
            service.save(
                startup_id=uuid4(),
                document_id=uuid4(),
                filename="empty.pdf",
                mime_type="application/pdf",
                data=b"",
            )

    # ------------------------------------------------------------------
    # Open
    # ------------------------------------------------------------------

    def test_open(self):
        """Open document."""

        service, provider = self._create_service()

        provider.storage["doc.txt"] = b"hello"

        assert service.open("doc.txt") == b"hello"

    # ------------------------------------------------------------------
    # Exists
    # ------------------------------------------------------------------

    def test_exists_true(self):
        """Existing document."""

        service, provider = self._create_service()

        provider.storage["doc.txt"] = b"abc"

        assert service.exists("doc.txt")

    def test_exists_false(self):
        """Missing document."""

        service, _ = self._create_service()

        assert not service.exists("missing.txt")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_metadata(self):
        """Metadata."""

        service, provider = self._create_service()

        provider.storage["doc.txt"] = b"abcdef"

        metadata = service.metadata("doc.txt")

        assert metadata.exists
        assert metadata.file_size == 6

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_delete(self):
        """Delete document."""

        service, provider = self._create_service()

        provider.storage["doc.txt"] = b"abc"

        service.delete("doc.txt")

        assert not provider.exists("doc.txt")
