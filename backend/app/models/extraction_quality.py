"""
Extraction quality model.

Defines the quality classification of extracted document content.

This model belongs to the model layer so that services and persistence
models can depend on it without introducing model -> service dependencies.
"""

from enum import Enum


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
