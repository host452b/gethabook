from unittest.mock import patch, MagicMock
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
        assert r0.extension == "pdf"
        assert r0.year == "2008"
        assert r0.size_bytes > 0

        r1 = results[1]
        assert "Pragmatic" in r1.title
        assert r1.md5 == "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        assert r1.extension == "epub"

    def test_returns_empty_on_network_error(self, source):
        with patch.object(source.client, "get", side_effect=httpx.ConnectError("fail")):
            results = source.search("test")
        assert results == []


class TestResolveDownload:
    def test_resolves_via_libgen_link(self, source):
        """Detail page has libgen.is link → follow to mirror → GET link."""
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

    def test_skips_fast_slow_download_links(self, source):
        """Should not try relative /fast_download or /slow_download URLs."""
        detail_html = """<html><body>
        <div id="md5-panel-downloads">
          <a class="js-download-link" href="/fast_download/abc/0/0">Fast</a>
          <a href="/slow_download/abc/0/0">Slow</a>
        </div>
        </body></html>"""

        detail_resp = MagicMock()
        detail_resp.text = detail_html
        detail_resp.status_code = 200
        detail_resp.raise_for_status = MagicMock()

        # The fallback (strategy 4) will try constructing a libgen URL
        fallback_resp = MagicMock()
        fallback_resp.text = "<html><body>no GET link</body></html>"
        fallback_resp.status_code = 200
        fallback_resp.raise_for_status = MagicMock()

        from gtb.models import BookResult
        book = BookResult(
            title="X", author="A", md5="AABBCCDDAABBCCDDAABBCCDDAABBCCDD",
            extension="pdf", size_bytes=100, language="en", year="2020",
            source="annas",
        )

        with patch.object(source.client, "get", side_effect=[detail_resp, fallback_resp]):
            url = source.resolve_download_url(book)

        # Should not crash on relative URLs, returns None if no GET found
        assert url is None
