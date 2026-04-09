# gethatbook (gtb) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool `gtb` that searches multiple ebook sources (LibGen, Anna's Archive) in parallel, deduplicates by MD5, auto-selects the best result by format priority `pdf(text) > md > epub > pdf(scanned)`, and downloads to the current directory.

**Architecture:** Plugin-style source backends behind a common `Source` ABC. A search orchestrator runs all sources in parallel via `concurrent.futures.ThreadPoolExecutor`, merges and deduplicates results by MD5 hash, then a ranking module picks the best result. A download manager fetches the file by resolving the actual download URL through mirror page scraping. CLI is a single `click` command.

**Tech Stack:** Python 3.10+, httpx (HTTP client), beautifulsoup4+lxml (HTML parsing), click (CLI)

---

## File Structure

```
gethatbook/
├── pyproject.toml                  # Package metadata, dependencies, [project.scripts] gtb entry point
├── src/
│   └── gtb/
│       ├── __init__.py             # Package version
│       ├── models.py               # BookResult dataclass, FormatType enum
│       ├── ranking.py              # score_book(), select_best()
│       ├── sources/
│       │   ├── __init__.py         # Source registry: ALL_SOURCES list
│       │   ├── base.py             # Source ABC
│       │   ├── libgen.py           # LibGenSource: search libgen.is + resolve library.lol mirror
│       │   └── annas.py            # AnnasArchiveSource: search annas-archive.gl + resolve external links
│       ├── search.py               # parallel_search(): ThreadPoolExecutor + dedup by MD5
│       ├── download.py             # download_file(): stream download with progress
│       └── cli.py                  # click CLI: gtb command
└── tests/
    ├── conftest.py                 # Shared HTML fixtures for mocking HTTP responses
    ├── test_models.py              # Tests for BookResult.format_type and scanned detection
    ├── test_ranking.py             # Tests for score_book, select_best
    ├── test_libgen.py              # Tests for LibGenSource with mocked HTML
    ├── test_annas.py               # Tests for AnnasArchiveSource with mocked HTML
    ├── test_search.py              # Tests for parallel_search with mock sources
    ├── test_download.py            # Tests for download_file with mocked HTTP
    └── test_cli.py                 # Tests for CLI invocation
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/gtb/__init__.py`
- Create: `src/gtb/sources/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "gethatbook"
version = "0.1.0"
description = "Aggregate ebook search across LibGen and Anna's Archive"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.30",
    "respx>=0.21",
]

[project.scripts]
gtb = "gtb.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create src/gtb/__init__.py**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create src/gtb/sources/__init__.py**

```python
from .libgen import LibGenSource
from .annas import AnnasArchiveSource

ALL_SOURCES = [LibGenSource, AnnasArchiveSource]
```

Note: This file will fail to import until Tasks 4 and 6 create the source modules. That is expected.

- [ ] **Step 4: Create empty tests/conftest.py**

```python
"""Shared test fixtures for gethatbook."""
```

- [ ] **Step 5: Install in editable mode and verify**

```bash
cd /localhome/swqa/workspace/gethatbook
pip install -e ".[dev]"
```

Expected: installs successfully, `gtb` command exists (will fail at runtime until cli.py is created).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/gtb/__init__.py src/gtb/sources/__init__.py tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and package structure"
```

---

### Task 2: Data Models and Format Ranking

**Files:**
- Create: `src/gtb/models.py`
- Create: `src/gtb/ranking.py`
- Create: `tests/test_models.py`
- Create: `tests/test_ranking.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/test_models.py`:

```python
from gtb.models import BookResult, FormatType


def test_format_type_text_pdf():
    book = BookResult(
        title="Clean Code",
        author="Robert Martin",
        md5="ABC123",
        extension="pdf",
        size_bytes=5 * 1024 * 1024,  # 5MB
        language="English",
        year="2008",
        source="libgen",
        pages="464",
    )
    assert book.format_type == FormatType.PDF_TEXT


def test_format_type_scanned_pdf():
    book = BookResult(
        title="Clean Code",
        author="Robert Martin",
        md5="ABC123",
        extension="pdf",
        size_bytes=200 * 1024 * 1024,  # 200MB for 464 pages = ~430KB/page
        language="English",
        year="2008",
        source="libgen",
        pages="464",
    )
    assert book.format_type == FormatType.PDF_SCANNED


def test_format_type_epub():
    book = BookResult(
        title="Test", author="A", md5="X", extension="epub",
        size_bytes=1000, language="en", year="2020", source="libgen",
    )
    assert book.format_type == FormatType.EPUB


def test_format_type_md():
    book = BookResult(
        title="Test", author="A", md5="X", extension="md",
        size_bytes=1000, language="en", year="2020", source="libgen",
    )
    assert book.format_type == FormatType.MD


def test_format_type_unknown():
    book = BookResult(
        title="Test", author="A", md5="X", extension="djvu",
        size_bytes=1000, language="en", year="2020", source="libgen",
    )
    assert book.format_type == FormatType.OTHER


def test_scanned_detection_no_pages():
    """Without page info, use absolute size threshold: >100MB = scanned."""
    book = BookResult(
        title="Test", author="A", md5="X", extension="pdf",
        size_bytes=150 * 1024 * 1024, language="en", year="2020", source="libgen",
    )
    assert book.format_type == FormatType.PDF_SCANNED


def test_not_scanned_no_pages_small():
    book = BookResult(
        title="Test", author="A", md5="X", extension="pdf",
        size_bytes=10 * 1024 * 1024, language="en", year="2020", source="libgen",
    )
    assert book.format_type == FormatType.PDF_TEXT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.models'`

- [ ] **Step 3: Implement models.py**

Create `src/gtb/models.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run model tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Write failing tests for ranking**

Create `tests/test_ranking.py`:

```python
from gtb.models import BookResult, FormatType
from gtb.ranking import score_book, select_best


def _book(ext: str, size_mb: float, pages: str = "") -> BookResult:
    return BookResult(
        title="Test", author="A", md5="X", extension=ext,
        size_bytes=int(size_mb * 1024 * 1024),
        language="en", year="2020", source="libgen", pages=pages,
    )


def test_score_prefers_text_pdf_over_epub():
    pdf = _book("pdf", 5, "300")
    epub = _book("epub", 1)
    assert score_book(pdf) < score_book(epub)


def test_score_prefers_epub_over_scanned_pdf():
    epub = _book("epub", 1)
    scanned = _book("pdf", 200, "300")  # ~680KB/page -> scanned
    assert score_book(epub) < score_book(scanned)


def test_score_prefers_md_over_epub():
    md = _book("md", 1)
    epub = _book("epub", 1)
    assert score_book(md) < score_book(epub)


def test_select_best_returns_none_for_empty():
    assert select_best([]) is None


def test_select_best_picks_text_pdf():
    books = [
        _book("epub", 1),
        _book("pdf", 5, "300"),
        _book("pdf", 200, "300"),
    ]
    best = select_best(books)
    assert best is not None
    assert best.format_type == FormatType.PDF_TEXT


def test_select_best_prefers_smaller_within_same_format():
    small = _book("pdf", 3, "300")
    large = _book("pdf", 8, "300")
    small.md5 = "SMALL"
    large.md5 = "LARGE"
    best = select_best([large, small])
    assert best is not None
    assert best.md5 == "SMALL"
```

- [ ] **Step 6: Run ranking tests to verify they fail**

```bash
pytest tests/test_ranking.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.ranking'`

- [ ] **Step 7: Implement ranking.py**

Create `src/gtb/ranking.py`:

```python
from __future__ import annotations

from .models import BookResult


def score_book(book: BookResult) -> tuple[int, int]:
    """Lower score = better. Sorts by (format_priority, file_size)."""
    return (book.format_type.value, book.size_bytes)


def select_best(books: list[BookResult]) -> BookResult | None:
    if not books:
        return None
    return min(books, key=score_book)
```

- [ ] **Step 8: Run ranking tests to verify they pass**

```bash
pytest tests/test_ranking.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add src/gtb/models.py src/gtb/ranking.py tests/test_models.py tests/test_ranking.py
git commit -m "feat: data models with format detection and ranking logic"
```

---

### Task 3: Source Base Class

**Files:**
- Create: `src/gtb/sources/base.py`

- [ ] **Step 1: Create the Source ABC**

Create `src/gtb/sources/base.py`:

```python
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
        """Search for books matching the query. Returns list of results."""
        ...

    @abstractmethod
    def resolve_download_url(self, book: BookResult) -> str | None:
        """Resolve a BookResult to a direct download URL. Returns None on failure."""
        ...
```

- [ ] **Step 2: Commit**

```bash
git add src/gtb/sources/base.py
git commit -m "feat: Source ABC for search backends"
```

---

### Task 4: LibGen Source

**Files:**
- Create: `src/gtb/sources/libgen.py`
- Create: `tests/test_libgen.py`
- Modify: `tests/conftest.py` (add HTML fixtures)

- [ ] **Step 1: Add LibGen HTML fixtures to conftest.py**

Modify `tests/conftest.py`:

```python
"""Shared test fixtures for gethatbook."""
import pytest


LIBGEN_SEARCH_HTML = """
<html><body>
<table width="100%" cellspacing="1" cellpadding="1" rules="rows" class="c" id="table1">
<tr valign="top" bgcolor="#C0C0C0">
  <td>ID</td><td>Author(s)</td><td>Title</td><td>Publisher</td>
  <td>Year</td><td>Pages</td><td>Language</td><td>Size</td>
  <td>Extension</td><td colspan="5">Mirrors</td><td>Edit</td>
</tr>
<tr valign="top">
  <td>12345</td>
  <td>Robert C. Martin</td>
  <td><a id="12345" href="/book/index.php?md5=D41D8CD98F00B204E9800998ECF8427E&amp;id=12345">Clean Code: A Handbook of Agile Software Craftsmanship</a></td>
  <td>Prentice Hall</td>
  <td>2008</td>
  <td>464</td>
  <td>English</td>
  <td>5 Mb</td>
  <td>pdf</td>
  <td><a href="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E">[1]</a></td>
  <td><a href="http://libgen.li/ads.php?md5=D41D8CD98F00B204E9800998ECF8427E">[2]</a></td>
  <td></td><td></td><td></td>
</tr>
<tr valign="top">
  <td>67890</td>
  <td>Martin Fowler</td>
  <td><a id="67890" href="/book/index.php?md5=A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4&amp;id=67890">Refactoring: Improving the Design of Existing Code</a></td>
  <td>Addison-Wesley</td>
  <td>2018</td>
  <td>448</td>
  <td>English</td>
  <td>12 Mb</td>
  <td>epub</td>
  <td><a href="http://library.lol/main/A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4">[1]</a></td>
  <td></td><td></td><td></td><td></td>
</tr>
</table>
</body></html>
"""

LIBGEN_MIRROR_HTML = """
<html><body>
<div id="download">
  <h2><a href="https://download.library.lol/main/d41d8cd9/Robert%20C.%20Martin%20-%20Clean%20Code.pdf">GET</a></h2>
</div>
</body></html>
"""

LIBGEN_SEARCH_NO_RESULTS_HTML = """
<html><body>
<p>Search string must contain minimum 3 characters.</p>
</body></html>
"""

ANNAS_SEARCH_HTML = """
<html><body>
<div class="mb-4">
  <div class="h-[125] flex">
    <div class="flex-col">
      <a href="/md5/D41D8CD98F00B204E9800998ECF8427E" class="text-lg font-bold">
        Clean Code: A Handbook of Agile Software Craftsmanship
      </a>
      <div class="text-sm text-gray-500">Robert C. Martin</div>
      <div class="text-xs">English, 2008, pdf, 5.0MB, 464 pages</div>
    </div>
  </div>
</div>
<div class="mb-4">
  <div class="h-[125] flex">
    <div class="flex-col">
      <a href="/md5/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB" class="text-lg font-bold">
        The Pragmatic Programmer
      </a>
      <div class="text-sm text-gray-500">David Thomas, Andrew Hunt</div>
      <div class="text-xs">English, 2019, epub, 3.2MB, 352 pages</div>
    </div>
  </div>
</div>
</body></html>
"""

ANNAS_DETAIL_HTML = """
<html><body>
<div class="text-3xl font-bold">Clean Code</div>
<div id="md5-panel-downloads">
  <ul class="list-inside">
    <li><a class="js-download-link" href="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E">Libgen.li</a></li>
    <li><a class="js-download-link" href="http://library.lol/fiction/D41D8CD98F00B204E9800998ECF8427E">Libgen.rs Fiction</a></li>
  </ul>
</div>
</body></html>
"""
```

- [ ] **Step 2: Write failing tests for LibGen search**

Create `tests/test_libgen.py`:

```python
from unittest.mock import patch, MagicMock
import httpx
import pytest

from conftest import LIBGEN_SEARCH_HTML, LIBGEN_SEARCH_NO_RESULTS_HTML, LIBGEN_MIRROR_HTML
from gtb.sources.libgen import LibGenSource


@pytest.fixture
def source():
    s = LibGenSource()
    s.base_url = "https://libgen.is"
    return s


class TestSearch:
    def test_parses_results(self, source):
        mock_resp = MagicMock()
        mock_resp.text = LIBGEN_SEARCH_HTML
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch.object(source.client, "get", return_value=mock_resp):
            results = source.search("clean code")

        assert len(results) == 2

        r0 = results[0]
        assert r0.title == "Clean Code: A Handbook of Agile Software Craftsmanship"
        assert r0.author == "Robert C. Martin"
        assert r0.md5 == "D41D8CD98F00B204E9800998ECF8427E"
        assert r0.extension == "pdf"
        assert r0.size_bytes == 5 * 1024 * 1024
        assert r0.year == "2008"
        assert r0.pages == "464"
        assert r0.source == "libgen"
        assert "library.lol" in r0.mirror_url

        r1 = results[1]
        assert r1.title == "Refactoring: Improving the Design of Existing Code"
        assert r1.extension == "epub"
        assert r1.md5 == "A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4"

    def test_returns_empty_on_no_results(self, source):
        mock_resp = MagicMock()
        mock_resp.text = LIBGEN_SEARCH_NO_RESULTS_HTML
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch.object(source.client, "get", return_value=mock_resp):
            results = source.search("x")
        assert results == []

    def test_returns_empty_on_network_error(self, source):
        with patch.object(source.client, "get", side_effect=httpx.ConnectError("fail")):
            results = source.search("test")
        assert results == []


class TestResolveDownload:
    def test_resolves_get_link(self, source):
        mock_resp = MagicMock()
        mock_resp.text = LIBGEN_MIRROR_HTML
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        from gtb.models import BookResult
        book = BookResult(
            title="Clean Code", author="Martin", md5="D41D8CD98F00B204E9800998ECF8427E",
            extension="pdf", size_bytes=5_000_000, language="English", year="2008",
            source="libgen",
            mirror_url="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E",
        )

        with patch.object(source.client, "get", return_value=mock_resp):
            url = source.resolve_download_url(book)

        assert url == "https://download.library.lol/main/d41d8cd9/Robert%20C.%20Martin%20-%20Clean%20Code.pdf"

    def test_returns_none_on_missing_mirror(self, source):
        from gtb.models import BookResult
        book = BookResult(
            title="X", author="A", md5="X", extension="pdf",
            size_bytes=100, language="en", year="2020", source="libgen",
            mirror_url="",
        )
        assert source.resolve_download_url(book) is None
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_libgen.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.sources.libgen'`

- [ ] **Step 4: Implement LibGen source**

Create `src/gtb/sources/libgen.py`:

```python
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

            # MD5 from mirror link
            mirror_url, md5 = "", ""
            for a in cols[9].find_all("a"):
                href = a.get("href", "")
                # library.lol/main/{MD5} pattern
                md5_match = re.search(r"/([a-fA-F0-9]{32})", href)
                if md5_match:
                    mirror_url = href
                    md5 = md5_match.group(1).upper()
                    break
            if not md5:
                # Try md5= query param pattern
                for a in cols[9].find_all("a"):
                    href = a.get("href", "")
                    m = re.search(r"md5=([a-fA-F0-9]{32})", href, re.IGNORECASE)
                    if m:
                        mirror_url = href
                        md5 = m.group(1).upper()
                        break
            if not md5:
                continue

            # Title from last <a> in title column
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
                # Make relative URL absolute
                parsed = urlparse(book.mirror_url)
                return f"{parsed.scheme}://{parsed.netloc}{href}"
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_libgen.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gtb/sources/libgen.py tests/conftest.py tests/test_libgen.py
git commit -m "feat: LibGen search source with mirror page download resolution"
```

---

### Task 5: Anna's Archive Source

**Files:**
- Create: `src/gtb/sources/annas.py`
- Create: `tests/test_annas.py`

- [ ] **Step 1: Write failing tests for Anna's Archive source**

Create `tests/test_annas.py`:

```python
from unittest.mock import patch, MagicMock, call
import httpx
import pytest

from conftest import ANNAS_SEARCH_HTML, ANNAS_DETAIL_HTML, LIBGEN_MIRROR_HTML
from gtb.sources.annas import AnnasArchiveSource


@pytest.fixture
def source():
    s = AnnasArchiveSource()
    s.base_url = "https://annas-archive.gl"
    return s


class TestSearch:
    def test_parses_results(self, source):
        mock_resp = MagicMock()
        mock_resp.text = ANNAS_SEARCH_HTML
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch.object(source.client, "get", return_value=mock_resp):
            results = source.search("clean code")

        assert len(results) == 2

        r0 = results[0]
        assert "Clean Code" in r0.title
        assert r0.md5 == "D41D8CD98F00B204E9800998ECF8427E"
        assert r0.source == "annas"

        r1 = results[1]
        assert "Pragmatic" in r1.title
        assert r1.md5 == "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    def test_returns_empty_on_network_error(self, source):
        with patch.object(source.client, "get", side_effect=httpx.ConnectError("fail")):
            results = source.search("test")
        assert results == []


class TestResolveDownload:
    def test_resolves_via_detail_and_mirror(self, source):
        detail_resp = MagicMock()
        detail_resp.text = ANNAS_DETAIL_HTML
        detail_resp.status_code = 200
        detail_resp.raise_for_status = MagicMock()

        mirror_resp = MagicMock()
        mirror_resp.text = LIBGEN_MIRROR_HTML
        mirror_resp.status_code = 200
        mirror_resp.raise_for_status = MagicMock()

        from gtb.models import BookResult
        book = BookResult(
            title="Clean Code", author="Martin", md5="D41D8CD98F00B204E9800998ECF8427E",
            extension="pdf", size_bytes=5_000_000, language="English", year="2008",
            source="annas",
        )

        with patch.object(source.client, "get", side_effect=[detail_resp, mirror_resp]):
            url = source.resolve_download_url(book)

        assert url is not None
        assert "download.library.lol" in url

    def test_returns_none_when_no_external_links(self, source):
        detail_resp = MagicMock()
        detail_resp.text = "<html><body><div id='md5-panel-downloads'></div></body></html>"
        detail_resp.status_code = 200
        detail_resp.raise_for_status = MagicMock()

        from gtb.models import BookResult
        book = BookResult(
            title="X", author="A", md5="AAAA", extension="pdf",
            size_bytes=100, language="en", year="2020", source="annas",
        )

        with patch.object(source.client, "get", return_value=detail_resp):
            url = source.resolve_download_url(book)
        assert url is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_annas.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.sources.annas'`

- [ ] **Step 3: Implement Anna's Archive source**

Create `src/gtb/sources/annas.py`:

```python
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..models import BookResult
from .base import Source, USER_AGENT

MIRRORS = ["annas-archive.gl", "annas-archive.pk", "annas-archive.gd"]


def _parse_meta_line(text: str) -> dict[str, str]:
    """Parse a line like 'English, 2008, pdf, 5.0MB, 464 pages' into fields."""
    info: dict[str, str] = {
        "language": "", "year": "", "extension": "", "size_bytes": 0, "pages": "",
    }
    parts = [p.strip() for p in text.split(",")]
    for part in parts:
        part_lower = part.lower()
        if re.match(r"^\d{4}$", part):
            info["year"] = part
        elif re.match(r"^[\d.]+\s*(kb|mb|gb|b)$", part_lower):
            info["size_bytes"] = _parse_size(part)
        elif re.match(r"^\d+\s*pages?$", part_lower):
            info["pages"] = re.search(r"\d+", part).group()
        elif part_lower in ("pdf", "epub", "mobi", "azw3", "djvu", "md", "txt", "fb2", "cbr", "cbz", "doc", "docx", "rtf"):
            info["extension"] = part_lower
        elif len(part) > 1 and not part[0].isdigit():
            info["language"] = part
    return info


def _parse_size(s: str) -> int:
    m = re.match(r"([\d.]+)\s*(kb|mb|gb|b)", s.strip(), re.IGNORECASE)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    mult = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
    return int(val * mult.get(unit, 1))


class AnnasArchiveSource(Source):
    name = "annas"

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

        params = {"q": query}
        try:
            resp = self.client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

        return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[BookResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[BookResult] = []

        # Find all links to /md5/{hash} pages
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

            # Walk up to find parent container, then look for author and meta info
            container = link.find_parent("div", class_="mb-4") or link.parent
            author = ""
            meta: dict[str, str] = {}

            if container:
                divs = container.find_all("div")
                for div in divs:
                    text = div.get_text(strip=True)
                    if div == link.parent:
                        continue
                    # Author line: typically the first non-title text div
                    if not author and "," not in text and not re.search(r"\d{4}", text):
                        author = text
                    # Meta line with year, format, size
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

        # Step 1: Fetch detail page to get external download links
        detail_url = f"{self.base_url}/md5/{book.md5}"
        try:
            resp = self.client.get(detail_url)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        panel = soup.find("div", id="md5-panel-downloads")
        if not panel:
            # Fallback: find any js-download-link
            panel = soup

        external_links = panel.find_all("a", class_="js-download-link")
        if not external_links:
            external_links = panel.find_all("a", href=re.compile(r"library\.lol"))

        # Step 2: Try each external link, resolve through mirror page
        for ext_link in external_links:
            mirror_url = ext_link.get("href", "")
            if not mirror_url:
                continue
            try:
                resp2 = self.client.get(mirror_url)
                resp2.raise_for_status()
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_annas.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gtb/sources/annas.py tests/test_annas.py
git commit -m "feat: Anna's Archive search source with two-hop download resolution"
```

---

### Task 6: Search Orchestrator

**Files:**
- Create: `src/gtb/search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write failing tests for parallel search**

Create `tests/test_search.py`:

```python
from gtb.models import BookResult
from gtb.search import parallel_search
from gtb.sources.base import Source


class FakeSourceA(Source):
    name = "fake_a"

    def search(self, query):
        return [
            BookResult(
                title="Book A", author="Auth A", md5="AAAA1111AAAA1111AAAA1111AAAA1111",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_a", mirror_url="http://example.com/a",
            ),
            BookResult(
                title="Shared Book", author="Shared", md5="SHARED11SHARED11SHARED11SHARED11",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_a", mirror_url="http://example.com/shared_a",
            ),
        ]

    def resolve_download_url(self, book):
        return "http://example.com/download_a"


class FakeSourceB(Source):
    name = "fake_b"

    def search(self, query):
        return [
            BookResult(
                title="Book B", author="Auth B", md5="BBBB2222BBBB2222BBBB2222BBBB2222",
                extension="epub", size_bytes=1_000_000, language="en", year="2021",
                source="fake_b",
            ),
            BookResult(
                title="Shared Book", author="Shared", md5="SHARED11SHARED11SHARED11SHARED11",
                extension="pdf", size_bytes=5_000_000, language="en", year="2020",
                source="fake_b", mirror_url="http://example.com/shared_b",
            ),
        ]

    def resolve_download_url(self, book):
        return "http://example.com/download_b"


class FakeSourceFail(Source):
    name = "fail"

    def search(self, query):
        raise ConnectionError("boom")

    def resolve_download_url(self, book):
        return None


def test_parallel_search_merges_results():
    sources = [FakeSourceA(), FakeSourceB()]
    results = parallel_search("test", sources)
    # 2 unique from A + 1 unique from B = 3 (shared deduped)
    assert len(results) == 3
    md5s = {r.md5 for r in results}
    assert "AAAA1111AAAA1111AAAA1111AAAA1111" in md5s
    assert "BBBB2222BBBB2222BBBB2222BBBB2222" in md5s
    assert "SHARED11SHARED11SHARED11SHARED11" in md5s


def test_parallel_search_dedupes_by_md5():
    sources = [FakeSourceA(), FakeSourceB()]
    results = parallel_search("test", sources)
    md5_counts = {}
    for r in results:
        md5_counts[r.md5] = md5_counts.get(r.md5, 0) + 1
    assert md5_counts["SHARED11SHARED11SHARED11SHARED11"] == 1


def test_parallel_search_survives_source_failure():
    sources = [FakeSourceA(), FakeSourceFail()]
    results = parallel_search("test", sources)
    assert len(results) == 2  # only A's results
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_search.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.search'`

- [ ] **Step 3: Implement search orchestrator**

Create `src/gtb/search.py`:

```python
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import BookResult
from .sources.base import Source


def parallel_search(
    query: str,
    sources: list[Source],
    timeout: float = 60,
) -> list[BookResult]:
    """Search all sources in parallel, deduplicate by MD5."""
    all_results: list[BookResult] = []

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = {pool.submit(_safe_search, src, query): src for src in sources}
        for future in as_completed(futures, timeout=timeout):
            src = futures[future]
            try:
                results = future.result()
                print(f"  [{src.name}] found {len(results)} results", file=sys.stderr)
                all_results.extend(results)
            except Exception as e:
                print(f"  [{src.name}] failed: {e}", file=sys.stderr)

    return _dedupe(all_results)


def _safe_search(source: Source, query: str) -> list[BookResult]:
    return source.search(query)


def _dedupe(results: list[BookResult]) -> list[BookResult]:
    """Keep first occurrence per MD5 (preserves source priority order)."""
    seen: set[str] = set()
    deduped: list[BookResult] = []
    for r in results:
        key = r.md5.upper()
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_search.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gtb/search.py tests/test_search.py
git commit -m "feat: parallel search orchestrator with MD5 dedup"
```

---

### Task 7: Download Manager

**Files:**
- Create: `src/gtb/download.py`
- Create: `tests/test_download.py`

- [ ] **Step 1: Write failing tests for download manager**

Create `tests/test_download.py`:

```python
import os
import tempfile
from unittest.mock import patch, MagicMock

import httpx
import pytest

from gtb.download import download_file


def test_download_saves_file():
    fake_content = b"fake pdf content here"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(fake_content))}
    mock_resp.iter_bytes = MagicMock(return_value=iter([fake_content]))
    mock_resp.raise_for_status = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("gtb.download.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.stream.return_value = mock_resp

            path = download_file(
                url="http://example.com/book.pdf",
                filename="test_book.pdf",
                dest_dir=tmpdir,
            )

        assert os.path.exists(path)
        assert path == os.path.join(tmpdir, "test_book.pdf")
        with open(path, "rb") as f:
            assert f.read() == fake_content


def test_download_returns_none_on_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("gtb.download.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.stream.side_effect = httpx.ConnectError("fail")

            path = download_file(
                url="http://example.com/book.pdf",
                filename="test.pdf",
                dest_dir=tmpdir,
            )

        assert path is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_download.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.download'`

- [ ] **Step 3: Implement download manager**

Create `src/gtb/download.py`:

```python
from __future__ import annotations

import os
import sys

import httpx

from .sources.base import USER_AGENT


def download_file(
    url: str,
    filename: str,
    dest_dir: str = ".",
    timeout: float = 300,
) -> str | None:
    """Download a file from URL. Returns the saved path, or None on failure."""
    dest = os.path.join(dest_dir, _sanitize_filename(filename))

    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()

                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        _print_progress(downloaded, total)

        print("", file=sys.stderr)  # newline after progress
        return dest

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        # Clean up partial file
        if os.path.exists(dest):
            os.remove(dest)
        return None


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters unsafe for filenames."""
    keep = " .-_()"
    return "".join(c if c.isalnum() or c in keep else "_" for c in name).strip()


def _print_progress(downloaded: int, total: int) -> None:
    if total > 0:
        pct = downloaded * 100 // total
        bar = "#" * (pct // 2) + "-" * (50 - pct // 2)
        print(f"\r  [{bar}] {pct}% ({downloaded // 1024}KB/{total // 1024}KB)", end="", file=sys.stderr)
    else:
        print(f"\r  {downloaded // 1024}KB downloaded", end="", file=sys.stderr)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_download.py -v
```

Expected: all 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gtb/download.py tests/test_download.py
git commit -m "feat: download manager with progress display"
```

---

### Task 8: CLI Entry Point

**Files:**
- Create: `src/gtb/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI**

Create `tests/test_cli.py`:

```python
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from gtb.cli import main
from gtb.models import BookResult, FormatType


@pytest.fixture
def runner():
    return CliRunner()


def _fake_book():
    return BookResult(
        title="Clean Code", author="Robert Martin",
        md5="D41D8CD98F00B204E9800998ECF8427E",
        extension="pdf", size_bytes=5_000_000,
        language="English", year="2008", source="libgen",
        mirror_url="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E",
        pages="464",
    )


import pytest


def test_search_and_download(runner):
    book = _fake_book()

    with patch("gtb.cli.parallel_search", return_value=[book]) as mock_search, \
         patch("gtb.cli.select_best", return_value=book), \
         patch("gtb.cli._resolve_and_download", return_value="/tmp/Clean_Code.pdf"):
        result = runner.invoke(main, ["Clean Code"])

    assert result.exit_code == 0
    assert "Clean Code" in result.output
    mock_search.assert_called_once()


def test_no_results(runner):
    with patch("gtb.cli.parallel_search", return_value=[]):
        result = runner.invoke(main, ["nonexistent book xyz"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_requires_query(runner):
    result = runner.invoke(main, [])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'gtb.cli'`

- [ ] **Step 3: Implement CLI**

Create `src/gtb/cli.py`:

```python
from __future__ import annotations

import os
import sys

import click

from .download import download_file
from .models import BookResult
from .ranking import select_best
from .search import parallel_search
from .sources import ALL_SOURCES


def _resolve_and_download(book: BookResult, sources: list, dest_dir: str) -> str | None:
    """Try each source to resolve a download URL, then download."""
    # Build a map of source instances by name
    source_map = {s.name: s for s in sources}

    # Try the book's own source first, then others
    order = [book.source] + [s.name for s in sources if s.name != book.source]
    for name in order:
        src = source_map.get(name)
        if not src:
            continue
        click.echo(f"  Resolving download via {name}...", err=True)
        url = src.resolve_download_url(book)
        if url:
            filename = f"{book.title[:80]}.{book.extension}"
            click.echo(f"  Downloading from {name}...", err=True)
            return download_file(url, filename, dest_dir=dest_dir)

    return None


@click.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--format", "-f", "fmt", default=None, help="Force format: pdf, epub, md, mobi")
@click.option("--output", "-o", "dest_dir", default=".", help="Download directory (default: current)")
def main(query: tuple[str, ...], fmt: str | None, dest_dir: str) -> None:
    """Search and download ebooks. Usage: gtb 'book title'"""
    query_str = " ".join(query)
    click.echo(f"Searching for: {query_str}", err=True)

    sources = [cls() for cls in ALL_SOURCES]
    results = parallel_search(query_str, sources)

    if not results:
        click.echo("No results found across any source.")
        return

    # Filter by format if specified
    if fmt:
        fmt_lower = fmt.lower().strip(".")
        results = [r for r in results if r.extension.lower() == fmt_lower]
        if not results:
            click.echo(f"No results found with format '{fmt}'.")
            return

    best = select_best(results)
    if not best:
        click.echo("No suitable results found.")
        return

    click.echo(f"\nBest match:", err=True)
    click.echo(f"  Title:  {best.title}")
    click.echo(f"  Author: {best.author}")
    click.echo(f"  Format: {best.extension} ({best.format_type.name})")
    click.echo(f"  Size:   {best.size_display}")
    click.echo(f"  Year:   {best.year}")
    click.echo(f"  Source: {best.source}")
    click.echo(f"  MD5:    {best.md5}")
    click.echo()

    path = _resolve_and_download(best, sources, dest_dir)
    if path:
        click.echo(f"Saved to: {path}")
    else:
        click.echo("Failed to download. Try a different result or source.", err=True)
        # Show top 5 alternatives
        click.echo("\nOther results:", err=True)
        for i, r in enumerate(sorted(results, key=lambda b: (b.format_type.value, b.size_bytes))[:5]):
            click.echo(f"  {i+1}. [{r.extension}] {r.title} - {r.author} ({r.size_display}, {r.source})", err=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS (approximately 20 tests across all files).

- [ ] **Step 6: Verify CLI installs and runs**

```bash
pip install -e ".[dev]"
gtb --help
```

Expected: prints help text showing usage, options `--format` and `--output`.

- [ ] **Step 7: Commit**

```bash
git add src/gtb/cli.py tests/test_cli.py
git commit -m "feat: CLI entry point with auto-select and download"
```

---

### Task 9: Fix Imports and Integration Smoke Test

**Files:**
- Modify: `src/gtb/sources/__init__.py` (verify imports work)
- Possibly fix any import issues surfaced by full test run

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v --tb=short
```

Fix any import errors or test failures. Common issues:
- `conftest.py` fixtures not found: ensure `tests/` has no `__init__.py` (pytest discovers conftest automatically in rootdir)
- Circular imports in sources/__init__.py: defer imports if needed

- [ ] **Step 2: Verify end-to-end with a dry run**

```bash
gtb "Clean Code" --help
gtb "Python" 2>&1 | head -20
```

The second command will attempt a real network search. Verify it either:
- Returns results and attempts download (if network is available and mirrors respond)
- Fails gracefully with "No results found" or connection error (if firewalled)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: gethatbook v0.1.0 — aggregate ebook search CLI"
```
