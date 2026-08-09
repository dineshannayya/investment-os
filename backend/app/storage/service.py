"""
Storage service.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from app.storage.base import (
    StorageProvider,
    StorageResult,
)


class StorageService:
    """High-level storage orchestration."""

    def __init__(
        self,
        provider: StorageProvider,
    ) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def sha256(
        data: bytes,
    ) -> str:
        """Return SHA-256 digest."""

        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def build_storage_path(
        startup_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str:
        """
        Build provider-independent storage path.
        """

        return str(
            Path(
                str(startup_id),
                str(document_id),
                filename,
            )
        )

    def resolve(
        self,
        storage_path: str,
    ) -> Path:
        """
        Resolve a storage path to an absolute filesystem path.
        """
    
        return self._backend.resolve(storage_path)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def save(
        self,
        *,
        startup_id: UUID,
        document_id: UUID,
        filename: str,
        mime_type: str,
        data: bytes,
    ) -> StorageResult:
        """
        Store a document.
        """

        if not data:
            raise ValueError(
                "File is empty."
            )

        storage_path = self.build_storage_path(
            startup_id,
            document_id,
            filename,
        )

        result = self._provider.save(
            data=data,
            storage_path=storage_path,
            filename=filename,
            mime_type=mime_type,
        )

        return StorageResult(
            filename=result.filename,
            storage_path=result.storage_path,
            file_size=result.file_size,
            file_hash=self.sha256(data),
            mime_type=result.mime_type,
        )

    def open(
        self,
        storage_path: str,
    ) -> bytes:
        """Read stored document."""

        return self._provider.open(
            storage_path,
        )

    def delete(
        self,
        storage_path: str,
    ) -> None:
        """Delete stored document."""

        self._provider.delete(
            storage_path,
        )

    def exists(
        self,
        storage_path: str,
    ) -> bool:
        """Return whether object exists."""

        return self._provider.exists(
            storage_path,
        )

    def metadata(
        self,
        storage_path: str,
    ):
        """Return object metadata."""

        return self._provider.metadata(
            storage_path,
        )
