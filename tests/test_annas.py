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
