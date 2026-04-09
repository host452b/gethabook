from gtb.models import BookResult, FormatType
from gtb.ranking import score_book, select_best, set_query


def _book(ext: str, size_mb: float, pages: str = "", title: str = "Test") -> BookResult:
    return BookResult(
        title=title, author="A", md5="X", extension=ext,
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


def test_title_relevance_prefers_matching_title():
    set_query("Godot Multiplayer Games")
    relevant = _book("pdf", 10, title="The Essential Guide to Creating Multiplayer Games with Godot 4.0")
    irrelevant = _book("pdf", 1, title="Passive Income Secrets")
    relevant.md5 = "RELEVANT"
    irrelevant.md5 = "IRRELEVANT"

    assert score_book(relevant) < score_book(irrelevant)

    best = select_best([irrelevant, relevant])
    assert best.md5 == "RELEVANT"
    set_query("")  # cleanup


def test_relevance_beats_smaller_size():
    set_query("Clean Code")
    match = _book("pdf", 20, title="Clean Code: A Handbook of Agile Software")
    tiny = _book("pdf", 0.3, title="Random Unrelated Book")
    match.md5 = "MATCH"
    tiny.md5 = "TINY"

    best = select_best([tiny, match])
    assert best.md5 == "MATCH"
    set_query("")
