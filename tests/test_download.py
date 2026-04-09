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
