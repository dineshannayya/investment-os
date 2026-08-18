"""
Document processing framework.
"""

from app.processors.base import (
    DocumentSegment,   
    DocumentContent,
    DocumentProcessor,
)
from app.processors.docx import DocxProcessor
from app.processors.factory import (
    ProcessorFactory,
    create_processor_factory,
)
from app.processors.pdf import PdfProcessor
from app.processors.text import TextProcessor

__all__ = [
    "DocumentSegment",
    "DocumentContent",
    "DocumentProcessor",
    "ProcessorFactory",
    "create_processor_factory",
    "TextProcessor",
    "PdfProcessor",
    "DocxProcessor",
]
