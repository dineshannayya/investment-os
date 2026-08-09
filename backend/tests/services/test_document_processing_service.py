"""
Tests for DocumentProcessingService.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.models.document import Document
from app.processors.base import (
    DocumentContent,
    DocumentProcessor,
)
from app.processors.factory import ProcessorFactory
from app.services.document_processing import (
    DocumentProcessingService,
)

from app.chunking.base import Chunk, Chunker

# ============================================================================
# Test Doubles
# ============================================================================

class FakeChunker(Chunker):
    """Fake chunker."""

    @property
    def name(self) -> str:
        return "fake"

    def chunk(self, document):
        return [
            Chunk(
                index=0,
                text=document.text,
                start_offset=0,
                end_offset=len(document.text),
                metadata={},
            )
        ]


class FakeDocumentService:
    """Fake document service."""

    def __init__(self, document: Document | None) -> None:
        self._document = document

    def get_document(self, document_id):
        return self._document


class FakeStorageService:
    """Fake storage service."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def resolve(self, storage_path: str) -> Path:
        return self._path


class FakeProcessor(DocumentProcessor):
    """Fake processor."""

    @property
    def supported_mime_types(self) -> set[str]:
        return {"text/plain"}

    @property
    def supported_extensions(self) -> set[str]:
        return {".txt"}

    def process(
        self,
        document_id,
        path,
    ) -> DocumentContent:
        return DocumentContent(
            document_id=document_id,
            title="Test",
            text="Investment OS",
            page_count=1,
            metadata={},
        )


# ============================================================================
# Tests
# ============================================================================


class TestDocumentProcessingService:
    """Tests for DocumentProcessingService."""

    @staticmethod
    def create_factory() -> ProcessorFactory:
        factory = ProcessorFactory()
        factory.register(FakeProcessor())
        return factory

    def test_process_document(
        self,
        tmp_path,
        document_factory,
    ):
        """
        Process a stored document.
        """

        path = tmp_path / "sample.txt"
        path.write_text("Hello")

        document = document_factory(
            storage_path="sample.txt",
            mime_type="text/plain",
        )

        service = DocumentProcessingService(
            documents=FakeDocumentService(document),
            storage=FakeStorageService(path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        result = service.process_document(
            document.id,
        )

        assert isinstance(
            result,
            DocumentContent,
        )

        assert result.document_id == document.id
        assert result.text == "Investment OS"
        assert result.title == "Test"

    def test_document_not_found(
        self,
        tmp_path,
    ):
        """
        Missing document raises ValueError.
        """

        service = DocumentProcessingService(
            documents=FakeDocumentService(None),
            storage=FakeStorageService(tmp_path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        with pytest.raises(
            ValueError,
            match="not found",
        ):
            service.process_document(
                uuid4(),
            )

    def test_file_not_found(
        self,
        tmp_path,
        document_factory,
    ):
        """
        Missing file raises FileNotFoundError.
        """

        missing = tmp_path / "missing.txt"

        document = document_factory(
            storage_path="missing.txt",
            mime_type="text/plain",
        )

        service = DocumentProcessingService(
            documents=FakeDocumentService(document),
            storage=FakeStorageService(missing),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        with pytest.raises(
            FileNotFoundError,
        ):
            service.process_document(
                document.id,
            )

    def test_unsupported_document(
        self,
        tmp_path,
        document_factory,
    ):
        """
        Unsupported document raises ValueError.
        """

        path = tmp_path / "sample.xyz"
        path.write_text("Hello")

        document = document_factory(
            storage_path="sample.xyz",
            mime_type="application/x-test",
        )

        service = DocumentProcessingService(
            documents=FakeDocumentService(document),
            storage=FakeStorageService(path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        with pytest.raises(
            ValueError,
            match="No processor",
        ):
            service.process_document(
                document.id,
            )

    def test_processor_factory_property(
        self,
        tmp_path,
    ):
        """
        Factory property is exposed.
        """

        factory = self.create_factory()

        service = DocumentProcessingService(
            documents=FakeDocumentService(None),
            storage=FakeStorageService(tmp_path),
            processors=factory,
            chunker=FakeChunker(),
        )

        assert service.processor_factory is factory

    def test_storage_service_property(
        self,
        tmp_path,
    ):
        """
        Storage service property is exposed.
        """

        storage = FakeStorageService(tmp_path)

        service = DocumentProcessingService(
            documents=FakeDocumentService(None),
            storage=storage,
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        assert service.storage_service is storage

    def test_document_service_property(
        self,
        tmp_path,
    ):
        """
        Document service property is exposed.
        """

        documents = FakeDocumentService(None)

        service = DocumentProcessingService(
            documents=documents,
            storage=FakeStorageService(tmp_path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )

        assert service.document_service is documents


    def test_chunker_property(self, tmp_path):
        chunker = FakeChunker()
    
        service = DocumentProcessingService(
            documents=FakeDocumentService(None),
            storage=FakeStorageService(tmp_path),
            processors=self.create_factory(),
            chunker=chunker,
        )
    
        assert service.chunker is chunker
    
    def test_chunk_document(
        self,
        tmp_path,
        document_factory,
    ):
        path = tmp_path / "sample.txt"
        path.write_text("Hello")
    
        document = document_factory(
            storage_path="sample.txt",
            mime_type="text/plain",
        )
    
        service = DocumentProcessingService(
            documents=FakeDocumentService(document),
            storage=FakeStorageService(path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )
    
        chunks = service.chunk_document(document.id)
    
        assert len(chunks) == 1
        assert chunks[0].text == "Investment OS"
    
    def test_process_and_chunk(
        self,
        tmp_path,
        document_factory,
    ):
        path = tmp_path / "sample.txt"
        path.write_text("Hello")
    
        document = document_factory(
            storage_path="sample.txt",
            mime_type="text/plain",
        )
    
        service = DocumentProcessingService(
            documents=FakeDocumentService(document),
            storage=FakeStorageService(path),
            processors=self.create_factory(),
            chunker=FakeChunker(),
        )
    
        content, chunks = service.process_and_chunk(document.id)
    
        assert content.text == "Investment OS"
        assert len(chunks) == 1
    
