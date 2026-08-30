from datetime import datetime, timezone
from uuid import uuid4

from app.models.extraction_quality import ExtractionQuality
from app.models.source_document import ExtractionStatus
from app.models.source_extraction_record import (
    ExtractionMethod,
    ExtractionProvenance,
    SourceExtractionRecord,
)
from app.services.source_extraction_document import (
    SourceExtractionDocumentAdapter,
)


def _record() -> SourceExtractionRecord:
    source_id = uuid4()
    now = datetime.now(timezone.utc)

    return SourceExtractionRecord(
        extraction_id=uuid4(),
        source_id=source_id,
        source_sha256="a" * 64,
        status=ExtractionStatus.EXTRACTED,
        title="PAN",
        page_count=1,
        text="PAN document extracted text.",
        segments=[
            {
                "index": 0,
                "text": "PAN document extracted text.",
                "start_offset": 0,
                "end_offset": 29,
                "metadata": {
                    "page": 1,
                },
            },
        ],
        quality=ExtractionQuality.PASS,
        quality_warnings=[],
        provenance=ExtractionProvenance(
            method=ExtractionMethod.OCR,
            processor_name="tesseract",
            fallback_used=True,
            fallback_reason="native_extraction_empty",
            configuration={
                "ocr_engine": "tesseract",
                "ocr_dpi": 100,
                "ocr_workers": 4,
                "ocr_language": "eng",
                "ocr_timeout_seconds": 120,
            },
        ),
        created_at=now,
        updated_at=now,
    )


def test_to_document_content_reconstructs_extraction() -> None:
    record = _record()

    content = (
        SourceExtractionDocumentAdapter.to_document_content(
            record,
        )
    )

    assert content.document_id == record.source_id
    assert content.text == record.text
    assert content.title == "PAN"
    assert content.page_count == 1

    assert len(content.segments) == 1

    segment = content.segments[0]

    assert segment.index == 0
    assert segment.text == record.segments[0]["text"]
    assert segment.start_offset == 0
    assert segment.end_offset == 29
    assert segment.metadata == {"page": 1}


def test_to_document_content_preserves_provenance_metadata() -> None:
    record = _record()

    content = (
        SourceExtractionDocumentAdapter.to_document_content(
            record,
        )
    )

    assert content.metadata["source_id"] == str(
        record.source_id,
    )

    assert content.metadata["source_sha256"] == (
        record.source_sha256
    )

    assert content.metadata["extraction_id"] == str(
        record.extraction_id,
    )

    assert content.metadata["extraction_method"] == "ocr"
    assert content.metadata["processor_name"] == "tesseract"
    assert content.metadata["fallback_used"] is True
    assert content.metadata["fallback_reason"] == (
        "native_extraction_empty"
    )

    assert content.metadata["extraction_config"] == (
        record.provenance.configuration
    )


def test_to_document_content_can_preserve_document_identity() -> None:
    record = _record()
    document_id = uuid4()

    content = (
        SourceExtractionDocumentAdapter.to_document_content(
            record,
            document_id=document_id,
        )
    )

    assert content.document_id == document_id
    assert content.document_id != record.source_id
