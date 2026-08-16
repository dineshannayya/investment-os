from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class StartupAnalysisMode(str, enum.Enum):
    """Generation mode used for startup analysis."""

    STANDARD = "standard"
    DEEP = "deep"


class StartupAnalysisStatus(str, enum.Enum):
    """Lifecycle status of a startup analysis."""

    COMPLETED = "completed"
    FAILED = "failed"


class StartupAnalysis(Base, UUIDMixin, TimestampMixin):
    """
    Persisted startup-analysis execution.

    Each record represents one analysis run and should be treated
    as an immutable historical snapshot after completion.
    """

    __tablename__ = "startup_analyses"
    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    def __init__(self, **kwargs):
        kwargs.setdefault("mode", StartupAnalysisMode.STANDARD)
        kwargs.setdefault("status", StartupAnalysisStatus.COMPLETED)
        kwargs.setdefault("analysis_version", "3.7.5")
        kwargs.setdefault("thinking_enabled", False)
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    startup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("startups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    startup = relationship(
        "Startup",
        back_populates="analyses",
    )

    # ------------------------------------------------------------------
    # Analysis configuration
    # ------------------------------------------------------------------

    mode: Mapped[StartupAnalysisMode] = mapped_column(
        nullable=False,
        default=StartupAnalysisMode.STANDARD,
    )

    status: Mapped[StartupAnalysisStatus] = mapped_column(
        nullable=False,
        default=StartupAnalysisStatus.COMPLETED,
    )

    analysis_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="3.7.5",
    )

    # ------------------------------------------------------------------
    # LLM configuration / execution metadata
    # ------------------------------------------------------------------

    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    thinking_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    max_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    finish_reason: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Usage / performance
    # ------------------------------------------------------------------

    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    completion_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    inference_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Investment conclusion
    # ------------------------------------------------------------------

    recommendation: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    investment_thesis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    input_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    metrics_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    result_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Error information
    # ------------------------------------------------------------------

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    json_serializer=lambda obj: float(obj)


    __table_args__ = (
        Index(
            "ix_startup_analyses_startup_created",
            "startup_id",
            "created_at",
        ),
    )
