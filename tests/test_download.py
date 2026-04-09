import os
import tempfile
from unittest.mock import patch, MagicMock

import httpx
import pytest

from gtb.download import download_file, _sanitize_filename


class TestDownloadFile:
    def test_saves_file(self):
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

    def test_returns_none_on_network_failure(self):
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

    def test_returns_none_on_bad_dest_dir(self):
        with patch("gtb.download.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.iter_bytes = MagicMock(return_value=iter([b"data"]))
            mock_resp.raise_for_status = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            client = MockClient.return_value.__enter__.return_value
            client.stream.return_value = mock_resp

            path = download_file(
                url="http://example.com/book.pdf",
                filename="test.pdf",
                dest_dir="/nonexistent/path/xyz",
            )
        assert path is None


class TestSanitizeFilename:
    def test_normal_filename(self):
        assert _sanitize_filename("Clean Code.pdf") == "Clean Code.pdf"

    def test_special_characters(self):
        result = _sanitize_filename("Book: A/B <C> \"D\".pdf")
        assert "/" not in result
        assert "<" not in result

    def test_empty_string(self):
        assert _sanitize_filename("") == "download"

    def test_whitespace_only(self):
        assert _sanitize_filename("   ") == "download"

    def test_dots_only(self):
        assert _sanitize_filename("...") == "download"

    def test_unicode_preserved(self):
        result = _sanitize_filename("Python编程.pdf")
        assert result != "download"

    def test_long_filename_truncated(self):
        long_name = "A" * 300 + ".pdf"
        result = _sanitize_filename(long_name)
        assert len(result.encode("utf-8")) <= 250
        assert result.endswith(".pdf")

    def test_long_filename_no_ext(self):
        result = _sanitize_filename("A" * 300)
        assert len(result.encode("utf-8")) <= 250

    def test_path_traversal_neutralized(self):
        result = _sanitize_filename("../../../etc/passwd")
        assert "/" not in result
