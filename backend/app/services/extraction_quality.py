from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.source_document import SourceDocument


class ExtractionQuality(str, Enum):
    """
    Quality classification of extracted document content.

    This is intentionally separate from ExtractionStatus.

    ExtractionStatus answers:
        "Did extraction execute?"

    ExtractionQuality answers:
        "Is the extracted result sufficiently usable?"
    """

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


class ExtractionQualityService:
    """
    Read-only quality assessment for extracted DocumentContent.

    Responsibilities:
        - inspect extracted content
        - detect obviously suspicious extraction results
        - classify the result as PASS / REVIEW / FAIL
        - produce an ExtractionQualityReport

    Non-responsibilities:
        - modifying SourceDocument
        - modifying DocumentContent
        - modifying source files
        - OCR
        - LLM processing
        - investment interpretation
        - evidence generation
        - persistence
    """

    def assess(
        self,
        source: SourceDocument,
        content,
        processor_name: str | None = None,
    ) -> ExtractionQualityReport:
        """
        Assess the quality of extracted content.

        The method is strictly read-only.
        """

        text = content.text or ""
        segments = content.segments or []

        text_length = len(text)
        segment_count = len(segments)

        warnings: list[str] = []

        # ---------------------------------------------------------
        # 1. Completely empty extraction
        # ---------------------------------------------------------

        if text_length == 0:
            warnings.append(
                "extracted_text_empty"
            )

        # ---------------------------------------------------------
        # 2. No structural segments
        # ---------------------------------------------------------

        if segment_count == 0:
            warnings.append(
                "no_segments_extracted"
            )

        # ---------------------------------------------------------
        # 3. Suspiciously short PDF extraction
        #
        # Do not automatically assume that every short PDF is
        # invalid. Some certificates are legitimately small.
        # Therefore classify this as REVIEW rather than FAIL.
        # ---------------------------------------------------------

        if (
            source.source_type.value == "pdf"
            and 0 < text_length < 100
        ):
            warnings.append(
                "pdf_text_suspiciously_short"
            )

        # ---------------------------------------------------------
        # 4. Financial PDF extraction
        #
        # Financial reports should normally contain substantial
        # textual content. A very small result is suspicious and
        # requires inspection/OCR consideration.
        # ---------------------------------------------------------

        if (
            source.source_type.value == "pdf"
            and source.source_category.value == "financial"
            and text_length < 1000
        ):
            warnings.append(
                "financial_pdf_text_suspiciously_short"
            )

        # ---------------------------------------------------------
        # 5. Determine overall quality
        # ---------------------------------------------------------

        if (
            "extracted_text_empty" in warnings
            or "no_segments_extracted" in warnings
        ):
            quality = ExtractionQuality.FAIL

        elif any(
            warning in warnings
            for warning in (
                "pdf_text_suspiciously_short",
                "financial_pdf_text_suspiciously_short",
            )
        ):
            quality = ExtractionQuality.REVIEW

        else:
            quality = ExtractionQuality.PASS

        return ExtractionQualityReport(
            source_id=str(source.source_id),
            relative_path=source.relative_path,
            source_type=source.source_type.value,
            source_category=source.source_category.value,
            quality=quality,
            text_length=text_length,
            segment_count=segment_count,
            processor_name=processor_name,
            warnings=warnings,
        )
