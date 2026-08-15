"""
Base document processor interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

# ============================================================================
# Processor Result
# ============================================================================


@dataclass(slots=True)
class DocumentContent:
    """
    Normalized document extracted from any file type.
    """

    document_id: UUID

    text: str

    title: str | None = None

    page_count: int = 1

    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Processor Interface
# ============================================================================


class DocumentProcessor(ABC):
    """
    Base class for document processors.
    """

    @property
    @abstractmethod
    def supported_mime_types(self) -> set[str]:
        """
        MIME types supported by this processor.
        """

    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """
        File extensions supported.
        """

    def supports(
        self,
        path: Path,
        mime_type: str,
    ) -> bool:
        """
        Return True if this processor supports the document.
        """

        if mime_type in self.supported_mime_types:
            return True

        return path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        """
        Extract structured content from a document.
        """
