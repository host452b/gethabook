from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..models import BookResult
from .base import Source, parse_size

MIRRORS = ["annas-archive.gl", "annas-archive.pk", "annas-archive.gd"]


def _parse_meta_line(text: str) -> dict:
    """Parse a line like 'English, 2008, pdf, 5.0MB, 464 pages' into fields."""
    info: dict = {"language": "", "year": "", "extension": "", "size_bytes": 0, "pages": ""}
    parts = [p.strip() for p in text.split(",")]
    for part in parts:
        part_lower = part.lower()
        if re.match(r"^\d{4}$", part):
            info["year"] = part
        elif re.match(r"^[\d.]+\s*(kb|mb|gb|b)$", part_lower):
            info["size_bytes"] = parse_size(part)
        elif re.match(r"^\d+\s*pages?$", part_lower):
            info["pages"] = re.search(r"\d+", part).group()
        elif part_lower in ("pdf", "epub", "mobi", "azw3", "djvu", "md", "txt", "fb2", "cbr", "cbz", "doc", "docx", "rtf"):
            info["extension"] = part_lower
        elif len(part) > 1 and not part[0].isdigit():
            info["language"] = part
    return info


class AnnasArchiveSource(Source):
    name = "annas"

    def __init__(self) -> None:
        super().__init__()
        self.base_url: str | None = None

    def _find_mirror(self) -> str | None:
        for mirror in MIRRORS:
            try:
                url = f"https://{mirror}"
                resp = self.client.get(url, timeout=10)
                if resp.status_code == 200:
                    self.base_url = url
                    return url
            except httpx.RequestError:
                continue
        return None

    def search(self, query: str) -> list[BookResult]:
        if not self.base_url and not self._find_mirror():
            return []

        params = {"q": query}
        try:
            resp = self._get(f"{self.base_url}/search", params=params)
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[BookResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[BookResult] = []

        md5_links = soup.find_all("a", href=re.compile(r"/md5/[a-fA-F0-9]{32}$"))
        for link in md5_links:
            href = link.get("href", "")
            md5_match = re.search(r"/md5/([a-fA-F0-9]{32})$", href)
            if not md5_match:
                continue
            md5 = md5_match.group(1).upper()

            title = link.get_text(strip=True)
            if not title:
                continue

            container = link.find_parent("div", class_="mb-4") or link.parent
            author = ""
            meta: dict = {}

            if container:
                divs = container.find_all("div")
                for div in divs:
                    text = div.get_text(strip=True)
                    if div == link.parent:
                        continue
                    if not author and not re.search(r"\d{4}", text) and not re.search(r"(pdf|epub|mobi|md|djvu)", text, re.I):
                        author = text
                    if re.search(r"\d{4}", text) and re.search(r"(pdf|epub|mobi|md|djvu)", text, re.I):
                        meta = _parse_meta_line(text)

            results.append(BookResult(
                title=title,
                author=author,
                md5=md5,
                extension=meta.get("extension", ""),
                size_bytes=meta.get("size_bytes", 0),
                language=meta.get("language", ""),
                year=meta.get("year", ""),
                pages=meta.get("pages", ""),
                source="annas",
            ))

        return results

    def resolve_download_url(self, book: BookResult) -> str | None:
        """Two-hop: detail page -> external link (library.lol) -> GET link."""
        if not self.base_url:
            if not self._find_mirror():
                return None

        detail_url = f"{self.base_url}/md5/{book.md5}"
        try:
            resp = self._get(detail_url)
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        panel = soup.find("div", id="md5-panel-downloads")
        if not panel:
            panel = soup

        external_links = panel.find_all("a", class_="js-download-link")
        if not external_links:
            external_links = panel.find_all("a", href=re.compile(r"library\.lol"))

        for ext_link in external_links:
            mirror_url = ext_link.get("href", "")
            if not mirror_url:
                continue
            try:
                resp2 = self._get(mirror_url)
            except (httpx.RequestError, httpx.HTTPStatusError):
                continue

            mirror_soup = BeautifulSoup(resp2.text, "lxml")
            for a in mirror_soup.find_all("a"):
                if a.get_text(strip=True) == "GET":
                    href = a.get("href", "")
                    if href.startswith("http"):
                        return href
                    parsed = urlparse(mirror_url)
                    return f"{parsed.scheme}://{parsed.netloc}{href}"

        return None
