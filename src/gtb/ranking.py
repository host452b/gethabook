from __future__ import annotations

import re

from .models import BookResult


def _title_relevance(title: str, query: str) -> float:
    """Score 0.0-1.0: fraction of query words found in title. Higher is better."""
    query_words = set(re.findall(r"\w+", query.lower()))
    title_words = set(re.findall(r"\w+", title.lower()))
    if not query_words:
        return 0.0
    return len(query_words & title_words) / len(query_words)


# Global query set by CLI before ranking
_current_query: str = ""


def set_query(query: str) -> None:
    global _current_query
    _current_query = query


def score_book(book: BookResult) -> tuple[float, int, int]:
    """Lower score = better.

    Sorting key: (1 - title_relevance, format_priority, file_size).
    Title relevance is inverted so higher relevance sorts first.
    """
    relevance = _title_relevance(book.title, _current_query) if _current_query else 0.5
    return (round(1.0 - relevance, 2), book.format_type.value, book.size_bytes)


def select_best(books: list[BookResult]) -> BookResult | None:
    if not books:
        return None
    return min(books, key=score_book)
