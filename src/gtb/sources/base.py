from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod

import httpx

from ..models import BookResult

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Polite delay between requests to avoid IP bans (seconds)
REQUEST_DELAY = 0.5


def parse_size(size_str: str) -> int:
    """Parse human-readable size like '5 Mb' to bytes."""
    m = re.match(r"([\d.]+)\s*(kb|mb|gb|bytes?|b)", size_str.strip(), re.IGNORECASE)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    mult = {"b": 1, "byte": 1, "bytes": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
    return int(val * mult.get(unit, 1))


class Source(ABC):
    """Abstract base for ebook search sources."""

    name: str

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30,
        )
        self._last_request_time: float = 0

    def close(self) -> None:
        self.client.close()

    def _get(self, url: str, retries: int = 2, **kwargs) -> httpx.Response:
        """HTTP GET with polite delay and retry."""
        # Rate limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                self._last_request_time = time.monotonic()
                resp = self.client.get(url, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(1 * (attempt + 1))  # linear backoff
        raise last_err

    @abstractmethod
    def search(self, query: str) -> list[BookResult]:
        ...

    @abstractmethod
    def resolve_download_url(self, book: BookResult) -> str | None:
        ...
