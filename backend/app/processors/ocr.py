"""
OCR document processor.

This processor performs OCR on PDF pages and returns the same
DocumentContent abstraction used by the native document processors.

The processor intentionally does not:
    - interpret document content
    - extract investment evidence
    - calculate financial metrics
    - call an LLM
    - modify the original source document
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader

from app.processors.base import (
    DocumentContent,
    DocumentProcessor,
    DocumentSegment,
)


class OcrProcessor(DocumentProcessor):
    """
    OCR processor for image/scanned PDF documents.

    Rendering:
        pdftoppm

    OCR:
        tesseract

    The original PDF is never modified.
    """

    _SUPPORTED_MIME_TYPES = {
        "application/pdf",
    }

    _SUPPORTED_EXTENSIONS = {
        ".pdf",
    }

    def __init__(
        self,
        *,
        language: str = "eng",
        dpi: int = 200,
        timeout_seconds: int = 120,
    ) -> None:
        if dpi <= 0:
            raise ValueError("dpi must be greater than zero")

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        self._language = language
        self._dpi = dpi
        self._timeout_seconds = timeout_seconds

    # -------------------------------------------------------------------------
    # Processor contract
    # -------------------------------------------------------------------------

    @property
    def supported_mime_types(self) -> set[str]:
        """Return supported MIME types."""
        return self._SUPPORTED_MIME_TYPES

    @property
    def supported_extensions(self) -> set[str]:
        """Return supported file extensions."""
        return self._SUPPORTED_EXTENSIONS

    # -------------------------------------------------------------------------
    # Public processing
    # -------------------------------------------------------------------------

    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        """
        OCR a PDF document page-by-page.

        Each PDF page becomes one DocumentSegment.

        Raises:
            FileNotFoundError:
                If the source PDF does not exist.

            RuntimeError:
                If the required OCR executables are unavailable or
                rendering/OCR fails.
        """

        if not path.exists():
            raise FileNotFoundError(
                f"OCR source document does not exist: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"OCR source path is not a file: {path}"
            )

        self._require_command("pdftoppm")
        self._require_command("tesseract")

        reader = PdfReader(path)

        page_count = len(reader.pages)

        if page_count == 0:
            raise RuntimeError(
                f"PDF contains no pages: {path}"
            )

        title = self._extract_title(
            reader,
            path,
        )

        pages: list[str] = []

        with tempfile.TemporaryDirectory(
            prefix="investment-os-ocr-",
        ) as temp_dir:

            temp_root = Path(temp_dir)

            for page_number in range(
                1,
                page_count + 1,
            ):
                page_text = self._ocr_page(
                    path=path,
                    page_number=page_number,
                    output_dir=temp_root,
                )

                pages.append(page_text)

        text = "\n\n".join(pages)

        segments = self._build_segments(
            pages=pages,
        )

        metadata = self._build_metadata(
            path=path,
            page_count=page_count,
            reader=reader,
        )

        return DocumentContent(
            document_id=document_id,
            title=title,
            text=text,
            page_count=page_count,
            metadata=metadata,
            segments=tuple(segments),
        )

    # -------------------------------------------------------------------------
    # PDF/page processing
    # -------------------------------------------------------------------------

    def _ocr_page(
        self,
        *,
        path: Path,
        page_number: int,
        output_dir: Path,
    ) -> str:
        """
        Render one PDF page and OCR it.
        """

        image_prefix = (
            output_dir
            / f"page-{page_number:04d}"
        )

        render_command = [
            "pdftoppm",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-r",
            str(self._dpi),
            "-png",
            "-singlefile",
            str(path),
            str(image_prefix),
        ]

        self._run_command(
            render_command,
            operation=f"PDF rendering page {page_number}",
        )

        image_path = image_prefix.with_suffix(".png")

        if not image_path.exists():
            raise RuntimeError(
                "PDF renderer did not produce expected image "
                f"for page {page_number}: {image_path}"
            )

        ocr_command = [
            "tesseract",
            str(image_path),
            "stdout",
            "-l",
            self._language,
            "--psm",
            "3",
        ]

        result = self._run_command(
            ocr_command,
            operation=f"OCR page {page_number}",
        )

        return self._normalize_page_text(
            result.stdout,
        )

    # -------------------------------------------------------------------------
    # Segment construction
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_segments(
        *,
        pages: list[str],
    ) -> list[DocumentSegment]:
        """
        Build one page-aware segment per PDF page.
        """

        segments: list[DocumentSegment] = []

        offset = 0

        for index, page_text in enumerate(pages):
            start_offset = offset
            end_offset = start_offset + len(page_text)

            segments.append(
                DocumentSegment(
                    index=index,
                    text=page_text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    metadata={
                        "type": "page",
                        "page": index + 1,
                        "extraction_method": "ocr",
                    },
                )
            )

            offset = end_offset

            if index < len(pages) - 1:
                offset += 2

        return segments

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def _build_metadata(
        self,
        *,
        path: Path,
        page_count: int,
        reader: PdfReader,
    ) -> dict[str, object]:
        """
        Build OCR provenance metadata.
        """

        metadata: dict[str, object] = {}

        if reader.metadata:
            for key, value in reader.metadata.items():
                metadata[key.lstrip("/")] = (
                    str(value)
                    if value is not None
                    else ""
                )

        metadata.update(
            {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "page_count": page_count,
                "extraction_method": "ocr",
                "ocr_engine": "tesseract",
                "ocr_language": self._language,
                "ocr_dpi": self._dpi,
                "fallback_used": False,
            }
        )

        return metadata

    @staticmethod
    def _extract_title(
        reader: PdfReader,
        path: Path,
    ) -> str:
        """
        Resolve the document title using PDF metadata when available.
        """

        title = path.stem

        if reader.metadata:
            pdf_title = reader.metadata.title

            if pdf_title:
                pdf_title = pdf_title.strip()

                if pdf_title.lower() not in {
                    "",
                    "untitled",
                    "none",
                }:
                    title = pdf_title

        return title

    # -------------------------------------------------------------------------
    # Text normalization
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_page_text(
        text: str,
    ) -> str:
        """
        Normalize OCR output without attempting semantic correction.

        Whitespace is normalized, but OCR tokens themselves are not
        corrected because OCR output must remain faithful to the source.
        """

        lines = [
            line.rstrip()
            for line in text.splitlines()
        ]

        return "\n".join(lines).strip()

    # -------------------------------------------------------------------------
    # Command execution
    # -------------------------------------------------------------------------

    @staticmethod
    def _require_command(
        command: str,
    ) -> None:
        """
        Verify that an external OCR dependency exists.
        """

        if shutil.which(command) is None:
            raise RuntimeError(
                f"Required OCR executable '{command}' was not found. "
                "Install the OCR system dependencies in the backend "
                "container."
            )

    def _run_command(
        self,
        command: list[str],
        *,
        operation: str,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute an OCR-related external command safely.
        """

        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"{operation} timed out after "
                f"{self._timeout_seconds} seconds"
            ) from exc

        except FileNotFoundError as exc:
            executable = command[0]

            raise RuntimeError(
                f"Required OCR executable '{executable}' "
                "was not found."
            ) from exc

        except subprocess.CalledProcessError as exc:
            stderr = (
                exc.stderr.strip()
                if exc.stderr
                else "no stderr output"
            )

            raise RuntimeError(
                f"{operation} failed with exit code "
                f"{exc.returncode}: {stderr}"
            ) from exc
