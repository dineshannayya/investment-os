
from __future__ import annotations

from app.storage.base import (
    StorageMetadata,
    StorageResult,
)


class FakeStorageProvider:
    """In-memory storage provider for unit tests."""

    def __init__(self) -> None:
        self.storage: dict[str, bytes] = {}
        self.saved_args = None

    def save(
        self,
        *,
        data: bytes,
        storage_path: str,
        filename: str,
        mime_type: str,
    ) -> StorageResult:
        self.saved_args = {
            "data": data,
            "storage_path": storage_path,
            "filename": filename,
            "mime_type": mime_type,
        }

        self.storage[storage_path] = data

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
        return self.storage[storage_path]

    def delete(
        self,
        storage_path: str,
    ) -> None:
        self.storage.pop(storage_path, None)

    def exists(
        self,
        storage_path: str,
    ) -> bool:
        return storage_path in self.storage

    def metadata(
        self,
        storage_path: str,
    ) -> StorageMetadata:
        exists = storage_path in self.storage

        return StorageMetadata(
            filename=storage_path.split("/")[-1],
            storage_path=storage_path,
            file_size=len(self.storage.get(storage_path, b"")),
            mime_type="text/plain",
            exists=exists,
        )

    def path(self, storage_path: str):
        raise NotImplementedError
