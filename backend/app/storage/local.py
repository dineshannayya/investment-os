"""
Local filesystem storage provider.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.storage.base import (
    StorageMetadata,
    StorageProvider,
    StorageResult,
)


class LocalStorageProvider(StorageProvider):
    """Store files on the local filesystem."""

    def __init__(
        self,
        root: str | Path,
    ) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(
            parents=True,
            exist_ok=True,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _resolve_path(
        self,
        storage_path: str,
    ) -> Path:
        """
        Resolve a storage path safely beneath the storage root.
        """

        path = (self._root / storage_path).resolve()

        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise ValueError(
                f"Invalid storage path: {storage_path}"
            ) from exc

        return path

    # -------------------------------------------------------------------------
    # StorageProvider
    # -------------------------------------------------------------------------

    def save(
        self,
        *,
        data: bytes,
        storage_path: str,
        filename: str,
        mime_type: str,
    ) -> StorageResult:
        """Store a file."""

        path = self._resolve_path(storage_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(data)

        return StorageResult(
            filename=filename,
            storage_path=storage_path,
            file_size=len(data),
            file_hash="",
            mime_type=mime_type,
        )

    def open(
        self,
        storage_path: str,
    ) -> bytes:
        """Read a stored file."""

        return self._resolve_path(
            storage_path
        ).read_bytes()

    def delete(
        self,
        storage_path: str,
    ) -> None:
        """Delete a stored file."""

        path = self._resolve_path(storage_path)

        if path.exists():
            path.unlink()

    def exists(
        self,
        storage_path: str,
    ) -> bool:
        """Return True if the file exists."""

        return self._resolve_path(
            storage_path
        ).exists()

    def metadata(
        self,
        storage_path: str,
    ) -> StorageMetadata:
        """Return metadata for a stored file."""

        path = self._resolve_path(storage_path)

        exists = path.exists()

        if exists:
            size = path.stat().st_size
            mime_type = (
                mimetypes.guess_type(path.name)[0]
                or "application/octet-stream"
            )
            filename = path.name
        else:
            size = 0
            mime_type = "application/octet-stream"
            filename = path.name

        return StorageMetadata(
            filename=filename,
            storage_path=storage_path,
            file_size=size,
            mime_type=mime_type,
            exists=exists,
        )

    def path(
        self,
        storage_path: str,
    ) -> Path:
        """Return filesystem path."""

        return self._resolve_path(storage_path)
