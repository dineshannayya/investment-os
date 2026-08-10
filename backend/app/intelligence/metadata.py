"""
Metadata extractor.
"""

from __future__ import annotations

import re

from app.chunking.base import Chunk
from app.intelligence.base import IntelligenceExtractor
from app.intelligence.models import DocumentMetadata
from app.processors import DocumentContent


class MetadataExtractor(IntelligenceExtractor[DocumentMetadata]):
    """
    Extract document-level metadata from processed content.
    """

    SECTION_PATTERN = re.compile(
        r"^(#+\s+.+|[A-Z][A-Za-z0-9 /&()_-]{2,80}:?)$",
        re.MULTILINE,
    )

    KEYWORD_PATTERN = re.compile(r"\b[A-Za-z]{2,}[A-Za-z0-9+\-]*\b")

    COMMON_STOP_WORDS = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "have",
        "will",
        "your",
        "into",
        "their",
        "about",
        "page",
        "document",
        "company",
    }

    @property
    def name(self) -> str:
        return "metadata"

    def extract(
        self,
        document: DocumentContent,
        chunks: list[Chunk],
    ) -> DocumentMetadata:
        """
        Extract document metadata.
        """

        title = self._extract_title(document)

        sections = self._extract_sections(document)

        keywords = self._extract_keywords(document)

        return DocumentMetadata(
            title=title,
            document_type=self._classify_document(title),
            language=None,
            page_count=document.page_count,
            sections=tuple(sections),
            keywords=tuple(keywords),
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_title(
        self,
        document: DocumentContent,
    ) -> str:
        """
        Determine the document title.
        """

        if document.title:
            return document.title.strip()

        for line in document.text.splitlines():
            line = line.strip()

            if line:
                return line

        return "Untitled"

    def _extract_sections(
        self,
        document: DocumentContent,
    ) -> list[str]:
    
        sections: list[str] = []
    
        for line in document.text.splitlines():
            line = line.strip()
    
            if not line:
                continue
    
            if line.startswith("#"):
                heading = line.rstrip()
    
            elif line.endswith(":"):
                heading = line[:-1].strip()
    
            else:
                continue
    
            if heading not in sections:
                sections.append(heading)
    
        return sections


    def _extract_keywords(
        self,
        document: DocumentContent,
    ) -> list[str]:
        """
        Extract simple keywords.
        """

        words: dict[str, int] = {}

        for match in self.KEYWORD_PATTERN.finditer(document.text.lower()):
            word = match.group(0)

            if word in self.COMMON_STOP_WORDS:
                continue

            words[word] = words.get(word, 0) + 1

        return [
            keyword
            for keyword, _ in sorted(
                words.items(),
                key=lambda item: (-item[1], item[0]),
            )[:20]
        ]

    def _classify_document(
        self,
        title: str,
    ) -> str | None:
        """
        Very lightweight document classification.

        This is intentionally simple and will later
        be replaced by a dedicated classifier.
        """

        title = title.lower()

        if "pitch" in title:
            return "Pitch Deck"

        if "term sheet" in title:
            return "Term Sheet"

        if "shareholder" in title or "sha" in title:
            return "Shareholders Agreement"

        if "financial" in title:
            return "Financial Statement"

        if "cap table" in title:
            return "Cap Table"

        return None
