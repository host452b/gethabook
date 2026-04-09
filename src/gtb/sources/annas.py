from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..models import BookResult
from .base import Source, parse_size

MIRRORS = ["annas-archive.gl", "annas-archive.pk", "annas-archive.gd"]


def _parse_meta_line(text: str) -> dict:
    """Parse metadata like 'English [en] · PDF · 23.2MB · 2023 · ...'"""
    info: dict = {"language": "", "year": "", "extension": "", "size_bytes": 0, "pages": ""}

    # Split on middle dot separator
    parts = [p.strip() for p in re.split(r"\s*·\s*", text)]
    for part in parts:
        part_stripped = part.strip()
        part_lower = part_stripped.lower()

        # Year: 4 digits
        if re.match(r"^\d{4}$", part_stripped):
            info["year"] = part_stripped
        # Size: e.g. "23.2MB"
        elif re.match(r"^[\d.]+\s*(kb|mb|gb|b)$", part_lower):
            info["size_bytes"] = parse_size(part_stripped)
        # Pages: e.g. "464 pages"
        elif re.match(r"^\d+\s*pages?$", part_lower):
            m = re.search(r"\d+", part_stripped)
            info["pages"] = m.group() if m else ""
        # Extension: pdf, epub, etc (case insensitive, may be uppercase like "PDF")
        elif part_lower in ("pdf", "epub", "mobi", "azw3", "djvu", "md", "txt",
                            "fb2", "cbr", "cbz", "doc", "docx", "rtf"):
            info["extension"] = part_lower
        # Language: e.g. "English [en]" — take first part if has brackets
        elif re.match(r"^[A-Z]", part_stripped) and "[" in part_stripped:
            info["language"] = re.sub(r"\s*\[.*\]", "", part_stripped)
        # Language without brackets
        elif re.match(r"^[A-Za-z]+$", part_stripped) and len(part_stripped) > 1 and not part_stripped[0].isdigit():
            if not info["language"]:
                info["language"] = part_stripped

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
        seen_md5: set[str] = set()

        # Real AA structure: each result row is a div with border-b and pt-3
        rows = soup.find_all(
            "div",
            class_=lambda c: c and "border-b" in c and "pt-3" in c,
        )

        for row in rows:
            # Find title link: <a> with /md5/ href that has visible text
            title = ""
            md5 = ""
            for a in row.find_all("a", href=re.compile(r"/md5/[a-fA-F0-9]{32}")):
                text = a.get_text(strip=True)
                if text and len(text) > 3:
                    href = a.get("href", "")
                    m = re.search(r"/md5/([a-fA-F0-9]{32})", href)
                    if m:
                        title = text
                        md5 = m.group(1).upper()
                        break

            if not md5 or md5 in seen_md5:
                continue
            seen_md5.add(md5)

            # Find metadata line: div containing middle dot separator
            meta: dict = {}
            author = ""
            for div in row.find_all("div"):
                text = div.get_text(strip=True)
                if "·" in text and len(text) < 300:
                    meta = _parse_meta_line(text)
                    break

            # Author: look for a line-clamped div that isn't the title
            for div in row.find_all("div", class_=lambda c: c and "line-clamp" in " ".join(c) if c else False):
                text = div.get_text(strip=True)
                if text and text != title and not re.search(r"·", text):
                    author = text
                    break

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

        # Fallback: if row-based parsing found nothing, try the old link-based approach
        if not results:
            for link in soup.find_all("a", href=re.compile(r"/md5/[a-fA-F0-9]{32}$")):
                text = link.get_text(strip=True)
                if not text or len(text) < 3:
                    continue
                m = re.search(r"/md5/([a-fA-F0-9]{32})$", link.get("href", ""))
                if not m:
                    continue
                md5 = m.group(1).upper()
                if md5 in seen_md5:
                    continue
                seen_md5.add(md5)
                results.append(BookResult(
                    title=text, author="", md5=md5,
                    extension="", size_bytes=0, language="",
                    year="", pages="", source="annas",
                ))

        return results

    def resolve_download_url(self, book: BookResult) -> str | None:
        """Resolve via detail page → find libgen mirror link → scrape GET link."""
        if not self.base_url:
            if not self._find_mirror():
                return None

        detail_url = f"{self.base_url}/md5/{book.md5}"
        try:
            resp = self._get(detail_url)
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Strategy 1: Find direct libgen.is/book/index.php?md5= link
        libgen_link = soup.find("a", href=re.compile(
            r"https?://libgen\.(is|rs|st)/book/index\.php\?md5=", re.I
        ))
        if libgen_link:
            mirror_url = libgen_link["href"]
            return self._resolve_mirror_page(mirror_url)

        # Strategy 2: Find libgen.li/file.php link (direct download)
        libgen_li = soup.find("a", href=re.compile(r"https?://libgen\.li/file\.php"))
        if libgen_li:
            return libgen_li["href"]

        # Strategy 3: Find any library.lol link
        lol_link = soup.find("a", href=re.compile(r"https?://library\.lol/"))
        if lol_link:
            return self._resolve_mirror_page(lol_link["href"])

        # Strategy 4: Construct libgen mirror URL from MD5 directly
        return self._resolve_mirror_page(
            f"https://libgen.is/book/index.php?md5={book.md5}"
        )

    def _resolve_mirror_page(self, mirror_url: str) -> str | None:
        """Fetch a mirror page and extract the GET download link."""
        try:
            resp = self._get(mirror_url)
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a"):
            if a.get_text(strip=True) == "GET":
                href = a.get("href", "")
                if href.startswith("http"):
                    return href
                parsed = urlparse(mirror_url)
                return f"{parsed.scheme}://{parsed.netloc}{href}"
        return None
