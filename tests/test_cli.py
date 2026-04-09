import pytest
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
