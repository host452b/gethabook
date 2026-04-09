from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import BookResult
from .sources.base import Source


def parallel_search(
    query: str,
    sources: list[Source],
    timeout: float = 60,
) -> list[BookResult]:
    """Search all sources in parallel, deduplicate by MD5."""
    all_results: list[BookResult] = []

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = {pool.submit(_safe_search, src, query): src for src in sources}
        for future in as_completed(futures, timeout=timeout):
            src = futures[future]
            try:
                results = future.result()
                print(f"  [{src.name}] found {len(results)} results", file=sys.stderr)
                all_results.extend(results)
            except Exception as e:
                print(f"  [{src.name}] failed: {e}", file=sys.stderr)

    return _dedupe(all_results)


def _safe_search(source: Source, query: str) -> list[BookResult]:
    return source.search(query)


def _dedupe(results: list[BookResult]) -> list[BookResult]:
    """Keep first occurrence per MD5."""
    seen: set[str] = set()
    deduped: list[BookResult] = []
    for r in results:
        key = r.md5.upper()
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped
