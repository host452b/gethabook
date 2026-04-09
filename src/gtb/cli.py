from __future__ import annotations

import click

from .download import download_file
from .models import BookResult
from .ranking import select_best
from .search import parallel_search
from .sources import ALL_SOURCES


def _resolve_and_download(book: BookResult, sources: list, dest_dir: str) -> str | None:
    """Try each source to resolve a download URL, then download."""
    source_map = {s.name: s for s in sources}

    order = [book.source] + [s.name for s in sources if s.name != book.source]
    for name in order:
        src = source_map.get(name)
        if not src:
            continue
        click.echo(f"  Resolving download via {name}...", err=True)
        url = src.resolve_download_url(book)
        if url:
            filename = f"{book.title[:80]}.{book.extension}"
            click.echo(f"  Downloading from {name}...", err=True)
            return download_file(url, filename, dest_dir=dest_dir)

    return None


@click.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--format", "-f", "fmt", default=None, help="Force format: pdf, epub, md, mobi")
@click.option("--output", "-o", "dest_dir", default=".", help="Download directory (default: current)")
def main(query: tuple[str, ...], fmt: str | None, dest_dir: str) -> None:
    """Search and download ebooks. Usage: gtb 'book title'"""
    query_str = " ".join(query)
    click.echo(f"Searching for: {query_str}", err=True)

    sources = [cls() for cls in ALL_SOURCES]
    results = parallel_search(query_str, sources)

    if not results:
        click.echo("No results found across any source.")
        return

    # Filter by format if specified
    if fmt:
        fmt_lower = fmt.lower().strip(".")
        results = [r for r in results if r.extension.lower() == fmt_lower]
        if not results:
            click.echo(f"No results found with format '{fmt}'.")
            return

    best = select_best(results)
    if not best:
        click.echo("No suitable results found.")
        return

    click.echo(f"\nBest match:", err=True)
    click.echo(f"  Title:  {best.title}")
    click.echo(f"  Author: {best.author}")
    click.echo(f"  Format: {best.extension} ({best.format_type.name})")
    click.echo(f"  Size:   {best.size_display}")
    click.echo(f"  Year:   {best.year}")
    click.echo(f"  Source: {best.source}")
    click.echo(f"  MD5:    {best.md5}")
    click.echo()

    path = _resolve_and_download(best, sources, dest_dir)
    if path:
        click.echo(f"Saved to: {path}")
    else:
        click.echo("Failed to download. Try a different result or source.", err=True)
        click.echo("\nOther results:", err=True)
        for i, r in enumerate(sorted(results, key=lambda b: (b.format_type.value, b.size_bytes))[:5]):
            click.echo(f"  {i+1}. [{r.extension}] {r.title} - {r.author} ({r.size_display}, {r.source})", err=True)


if __name__ == "__main__":
    main()
