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
