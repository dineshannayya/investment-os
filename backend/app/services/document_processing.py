"""
Document processing service.

Provides the downstream DocumentContent contract.

Processing strategy:

    Document
        |
        v
    persisted SourceExtractionRecord?
        |
        +---- YES ----> SourceExtractionDocumentAdapter
        |                    |
        |                    v
        |              DocumentContent
        |
        +---- NO -----> filesystem processor
                             |
                             v
                       DocumentContent

The persisted source extraction is preferred because it is the
canonical extraction artifact.

The filesystem processor remains a compatibility fallback for
documents that do not yet have a persisted source extraction.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.adapters.source_extraction_document import (
    SourceExtractionDocumentAdapter,
)
from app.chunking.base import Chunk, Chunker
from app.models.document import Document
from app.models.source_extraction_record import (
    SourceExtractionRecord,
)
from app.processors.base import DocumentContent
from app.processors.factory import ProcessorFactory
from app.services.document import DocumentService
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)
from app.storage.service import StorageService


class DocumentProcessingService:
    """
    Service responsible for producing normalized DocumentContent.

    Preferred production path:

        persisted source extraction
            ->
        SourceExtractionDocumentAdapter
            ->
        DocumentContent

    Compatibility path:

        stored document
            ->
        filesystem
            ->
        ProcessorFactory
            ->
        DocumentContent
    """

    def __init__(
        self,
        *,
        documents: DocumentService,
        storage: StorageService,
        processors: ProcessorFactory,
        chunker: Chunker,
        source_extractions: (
            SourceExtractionPersistenceService | None
        ) = None,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._processors = processors
        self._chunker = chunker

        self._source_extractions = source_extractions

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def document_service(self) -> DocumentService:
        return self._documents

    @property
    def storage_service(self) -> StorageService:
        return self._storage

    @property
    def processor_factory(self) -> ProcessorFactory:
        return self._processors

    @property
    def chunker(self) -> Chunker:
        return self._chunker

    @property
    def source_extraction_persistence(
        self,
    ) -> SourceExtractionPersistenceService | None:
        return self._source_extractions

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        document_id: UUID,
    ) -> list[Chunk]:
        """
        Process and chunk a document.
        """

        content = self.process_document(
            document_id,
        )

        return self._chunker.chunk(
            content,
        )

    def chunk_content(
        self,
        content: DocumentContent,
    ) -> list[Chunk]:
        """
        Chunk already-normalized DocumentContent.
    
        This is used when the canonical DocumentContent is already
        available, for example from a persisted SourceExtractionRecord.
    
        Unlike chunk_document(), this method does not perform a
        Document-table lookup or filesystem processing.
        """
    
        return self._chunker.chunk(
            content,
        )

    def process_and_chunk(
        self,
        document_id: UUID,
    ) -> tuple[DocumentContent, list[Chunk]]:
        """
        Process a document and produce chunks.
        """

        content = self.process_document(
            document_id,
        )

        chunks = self._chunker.chunk(
            content,
        )

        return content, chunks

    def process_document(
        self,
        document_id: UUID,
    ) -> DocumentContent:
        """
        Produce DocumentContent for a stored document.

        Production priority:

            1. persisted source extraction
            2. filesystem processor fallback

        Raises:

            ValueError:
                If the document cannot be found.

            FileNotFoundError:
                If the filesystem fallback is required but the
                stored file does not exist.
        """

        document = self._get_document(
            document_id,
        )

        # --------------------------------------------------------------
        # 1. Preferred production path:
        #    persisted source extraction
        # --------------------------------------------------------------

        extraction = self._get_persisted_extraction(
            document,
        )

        if extraction is not None:
            return SourceExtractionDocumentAdapter.to_document_content(
                extraction,
                document_id=document.id,
            )

        # --------------------------------------------------------------
        # 2. Compatibility fallback:
        #    process the stored file directly
        # --------------------------------------------------------------

        return self._process_from_storage(
            document,
        )

    # ------------------------------------------------------------------
    # Persisted extraction
    # ------------------------------------------------------------------

    def _get_persisted_extraction(
        self,
        document: Document,
    ) -> SourceExtractionRecord | None:
        """
        Look up the canonical persisted extraction for this document.

        The document's file_hash represents the SHA256 of the exact
        stored source bytes.

        SourceExtractionRecord is versioned using source_id +
        source_sha256. The persistence service therefore provides the
        SHA256 lookup boundary.

        If source extraction persistence is not configured, return None
        and use the existing processor path.
        """

        if self._source_extractions is None:
            return None

        file_hash = (
            document.file_hash
            if document.file_hash
            else None
        )

        if not file_hash:
            return None

        return (
            self._source_extractions
            .get_latest_by_source_sha256(
                file_hash,
            )
        )

    # ------------------------------------------------------------------
    # Filesystem processing
    # ------------------------------------------------------------------

    def _process_from_storage(
        self,
        document: Document,
    ) -> DocumentContent:
        """
        Process the stored document using the existing processor flow.
        """

        path = self._resolve_path(
            document,
        )

        processor = self._processors.get_processor(
            path=path,
            mime_type=document.mime_type,
        )

        return processor.process(
            document_id=document.id,
            path=path,
        )

    # ------------------------------------------------------------------
    # Document lookup
    # ------------------------------------------------------------------

    def _get_document(
        self,
        document_id: UUID,
    ) -> Document:
        """
        Retrieve document metadata.
        """

        document = self._documents.get_document(
            document_id,
        )

        if document is None:
            raise ValueError(
                f"Document '{document_id}' not found."
            )

        return document

    # ------------------------------------------------------------------
    # Storage path
    # ------------------------------------------------------------------

    def _resolve_path(
        self,
        document: Document,
    ) -> Path:
        """
        Resolve the stored document path.
        """

        path = self._storage.resolve(
            document.storage_path,
        )

        if not path.exists():
            raise FileNotFoundError(
                path,
            )

        return path
