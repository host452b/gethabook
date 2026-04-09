from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..models import BookResult
from .base import Source, USER_AGENT

MIRRORS = ["libgen.is", "libgen.st", "libgen.rs"]


def _parse_size(size_str: str) -> int:
    """Parse '5 Mb' -> bytes."""
    m = re.match(r"([\d.]+)\s*(kb|mb|gb|bytes?|b)", size_str.strip(), re.IGNORECASE)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    mult = {"b": 1, "byte": 1, "bytes": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
    return int(val * mult.get(unit, 1))


class LibGenSource(Source):
    name = "libgen"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30,
        )
        self.base_url: str | None = None

    def _find_mirror(self) -> str | None:
        for mirror in MIRRORS:
            try:
                url = f"https://{mirror}"
                r = self.client.get(url, timeout=10)
                if r.status_code == 200:
                    self.base_url = url
                    return url
            except httpx.RequestError:
                continue
        return None

    def search(self, query: str) -> list[BookResult]:
        if not self.base_url and not self._find_mirror():
            return []

        params = {
            "req": query,
            "lg_topic": "libgen",
            "open": "0",
            "view": "simple",
            "res": "25",
            "phrase": "1",
            "column": "def",
        }
        try:
            resp = self.client.get(f"{self.base_url}/search.php", params=params)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[BookResult]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="c")
        if not table:
            return []

        results: list[BookResult] = []
        for row in table.find_all("tr")[1:]:  # skip header
            cols = row.find_all("td")
            if len(cols) < 10:
                continue

            # MD5 from mirror links (search cols 9+ for mirror columns)
            mirror_url, md5 = "", ""
            for col in cols[9:]:
                for a in col.find_all("a"):
                    href = a.get("href", "")
                    md5_match = re.search(r"/([a-fA-F0-9]{32})", href)
                    if md5_match:
                        mirror_url = href
                        md5 = md5_match.group(1).upper()
                        break
                    m = re.search(r"md5=([a-fA-F0-9]{32})", href, re.IGNORECASE)
                    if m:
                        mirror_url = href
                        md5 = m.group(1).upper()
                        break
                if md5:
                    break
            if not md5:
                continue

            title_links = cols[2].find_all("a")
            title = title_links[-1].get_text(strip=True) if title_links else cols[2].get_text(strip=True)

            results.append(BookResult(
                title=title,
                author=cols[1].get_text(strip=True),
                md5=md5,
                extension=cols[8].get_text(strip=True).lower(),
                size_bytes=_parse_size(cols[7].get_text(strip=True)),
                language=cols[6].get_text(strip=True),
                year=cols[4].get_text(strip=True),
                publisher=cols[3].get_text(strip=True),
                pages=cols[5].get_text(strip=True),
                source="libgen",
                mirror_url=mirror_url,
            ))
        return results

    def resolve_download_url(self, book: BookResult) -> str | None:
        if not book.mirror_url:
            return None

        try:
            resp = self.client.get(book.mirror_url)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        for link in soup.find_all("a"):
            if link.get_text(strip=True) == "GET":
                href = link.get("href", "")
                if href.startswith("http"):
                    return href
                parsed = urlparse(book.mirror_url)
                return f"{parsed.scheme}://{parsed.netloc}{href}"
        return None
