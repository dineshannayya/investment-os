"""
Source extraction persistence service.

Persists SourceExtractionRecord domain objects into the
source_extractions database table.

Responsibilities:
    - Map domain records to ORM entities.
    - Create new extraction records.
    - Refresh existing source-version records.
    - Read persisted extraction records.
    - Own transaction boundaries.

Non-responsibilities:
    - File discovery.
    - Native extraction.
    - OCR execution.
    - Extraction quality assessment.
    - Source-version calculation.
    - Extraction orchestration.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mappers.source_extraction import SourceExtractionMapper
from app.models.source_extraction_orm import SourceExtractionORM
from app.models.source_extraction_record import SourceExtractionRecord
from app.repositories.source_extraction import SourceExtractionRepository


class SourceExtractionPersistenceService:
    """Persist source extraction records."""

    def __init__(
        self,
        *,
        session: Session,
        repository: SourceExtractionRepository | None = None,
    ) -> None:
        self._session = session

        self._repository = (
            repository
            or SourceExtractionRepository(session)
        )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        extraction_id: UUID,
    ) -> SourceExtractionRecord | None:
        """Return an extraction by ID."""

        entity = self._repository.get_by_id(
            extraction_id,
        )

        if entity is None:
            return None

        return SourceExtractionMapper.from_orm(entity)

    def get_by_source_version(
        self,
        source_id: UUID,
        source_sha256: str,
    ) -> SourceExtractionRecord | None:
        """
        Return the persisted extraction for an exact source version.

        Source identity is:

            source_id + source_sha256
        """

        entity = self._repository.get_by_source_version(
            source_id=source_id,
            source_sha256=source_sha256,
        )

        if entity is None:
            return None

        return SourceExtractionMapper.from_orm(entity)

    def get_latest_by_source_id(
        self,
        source_id: UUID,
    ) -> SourceExtractionRecord | None:
        """Return the newest extraction for a source."""
    
        entity = self._repository.get_latest_by_source_id(
            source_id,
        )
    
        if entity is None:
            return None
    
        return SourceExtractionMapper.from_orm(entity)


    def get_latest_by_source_sha256(
        self,
        source_sha256: str,
    ) -> SourceExtractionRecord | None:
        """
        Return the newest persisted extraction for an exact source SHA256.

        This lookup allows document processing to reuse the canonical
        extraction artifact using the document's content hash alone.
        """

        entity = self._repository.get_latest_by_source_sha256(
            source_sha256,
        )

        if entity is None:
            return None

        return SourceExtractionMapper.from_orm(entity)

    def list_by_source(
        self,
        source_id: UUID,
    ) -> list[SourceExtractionRecord]:
        """Return extraction history for a source."""

        entities = self._repository.list_by_source(
            source_id,
        )

        return [
            SourceExtractionMapper.from_orm(entity)
            for entity in entities
        ]

    def list_by_source_ids(
        self,
        source_ids: Iterable[UUID],
    ) -> list[SourceExtractionRecord]:
        """
        Return the latest persisted extraction for each supplied source ID.

        The caller is responsible for determining which SourceDocument
        objects belong to a startup.

        This service only performs persistence-layer lookup.

        Results are returned deterministically by source ID.
        """

        normalized_ids = tuple(
            dict.fromkeys(source_ids)
        )

        if not normalized_ids:
            return []

        records: list[SourceExtractionRecord] = []

        for source_id in normalized_ids:
            entity = self._repository.get_latest_by_source_id(
                source_id,
            )

            if entity is None:
                continue

            records.append(
                SourceExtractionMapper.from_orm(entity)
            )

        records.sort(
            key=lambda record: str(record.source_id),
        )

        return records

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def persist(
        self,
        record: SourceExtractionRecord,
    ) -> SourceExtractionRecord:
        """
        Persist a new extraction record.

        This method is create-only.

        Existing source versions should use refresh().
        """

        try:
            existing = self._repository.get_by_source_version(
                source_id=record.source_id,
                source_sha256=record.source_sha256,
            )

            if existing is not None:
                raise ValueError(
                    "Source extraction already exists for "
                    f"source_id={record.source_id} "
                    f"source_sha256={record.source_sha256}"
                )

            entity = SourceExtractionMapper.to_orm(
                record,
            )

            entity = self._repository.create(
                entity,
            )

            self._session.commit()

            return SourceExtractionMapper.from_orm(
                entity,
            )

        except Exception:
            self._session.rollback()
            raise

    # -------------------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------------------

    def refresh(
        self,
        record: SourceExtractionRecord,
    ) -> SourceExtractionRecord:
        """
        Refresh an existing extraction for the same source version.

        Source version:

            source_id + source_sha256

        Existing database identity is preserved:

            id
            created_at

        Refreshed fields include:

            status
            extraction method
            processor
            title
            page count
            text
            segments
            quality
            quality warnings
            fallback information
            extraction configuration
            updated_at

        If no existing record is found, a new record is created.
        """

        try:
            existing = self._repository.get_by_source_version(
                source_id=record.source_id,
                source_sha256=record.source_sha256,
            )

            # -------------------------------------------------------------
            # No existing record
            # -------------------------------------------------------------

            if existing is None:
                entity = SourceExtractionMapper.to_orm(
                    record,
                )

                entity = self._repository.create(
                    entity,
                )

            # -------------------------------------------------------------
            # Existing record
            # -------------------------------------------------------------

            else:
                replacement = SourceExtractionMapper.to_orm(
                    record,
                )

                # Refresh modification timestamp.
                existing.updated_at = datetime.now(
                    timezone.utc,
                )

                self._copy_refresh_fields(
                    existing=existing,
                    replacement=replacement,
                )

                entity = self._repository.update(
                    existing,
                )

            self._session.commit()

            return SourceExtractionMapper.from_orm(
                entity,
            )

        except Exception:
            self._session.rollback()
            raise

    # -------------------------------------------------------------------------
    # Refresh helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _copy_refresh_fields(
        *,
        existing: SourceExtractionORM,
        replacement: SourceExtractionORM,
    ) -> None:
        """
        Copy refreshed extraction data onto an existing ORM entity.

        The ORM identity and creation timestamp are intentionally
        not copied.
        """

        existing.source_id = replacement.source_id
        existing.source_sha256 = replacement.source_sha256

        existing.status = replacement.status

        existing.extraction_method = (
            replacement.extraction_method
        )

        existing.processor_name = (
            replacement.processor_name
        )

        existing.title = replacement.title
        existing.page_count = replacement.page_count

        existing.text = replacement.text
        existing.segments = replacement.segments

        existing.quality = replacement.quality

        existing.quality_warnings = (
            replacement.quality_warnings
        )

        existing.fallback_used = (
            replacement.fallback_used
        )

        existing.fallback_reason = (
            replacement.fallback_reason
        )

        existing.extraction_config = (
            replacement.extraction_config
        )

        existing.updated_at = replacement.updated_at
