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
    scanned = _book("pdf", 200, "300")
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
