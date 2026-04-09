import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from gtb.cli import main
from gtb.models import BookResult, FormatType


@pytest.fixture
def runner():
    return CliRunner()


def _fake_book(ext="pdf", size=5_000_000, md5="D41D8CD98F00B204E9800998ECF8427E"):
    return BookResult(
        title="Clean Code", author="Robert Martin",
        md5=md5,
        extension=ext, size_bytes=size,
        language="English", year="2008", source="libgen",
        mirror_url="http://library.lol/main/" + md5,
        pages="464",
    )


def test_search_and_download(runner):
    book = _fake_book()

    with patch("gtb.cli.parallel_search", return_value=[book]) as mock_search, \
         patch("gtb.cli._resolve_and_download", return_value="/tmp/Clean_Code.pdf"):
        result = runner.invoke(main, ["Clean Code"])

    assert result.exit_code == 0
    assert "Clean Code" in result.output
    mock_search.assert_called_once()


def test_no_results_exits_1(runner):
    with patch("gtb.cli.parallel_search", return_value=[]):
        result = runner.invoke(main, ["nonexistent book xyz"])

    assert result.exit_code == 1
    assert "No results" in result.output


def test_requires_query(runner):
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_format_filter(runner):
    pdf_book = _fake_book("pdf", md5="AAAA" * 8)
    epub_book = _fake_book("epub", md5="BBBB" * 8)

    with patch("gtb.cli.parallel_search", return_value=[pdf_book, epub_book]), \
         patch("gtb.cli._resolve_and_download", return_value="/tmp/book.epub"):
        result = runner.invoke(main, ["test", "--format", "epub"])

    assert result.exit_code == 0
    # Should only show epub, not pdf
    assert "epub" in result.output.lower()


def test_format_filter_no_match_exits_1(runner):
    pdf_book = _fake_book("pdf")

    with patch("gtb.cli.parallel_search", return_value=[pdf_book]):
        result = runner.invoke(main, ["test", "--format", "djvu"])

    assert result.exit_code == 1
    assert "No results found with format" in result.output


def test_list_mode(runner):
    books = [_fake_book("pdf", md5="AAAA" * 8), _fake_book("epub", md5="BBBB" * 8)]

    with patch("gtb.cli.parallel_search", return_value=books):
        result = runner.invoke(main, ["test", "--list"])

    assert result.exit_code == 0
    assert "2 results" in result.output
    assert "pdf" in result.output.lower()
    assert "epub" in result.output.lower()


def test_auto_fallback_on_download_failure(runner):
    book1 = _fake_book("pdf", md5="AAAA" * 8)
    book2 = _fake_book("epub", md5="BBBB" * 8)

    call_count = 0

    def fake_resolve(book, sources, dest_dir):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None  # first attempt fails
        return "/tmp/book.epub"  # second succeeds

    with patch("gtb.cli.parallel_search", return_value=[book1, book2]), \
         patch("gtb.cli._resolve_and_download", side_effect=fake_resolve):
        result = runner.invoke(main, ["test"])

    assert result.exit_code == 0
    assert call_count == 2  # tried both
    assert "Saved to:" in result.output


def test_all_downloads_fail_exits_1(runner):
    book = _fake_book()

    with patch("gtb.cli.parallel_search", return_value=[book]), \
         patch("gtb.cli._resolve_and_download", return_value=None):
        result = runner.invoke(main, ["test"])

    assert result.exit_code == 1
    assert "All download attempts failed" in result.output


def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
