"""
Storage provider abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

# ============================================================================
# Storage Result
# ============================================================================


@dataclass(frozen=True, slots=True)
class StorageResult:
    """
    Result returned after storing a file.
    """

    filename: str
    storage_path: str
    file_size: int
    file_hash: str
    mime_type: str


# ============================================================================
# Storage Metadata
# ============================================================================


@dataclass(frozen=True, slots=True)
class StorageMetadata:
    """
    Metadata describing an existing stored object.
    """

    filename: str
    storage_path: str
    file_size: int
    mime_type: str
    exists: bool


# ============================================================================
# Storage Provider
# ============================================================================


class StorageProvider(ABC):
    """
    Abstract storage provider.
    """

    @abstractmethod
    def save(
        self,
        *,
        data: bytes,
        storage_path: str,
        filename: str,
        mime_type: str,
    ) -> StorageResult:
        """
        Store a file.
        """
        raise NotImplementedError

    @abstractmethod
    def open(
        self,
        storage_path: str,
    ) -> bytes:
        """
        Read file contents.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        storage_path: str,
    ) -> None:
        """
        Delete a stored object.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        storage_path: str,
    ) -> bool:
        """
        Return True if object exists.
        """
        raise NotImplementedError

    @abstractmethod
    def metadata(
        self,
        storage_path: str,
    ) -> StorageMetadata:
        """
        Return metadata for a stored object.
        """
        raise NotImplementedError

    @abstractmethod
    def path(
        self,
        storage_path: str,
    ) -> Path:
        """
        Return provider-specific path.

        For local storage this returns a filesystem Path.
        Cloud providers may raise NotImplementedError if
        filesystem paths are not applicable.
        """
        raise NotImplementedError
