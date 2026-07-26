"""
Document ORM model.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    DocumentStatus,
    DocumentType,
)
from app.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.startup import Startup


class Document(
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    """
    Startup document metadata.
    """

    __tablename__ = "documents"

    #
    # Relationship
    #
    startup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #
    # Document Information
    #
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    #
    # File Information
    #
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    #
    # Processing
    #
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    #
    # Relationships
    #
    startup: Mapped[Startup] = relationship(
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return (
            f"Document("
            f"id={self.id}, "
            f"type='{self.document_type.value}', "
            f"filename='{self.filename}')"
        )
