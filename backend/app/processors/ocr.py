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
import sys
import tempfile
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
from time import monotonic
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

    Pages are processed independently using a bounded worker pool.

    The original PDF is never modified.

    Configuration defaults:
        language: eng
        dpi: 100
        timeout_seconds: 120
        workers: 4
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
        dpi: int = 100,
        timeout_seconds: int = 120,
        workers: int = 4,
    ) -> None:
        if dpi <= 0:
            raise ValueError(
                "dpi must be greater than zero"
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        if workers <= 0:
            raise ValueError(
                "workers must be greater than zero"
            )

        self._language = language
        self._dpi = dpi
        self._timeout_seconds = timeout_seconds
        self._workers = workers

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

        Pages are processed concurrently using a bounded worker pool,
        but returned segments always preserve the original PDF page order.

        Each PDF page becomes one DocumentSegment.

        Raises:
            FileNotFoundError:
                If the source PDF does not exist.

            ValueError:
                If the source path is not a file.

            RuntimeError:
                If the PDF contains no pages, required OCR executables
                are unavailable, rendering/OCR fails, or an OCR operation
                times out.
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

        process_start = monotonic()

        self._log(
            "START "
            f"file={path.name} "
            f"dpi={self._dpi} "
            f"workers={self._workers} "
            f"language={self._language} "
            f"timeout={self._timeout_seconds}s"
        )

        reader = PdfReader(path)

        page_count = len(reader.pages)

        if page_count == 0:
            raise RuntimeError(
                f"PDF contains no pages: {path}"
            )

        self._log(
            "DOCUMENT "
            f"file={path.name} "
            f"pages={page_count} "
            f"dpi={self._dpi} "
            f"workers={self._workers}"
        )

        title = self._extract_title(
            reader,
            path,
        )

        self._log(
            f"TITLE file={path.name} title={title!r}"
        )

        # Do not create more workers than pages.
        worker_count = min(
            self._workers,
            page_count,
        )

        self._log(
            "POOL_START "
            f"file={path.name} "
            f"workers={worker_count}"
        )

        page_texts: list[str] = [
            ""
            for _ in range(page_count)
        ]

        # Each page gets a separate temporary directory. This prevents
        # concurrent workers from ever sharing intermediate image paths.
        with tempfile.TemporaryDirectory(
            prefix="investment-os-ocr-",
        ) as temp_dir:

            temp_root = Path(temp_dir)

            futures: dict[
                Future[str],
                int,
            ] = {}

            try:
                with ThreadPoolExecutor(
                    max_workers=worker_count,
                    thread_name_prefix="ocr-page",
                ) as executor:

                    for page_number in range(
                        1,
                        page_count + 1,
                    ):
                        page_dir = (
                            temp_root
                            / f"page-{page_number:04d}"
                        )

                        page_dir.mkdir(
                            parents=True,
                            exist_ok=True,
                        )

                        future = executor.submit(
                            self._ocr_page,
                            path=path,
                            page_number=page_number,
                            page_count=page_count,
                            output_dir=page_dir,
                        )

                        futures[future] = page_number

                    for future in as_completed(futures):
                        page_number = futures[future]

                        try:
                            page_texts[
                                page_number - 1
                            ] = future.result()

                        except Exception as exc:
                            self._log(
                                "PAGE_FAILED "
                                f"file={path.name} "
                                f"page={page_number}/{page_count} "
                                f"error={exc!r}"
                            )

                            # Cancel work that has not started yet.
                            for pending in futures:
                                if pending is not future:
                                    pending.cancel()

                            raise

            except Exception:
                self._log(
                    "POOL_FAILED "
                    f"file={path.name}"
                )
                raise

        self._log(
            "POOL_DONE "
            f"file={path.name} "
            f"pages={page_count}"
        )

        text = "\n\n".join(page_texts)

        segments = self._build_segments(
            pages=page_texts,
        )

        metadata = self._build_metadata(
            path=path,
            page_count=page_count,
            reader=reader,
        )

        elapsed = monotonic() - process_start

        self._log(
            "COMPLETE "
            f"file={path.name} "
            f"pages={page_count} "
            f"text_chars={len(text)} "
            f"segments={len(segments)} "
            f"elapsed={elapsed:.1f}s"
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
        page_count: int,
        output_dir: Path,
    ) -> str:
        """Render and OCR one PDF page."""

        page_start = monotonic()

        self._log(
            "PAGE_START "
            f"file={path.name} "
            f"page={page_number}/{page_count}"
        )

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

        self._log(
            "RENDER_START "
            f"file={path.name} "
            f"page={page_number}/{page_count} "
            f"dpi={self._dpi}"
        )

        render_start = monotonic()

        self._run_command(
            render_command,
            operation=(
                f"PDF rendering page "
                f"{page_number}/{page_count}"
            ),
        )

        render_elapsed = monotonic() - render_start

        image_path = image_prefix.with_suffix(".png")

        if not image_path.exists():
            raise RuntimeError(
                "PDF renderer did not produce expected image "
                f"for page {page_number}: {image_path}"
            )

        try:
            image_size = image_path.stat().st_size
        except OSError:
            image_size = -1

        self._log(
            "RENDER_DONE "
            f"file={path.name} "
            f"page={page_number}/{page_count} "
            f"elapsed={render_elapsed:.1f}s "
            f"image_bytes={image_size}"
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

        self._log(
            "OCR_START "
            f"file={path.name} "
            f"page={page_number}/{page_count} "
            f"engine=tesseract "
            f"language={self._language}"
        )

        ocr_start = monotonic()

        result = self._run_command(
            ocr_command,
            operation=(
                f"OCR page "
                f"{page_number}/{page_count}"
            ),
        )

        ocr_elapsed = monotonic() - ocr_start

        page_text = self._normalize_page_text(
            result.stdout,
        )

        self._log(
            "OCR_DONE "
            f"file={path.name} "
            f"page={page_number}/{page_count} "
            f"elapsed={ocr_elapsed:.1f}s "
            f"text_chars={len(page_text)}"
        )

        page_elapsed = monotonic() - page_start

        self._log(
            "PAGE_DONE "
            f"file={path.name} "
            f"page={page_number}/{page_count} "
            f"elapsed={page_elapsed:.1f}s "
            f"text_chars={len(page_text)}"
        )

        return page_text

    # -------------------------------------------------------------------------
    # Segment construction
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_segments(
        *,
        pages: list[str],
    ) -> list[DocumentSegment]:
        """Build one page-aware segment per PDF page."""

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

        Execution configuration is included here so that the processor's
        actual runtime configuration remains the source of truth for
        persistence.
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
                "ocr_workers": self._workers,
                "ocr_timeout_seconds": self._timeout_seconds,
                "fallback_used": False,
            }
        )

        return metadata

    # -------------------------------------------------------------------------
    # Title
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_title(
        reader: PdfReader,
        path: Path,
    ) -> str:
        """Resolve the document title using PDF metadata when available."""

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
        Normalize OCR output without semantic correction.

        OCR tokens are deliberately not corrected because OCR output
        should remain faithful to the source document.
        """

        lines = [
            line.rstrip()
            for line in text.splitlines()
        ]

        return "\n".join(lines).strip()

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    @staticmethod
    def _log(message: str) -> None:
        """Emit OCR progress information to stderr."""

        print(
            f"[OCR] {message}",
            file=sys.stderr,
            flush=True,
        )

    # -------------------------------------------------------------------------
    # Command execution
    # -------------------------------------------------------------------------

    @staticmethod
    def _require_command(
        command: str,
    ) -> None:
        """Verify that an external OCR dependency exists."""

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
        """Execute an OCR-related external command safely."""

        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )

        except subprocess.TimeoutExpired as exc:
            self._log(
                "TIMEOUT "
                f"operation={operation!r} "
                f"timeout={self._timeout_seconds}s"
            )

            raise RuntimeError(
                f"{operation} timed out after "
                f"{self._timeout_seconds} seconds"
            ) from exc

        except FileNotFoundError as exc:
            executable = command[0]

            self._log(
                "EXECUTABLE_NOT_FOUND "
                f"executable={executable}"
            )

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

            self._log(
                "COMMAND_FAILED "
                f"operation={operation!r} "
                f"exit_code={exc.returncode} "
                f"stderr={stderr[:500]!r}"
            )

            raise RuntimeError(
                f"{operation} failed with exit code "
                f"{exc.returncode}: {stderr}"
            ) from exc
