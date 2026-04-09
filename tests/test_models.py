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
