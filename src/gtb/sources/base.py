from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import BookResult

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class Source(ABC):
    """Abstract base for ebook search sources."""

    name: str

    @abstractmethod
    def search(self, query: str) -> list[BookResult]:
        ...

    @abstractmethod
    def resolve_download_url(self, book: BookResult) -> str | None:
        ...
