"""
Mapper between SourceExtractionRecord and SourceExtractionORM.

The mapper contains no database/session logic.

Responsibilities:
    Domain/Pydantic model
        ->
    SQLAlchemy ORM entity

and:

    SQLAlchemy ORM entity
        ->
    Domain/Pydantic model
"""

from __future__ import annotations

from app.models.source_extraction_orm import SourceExtractionORM
from app.models.source_extraction_record import (
    ExtractionProvenance,
    SourceExtractionRecord,
)


class SourceExtractionMapper:
    """
    Convert between SourceExtractionRecord and SourceExtractionORM.
    """

    @staticmethod
    def to_orm(
        record: SourceExtractionRecord,
    ) -> SourceExtractionORM:
        """
        Convert a domain/persistence contract into a SQLAlchemy entity.
        """

        return SourceExtractionORM(
            id=record.extraction_id,
            source_id=record.source_id,
            source_sha256=record.source_sha256,

            status=record.status.value,

            extraction_method=record.provenance.method.value,
            processor_name=record.provenance.processor_name,

            title=record.title,
            page_count=record.page_count,

            text=record.text,
            segments=record.segments,

            quality=record.quality.value,
            quality_warnings=record.quality_warnings,

            fallback_used=record.provenance.fallback_used,
            fallback_reason=record.provenance.fallback_reason,

            extraction_config=record.provenance.configuration,

            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def from_orm(
        entity: SourceExtractionORM,
    ) -> SourceExtractionRecord:
        """
        Convert a SQLAlchemy entity into a SourceExtractionRecord.
        """

        return SourceExtractionRecord(
            extraction_id=entity.id,

            source_id=entity.source_id,
            source_sha256=entity.source_sha256,

            status=entity.status,

            title=entity.title,
            page_count=entity.page_count,

            text=entity.text,
            segments=entity.segments,

            quality=entity.quality,
            quality_warnings=entity.quality_warnings,

            provenance=ExtractionProvenance(
                method=entity.extraction_method,
                processor_name=entity.processor_name,
                fallback_used=entity.fallback_used,
                fallback_reason=entity.fallback_reason,
                configuration=entity.extraction_config,
            ),

            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
