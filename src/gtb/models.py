from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum


class FormatType(IntEnum):
    """Format priority — lower value = higher priority."""
    PDF_TEXT = 1
    MD = 2
    EPUB = 3
    MOBI = 4
    PDF_SCANNED = 5
    OTHER = 6


@dataclass
class BookResult:
    title: str
    author: str
    md5: str
    extension: str
    size_bytes: int
    language: str
    year: str
    source: str
    mirror_url: str = ""
    pages: str = ""
    publisher: str = ""

    @property
    def format_type(self) -> FormatType:
        ext = self.extension.lower().strip(".")
        if ext == "md":
            return FormatType.MD
        if ext == "epub":
            return FormatType.EPUB
        if ext in ("mobi", "azw3"):
            return FormatType.MOBI
        if ext == "pdf":
            return FormatType.PDF_SCANNED if self._is_likely_scanned() else FormatType.PDF_TEXT
        return FormatType.OTHER

    def _is_likely_scanned(self) -> bool:
        pages = self._parse_pages()
        if pages == 0:
            return self.size_bytes > 100 * 1024 * 1024
        bytes_per_page = self.size_bytes / pages
        return bytes_per_page > 80 * 1024

    def _parse_pages(self) -> int:
        if not self.pages:
            return 0
        m = re.search(r"\d+", self.pages)
        return int(m.group()) if m else 0

    @property
    def size_display(self) -> str:
        if self.size_bytes >= 1024 ** 3:
            return f"{self.size_bytes / 1024**3:.1f} GB"
        if self.size_bytes >= 1024 ** 2:
            return f"{self.size_bytes / 1024**2:.1f} MB"
        if self.size_bytes >= 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes} B"
