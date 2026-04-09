from __future__ import annotations

from .models import BookResult


def score_book(book: BookResult) -> tuple[int, int]:
    """Lower score = better. Sorts by (format_priority, file_size)."""
    return (book.format_type.value, book.size_bytes)


def select_best(books: list[BookResult]) -> BookResult | None:
    if not books:
        return None
    return min(books, key=score_book)
