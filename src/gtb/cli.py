from __future__ import annotations

import sys

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


def _print_book(book: BookResult, prefix: str = "") -> None:
    """Print book info to stderr consistently."""
    click.echo(f"{prefix}Title:  {book.title}", err=True)
    click.echo(f"{prefix}Author: {book.author}", err=True)
    click.echo(f"{prefix}Format: {book.extension} ({book.format_type.name})", err=True)
    click.echo(f"{prefix}Size:   {book.size_display}", err=True)
    click.echo(f"{prefix}Year:   {book.year}", err=True)
    click.echo(f"{prefix}Source: {book.source}", err=True)
    click.echo(f"{prefix}MD5:    {book.md5}", err=True)


@click.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--format", "-f", "fmt", default=None, help="Force format: pdf, epub, md, mobi")
@click.option("--output", "-o", "dest_dir", default=".", help="Download directory (default: current)")
@click.option("--list", "-l", "list_mode", is_flag=True, help="List results without downloading")
@click.version_option(package_name="gethatbook")
def main(query: tuple[str, ...], fmt: str | None, dest_dir: str, list_mode: bool) -> None:
    """Search and download ebooks. Usage: gtb 'book title'"""
    query_str = " ".join(query)
    click.echo(f"Searching for: {query_str}", err=True)

    sources = [cls() for cls in ALL_SOURCES]
    try:
        results = parallel_search(query_str, sources)

        if not results:
            click.echo("No results found across any source.", err=True)
            sys.exit(1)

        # Filter by format if specified
        if fmt:
            fmt_lower = fmt.lower().strip(".")
            results = [r for r in results if r.extension.lower() == fmt_lower]
            if not results:
                click.echo(f"No results found with format '{fmt}'.", err=True)
                sys.exit(1)

        # Sort by ranking
        ranked = sorted(results, key=lambda b: (b.format_type.value, b.size_bytes))

        # List mode: show all results and exit
        if list_mode:
            click.echo(f"\n{len(ranked)} results:", err=True)
            for i, r in enumerate(ranked):
                click.echo(
                    f"  {i+1}. [{r.extension}] {r.title} - {r.author} "
                    f"({r.size_display}, {r.source})",
                    err=True,
                )
            return

        # Auto mode: try downloading from best to worst
        for attempt, book in enumerate(ranked):
            if attempt == 0:
                click.echo(f"\nBest match:", err=True)
            else:
                click.echo(f"\nTrying next result ({attempt + 1}/{len(ranked)}):", err=True)
            _print_book(book, prefix="  ")
            click.echo("", err=True)

            path = _resolve_and_download(book, sources, dest_dir)
            if path:
                click.echo(f"Saved to: {path}", err=True)
                return

            if attempt < len(ranked) - 1:
                click.echo("  Download failed, trying next...", err=True)

        click.echo("All download attempts failed.", err=True)
        sys.exit(1)

    finally:
        for src in sources:
            src.close()


if __name__ == "__main__":
    main()
