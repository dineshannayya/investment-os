"""
Tests for LocalStorageProvider.
"""

from __future__ import annotations

import pytest

from app.storage.local import LocalStorageProvider


class TestLocalStorageProvider:
    """Tests for LocalStorageProvider."""

    # -------------------------------------------------------------------------
    # Construction
    # -------------------------------------------------------------------------

    def test_initializes_storage_directory(
        self,
        tmp_path,
    ) -> None:
        """Provider creates the storage root."""

        root = tmp_path / "storage"

        assert not root.exists()

        LocalStorageProvider(root)

        assert root.exists()
        assert root.is_dir()

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    def test_save_file(
        self,
        tmp_path,
    ) -> None:
        """Save a file."""

        provider = LocalStorageProvider(tmp_path)

        data = b"Hello Investment OS"

        result = provider.save(
            data=data,
            storage_path="startup1/doc1/test.txt",
            filename="test.txt",
            mime_type="text/plain",
        )

        assert result.filename == "test.txt"
        assert result.storage_path == "startup1/doc1/test.txt"
        assert result.file_size == len(data)
        assert provider.exists(result.storage_path)

    # -------------------------------------------------------------------------
    # Open
    # -------------------------------------------------------------------------

    def test_open_file(
        self,
        tmp_path,
    ) -> None:
        """Read file contents."""

        provider = LocalStorageProvider(tmp_path)

        data = b"Investment AI"

        provider.save(
            data=data,
            storage_path="a/b/file.txt",
            filename="file.txt",
            mime_type="text/plain",
        )

        assert provider.open("a/b/file.txt") == data

    # -------------------------------------------------------------------------
    # Exists
    # -------------------------------------------------------------------------

    def test_exists_true(
        self,
        tmp_path,
    ) -> None:
        """Existing file."""

        provider = LocalStorageProvider(tmp_path)

        provider.save(
            data=b"abc",
            storage_path="exists.txt",
            filename="exists.txt",
            mime_type="text/plain",
        )

        assert provider.exists("exists.txt")

    def test_exists_false(
        self,
        tmp_path,
    ) -> None:
        """Missing file."""

        provider = LocalStorageProvider(tmp_path)

        assert not provider.exists("missing.txt")

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def test_metadata_existing_file(
        self,
        tmp_path,
    ) -> None:
        """Metadata for existing file."""

        provider = LocalStorageProvider(tmp_path)

        data = b"123456"

        provider.save(
            data=data,
            storage_path="meta.txt",
            filename="meta.txt",
            mime_type="text/plain",
        )

        metadata = provider.metadata("meta.txt")

        assert metadata.exists
        assert metadata.filename == "meta.txt"
        assert metadata.file_size == len(data)
        assert metadata.mime_type == "text/plain"

    def test_metadata_missing_file(
        self,
        tmp_path,
    ) -> None:
        """Metadata for missing file."""

        provider = LocalStorageProvider(tmp_path)

        metadata = provider.metadata("missing.txt")

        assert not metadata.exists
        assert metadata.file_size == 0

    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    def test_delete_file(
        self,
        tmp_path,
    ) -> None:
        """Delete existing file."""

        provider = LocalStorageProvider(tmp_path)

        provider.save(
            data=b"abc",
            storage_path="delete.txt",
            filename="delete.txt",
            mime_type="text/plain",
        )

        provider.delete("delete.txt")

        assert not provider.exists("delete.txt")

    def test_delete_missing_file(
        self,
        tmp_path,
    ) -> None:
        """Deleting a missing file should be harmless."""

        provider = LocalStorageProvider(tmp_path)

        provider.delete("missing.txt")

        assert not provider.exists("missing.txt")

    # -------------------------------------------------------------------------
    # Path
    # -------------------------------------------------------------------------

    def test_path_returns_absolute_path(
        self,
        tmp_path,
    ) -> None:
        """Filesystem path."""

        provider = LocalStorageProvider(tmp_path)

        path = provider.path("folder/file.txt")

        assert path.is_absolute()
        assert path.name == "file.txt"

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "storage_path",
        [
            "../outside.txt",
            "../../etc/passwd",
            "/absolute/path.txt",
        ],
    )
    def test_path_traversal_rejected(
        self,
        tmp_path,
        storage_path,
    ) -> None:
        """Reject path traversal attempts."""

        provider = LocalStorageProvider(tmp_path)

        with pytest.raises(ValueError):
            provider.save(
                data=b"attack",
                storage_path=storage_path,
                filename="attack.txt",
                mime_type="text/plain",
            )
