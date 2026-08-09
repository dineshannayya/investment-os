"""
Document processor factory.
"""

from __future__ import annotations

from pathlib import Path

from app.processors.base import DocumentProcessor
from app.processors.docx import DocxProcessor
from app.processors.pdf import PdfProcessor
from app.processors.text import TextProcessor


class ProcessorFactory:
    """
    Factory for resolving document processors.
    """

    def __init__(self) -> None:
        self._processors: list[DocumentProcessor] = []

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(
        self,
        processor: DocumentProcessor,
    ) -> None:
        """
        Register a document processor.
        """

        if processor in self._processors:
            return

        self._processors.append(processor)

        return self

    def clear(self) -> None:
        """
        Remove all registered processors.
        """
    
        self._processors.clear()


    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get_processor(
        self,
        path: Path,
        mime_type: str,
    ) -> DocumentProcessor:
        """
        Return a processor supporting the document.

        Raises:
            ValueError:
                If no processor supports the supplied file.
        """

        for processor in self._processors:
            if processor.supports(path, mime_type):
                return processor

        raise ValueError(
            f"No processor registered for MIME type "
            f"'{mime_type}' and extension '{path.suffix}'."
        )

    def supports(
        self,
        path: Path,
        mime_type: str,
    ) -> bool:
        """
        Return True if any processor supports the document.
        """

        return any(
            processor.supports(path, mime_type)
            for processor in self._processors
        )

    @property
    def processors(self) -> tuple[DocumentProcessor, ...]:
        """
        Return registered processors.
        """

        return tuple(self._processors)

# --------------------------------------------
#
# --------------------------------------------
def create_processor_factory() -> ProcessorFactory:
    """
    Create a factory with all built-in processors registered.
    """

    factory = ProcessorFactory()

    # Registration will be added as processors are implemented.
    factory.register(TextProcessor())
    factory.register(PdfProcessor())
    factory.register(DocxProcessor())

    return factory

