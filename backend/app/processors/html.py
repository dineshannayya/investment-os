"""
HTML document processor.

Extracts human-readable HTML content while preserving basic
document structure such as headings, paragraphs, lists, and
table rows.

The processor intentionally does NOT:
- classify the source
- interpret investment claims
- extract investment evidence
- call an LLM
- reconcile conflicting information

Those responsibilities belong to later layers.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import UUID

from app.processors.base import (
    DocumentContent,
    DocumentProcessor,
    DocumentSegment,
)


class _HtmlTextExtractor(HTMLParser):
    """
    Internal HTML parser that converts human-readable HTML
    elements into structured text blocks.

    This intentionally ignores scripts, styles, SVGs and other
    non-document content.
    """

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "dt",
        "dd",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "pre",
        "section",
        "td",
        "th",
        "tr",
    }

    _HEADING_TAGS = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "title",
    }

    _IGNORED_TAGS = {
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "iframe",
        "object",
        "embed",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self.blocks: list[dict[str, Any]] = []
        self.document_title: str | None = None

        self._ignored_depth = 0
        self._block_stack: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Tag handling
    # ------------------------------------------------------------------

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()

        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return

        if self._ignored_depth:
            return

        if tag == "br":
            self._append_text("\n")
            return

        if tag == "title":
            self._start_block(
                tag="title",
                block_type="title",
            )
            return

        if tag in self._BLOCK_TAGS:
            block_type = self._block_type(tag)

            self._start_block(
                tag=tag,
                block_type=block_type,
            )

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in self._IGNORED_TAGS:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return

        if self._ignored_depth:
            return

        if tag in self._BLOCK_TAGS or tag == "title":
            self._finish_block(tag)

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return

        self._append_text(data)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _start_block(
        self,
        *,
        tag: str,
        block_type: str,
    ) -> None:
        """
        Start a new structural block.

        Nested block tags are allowed. The outer block is finalized
        when a nested block begins so that we do not accidentally
        combine unrelated HTML structures.
        """

        if self._block_stack:
            self._finish_current_block()

        self._block_stack.append(
            {
                "tag": tag,
                "type": block_type,
                "parts": [],
            }
        )

    def _finish_block(self, tag: str) -> None:
        if not self._block_stack:
            return

        current = self._block_stack[-1]

        if current["tag"] != tag:
            return

        self._finish_current_block()

    def _finish_current_block(self) -> None:
        if not self._block_stack:
            return

        block = self._block_stack.pop()

        text = self._normalize_text("".join(block["parts"]))

        if not text:
            return

        block_type = block["type"]

        if block_type == "title" and self.document_title is None:
            self.document_title = text

        self.blocks.append(
            {
                "type": block_type,
                "tag": block["tag"],
                "text": text,
            }
        )

    def _append_text(self, text: str) -> None:
        if not self._block_stack:
            return

        self._block_stack[-1]["parts"].append(text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize whitespace while preserving meaningful line breaks.
        """

        lines = []

        for line in text.splitlines():
            normalized = " ".join(line.split())

            if normalized:
                lines.append(normalized)

        return "\n".join(lines).strip()

    @classmethod
    def _block_type(cls, tag: str) -> str:
        if tag in cls._HEADING_TAGS:
            return "heading"

        if tag == "li":
            return "list_item"

        if tag in {"td", "th"}:
            return "table_cell"

        if tag == "tr":
            return "table_row"

        return "paragraph"


class HtmlProcessor(DocumentProcessor):
    """
    Processor for HTML documents.

    Supported formats:
        .html
        .htm

    Supported MIME types:
        text/html
        application/xhtml+xml
    """

    _SUPPORTED_MIME_TYPES = {
        "text/html",
        "application/xhtml+xml",
    }

    _SUPPORTED_EXTENSIONS = {
        ".html",
        ".htm",
    }

    @property
    def supported_mime_types(self) -> set[str]:
        """Return supported MIME types."""
        return self._SUPPORTED_MIME_TYPES

    @property
    def supported_extensions(self) -> set[str]:
        """Return supported file extensions."""
        return self._SUPPORTED_EXTENSIONS

    def process(
        self,
        document_id: UUID,
        path: Path,
    ) -> DocumentContent:
        """
        Extract human-readable content from an HTML document.
        """

        html, encoding = self._read_text(path)

        parser = _HtmlTextExtractor()
        parser.feed(html)
        parser.close()

        # Flush any unfinished block caused by malformed HTML.
        while parser._block_stack:
            parser._finish_current_block()

        blocks = parser.blocks

        text_parts: list[str] = []
        segments: list[DocumentSegment] = []

        offset = 0

        for index, block in enumerate(blocks):
            block_text = block["text"]

            if text_parts:
                text_parts.append("\n\n")
                offset += 2

            start_offset = offset
            text_parts.append(block_text)
            offset += len(block_text)
            end_offset = offset

            segments.append(
                DocumentSegment(
                    index=index,
                    text=block_text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    metadata={
                        "type": block["type"],
                        "html_tag": block["tag"],
                    },
                )
            )

        text = "".join(text_parts)

        title = parser.document_title or path.stem

        metadata = {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "encoding": encoding,
            "block_count": len(blocks),
            "heading_count": sum(
                1
                for block in blocks
                if block["type"] == "heading"
            ),
            "paragraph_count": sum(
                1
                for block in blocks
                if block["type"] == "paragraph"
            ),
            "list_item_count": sum(
                1
                for block in blocks
                if block["type"] == "list_item"
            ),
            "table_row_count": sum(
                1
                for block in blocks
                if block["type"] == "table_row"
            ),
        }

        return DocumentContent(
            document_id=document_id,
            title=title,
            text=text,
            page_count=1,
            metadata=metadata,
            segments=tuple(segments),
        )

    @staticmethod
    def _read_text(path: Path) -> tuple[str, str]:
        """
        Read HTML as UTF-8 first, followed by Latin-1 fallback.
        """

        try:
            return (
                path.read_text(encoding="utf-8"),
                "utf-8",
            )
        except UnicodeDecodeError:
            return (
                path.read_text(encoding="latin-1"),
                "latin-1",
            )
