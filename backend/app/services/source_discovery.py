"""
Source discovery service.

Discovers source files belonging to a startup and creates
SourceDocument metadata records.

Responsibilities:
    - recursively scan a source directory
    - identify supported file types
    - collect deterministic file metadata
    - calculate SHA256
    - classify broad source category from directory structure
    - return SourceDocument records

Non-responsibilities:
    - document extraction
    - financial interpretation
    - evidence generation
    - source reconciliation
    - investment scoring
    - LLM invocation
"""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.models.source_document import (
    SourceAuthority,
    SourceCategory,
    SourceDocument,
    SourceType,
    ExtractionStatus,
)
from app.processors.factory import create_processor_factory


class SourceDiscoveryError(RuntimeError):
    """Raised when source discovery cannot be completed."""


class SourceDiscoveryService:
    """
    Discover source files under a startup source directory.

    Discovery is deterministic and does not read document contents.
    """

    _EXTENSION_TO_SOURCE_TYPE: dict[str, SourceType] = {
        ".pdf": SourceType.PDF,
        ".docx": SourceType.DOCX,
        ".xlsx": SourceType.XLSX,
        ".html": SourceType.HTML,
        ".htm": SourceType.HTML,
        ".txt": SourceType.TXT,
    }

    _CATEGORY_BY_DIRECTORY: dict[str, SourceCategory] = {
        "business": SourceCategory.BUSINESS,
        "company_docs": SourceCategory.COMPANY_DOCUMENT,
        "company-docs": SourceCategory.COMPANY_DOCUMENT,
        "financials": SourceCategory.FINANCIAL,
        "financial": SourceCategory.FINANCIAL,
        "legal": SourceCategory.LEGAL,
        "web": SourceCategory.WEB,
    }

    def __init__(
        self,
        processor_factory=None,
    ) -> None:
        self._processor_factory = (
            processor_factory
            or create_processor_factory()
        )

    def discover(
        self,
        startup_id: str,
        source_root: Path,
    ) -> list[SourceDocument]:
        """
        Discover supported source files.

        Args:
            startup_id:
                Startup identifier, e.g. "restomart".

            source_root:
                Root directory containing startup sources.

        Returns:
            Deterministically ordered list of SourceDocument records.
        """

        if not startup_id or not startup_id.strip():
            raise ValueError(
                "startup_id must not be empty."
            )

        source_root = source_root.resolve()

        if not source_root.exists():
            raise SourceDiscoveryError(
                f"Source root does not exist: {source_root}"
            )

        if not source_root.is_dir():
            raise SourceDiscoveryError(
                f"Source root is not a directory: {source_root}"
            )

        discovered: list[SourceDocument] = []

        for path in sorted(
            source_root.rglob("*"),
            key=lambda item: item.as_posix().lower(),
        ):
            if not path.is_file():
                continue

            source_type = self._source_type_for(path)

            if source_type is None:
                continue

            relative_path = path.relative_to(
                source_root
            ).as_posix()

            mime_type = (
                self._mime_type_for(
                    path,
                    source_type,
                )
            )

            source_category = (
                self._category_for(
                    path,
                    source_root,
                )
            )

            discovered.append(
                SourceDocument(
                    source_id=uuid5( NAMESPACE_URL, f"investment-os:{startup_id}:{relative_path}",),
                    startup_id=startup_id.strip(),
                    relative_path=relative_path,
                    filename=path.name,
                    source_type=source_type,
                    source_category=source_category,
                    source_authority=SourceAuthority.UNKNOWN,
                    mime_type=mime_type,
                    title=path.stem,
                    file_size_bytes=path.stat().st_size,
                    sha256=self._sha256(path),
                    extraction_status=(
                        ExtractionStatus.DISCOVERED
                    ),
                )
            )

        return discovered

    @classmethod
    def _source_type_for(
        cls,
        path: Path,
    ) -> SourceType | None:
        return cls._EXTENSION_TO_SOURCE_TYPE.get(
            path.suffix.lower()
        )

    @staticmethod
    def _mime_type_for(
        path: Path,
        source_type: SourceType,
    ) -> str:
        """
        Determine MIME type.

        Uses mimetypes first, then deterministic fallbacks.
        """

        guessed, _ = mimetypes.guess_type(
            path.name
        )

        if guessed:
            return guessed

        fallback = {
            SourceType.PDF: "application/pdf",
            SourceType.DOCX: (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            SourceType.XLSX: (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            SourceType.HTML: "text/html",
            SourceType.TXT: "text/plain",
        }

        return fallback.get(
            source_type,
            "application/octet-stream",
        )

    @classmethod
    def _category_for(
        cls,
        path: Path,
        source_root: Path,
    ) -> SourceCategory:
        """
        Determine source category from the most specific recognized
        directory in the relative path.
        """
    
        relative = path.relative_to(source_root)
    
        directories = [
            part.lower()
            for part in relative.parts[:-1]
        ]
    
        # Most specific recognized directory wins.
        for directory in reversed(directories):
            category = cls._CATEGORY_BY_DIRECTORY.get(
                directory
            )
    
            if category is not None:
                return category
    
        return SourceCategory.OTHER

    @staticmethod
    def _sha256(
        path: Path,
        chunk_size: int = 1024 * 1024,
    ) -> str:
        """
        Calculate SHA256 without loading the entire file into memory.
        """

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()
