from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ExtractionQuality(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"


class ExtractionQualityReport(BaseModel):
    """
    Read-only quality assessment of extracted source content.

    This model does not represent extraction execution status.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str
    relative_path: str
    source_type: str
    source_category: str

    quality: ExtractionQuality

    text_length: int = Field(ge=0)
    segment_count: int = Field(ge=0)

    processor_name: str | None = None

    warnings: list[str] = Field(default_factory=list)
