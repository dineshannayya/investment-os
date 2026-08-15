"""
Document processing service.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.chunking.base import Chunk, Chunker
from app.models.document import Document
from app.processors.base import DocumentContent
from app.processors.factory import ProcessorFactory
from app.services.document import DocumentService
from app.storage.service import StorageService


class DocumentProcessingService:
    """
    Service responsible for processing stored documents.

    Responsibilities:
      * Retrieve document metadata
      * Resolve storage path
      * Select appropriate processor
      * Produce normalized DocumentContent
    """

    def __init__(
        self,
        *,
        documents: DocumentService,
        storage: StorageService,
        processors: ProcessorFactory,
        chunker: Chunker,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._processors = processors
        self._chunker = chunker

    # ------------------------------------
    # properties
    # -----------------------------------
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


    # -----------------------------
    # public methods
    # ----------------------------
    def chunk_document(
        self,
        document_id: UUID,
    ) -> list[Chunk]:
        """
        Process and chunk a document.
        """
    
        content = self.process_document(document_id)
    
        return self._chunker.chunk(content)
    
    def process_and_chunk(
        self,
        document_id: UUID,
    ) -> tuple[DocumentContent, list[Chunk]]:
    
        content = self.process_document(document_id)
        
        chunks = self._chunker.chunk(content)
        
        return content, chunks

    def process_document(
        self,
        document_id: UUID,
    ) -> DocumentContent:
        """
        Process a stored document.

        Raises:
            ValueError:
                If the document cannot be found.

            FileNotFoundError:
                If the stored file does not exist.
        """

        document = self._get_document(document_id)

        path = self._resolve_path(document)

        processor = self._processors.get_processor(
            path=path,
            mime_type=document.mime_type,
        )

        return processor.process(
            document_id=document.id,
            path=path,
        )


    
    # -------------------------------------
    # private helpers
    # -------------------------------------

    def _get_document(
        self,
        document_id: UUID,
    ) -> Document:
        """
        Retrieve document metadata.
        """

        document = self._documents.get_document(document_id)

        if document is None:
            raise ValueError(
                f"Document '{document_id}' not found."
            )

        return document

    def _resolve_path(
        self,
        document: Document,
    ) -> Path:
        """
        Resolve storage path.
        """

        path = self._storage.resolve(document.storage_path)

        if not path.exists():
            raise FileNotFoundError(path)

        return path
