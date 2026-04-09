from __future__ import annotations

import os
import sys

import httpx

from .sources.base import USER_AGENT


def download_file(
    url: str,
    filename: str,
    dest_dir: str = ".",
    timeout: float = 300,
) -> str | None:
    """Download a file from URL. Returns the saved path, or None on failure."""
    dest = os.path.join(dest_dir, _sanitize_filename(filename))

    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        ) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()

                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        _print_progress(downloaded, total)

        print("", file=sys.stderr)
        return dest

    except (httpx.RequestError, httpx.HTTPStatusError, OSError) as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        if os.path.exists(dest):
            os.remove(dest)
        return None


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters unsafe for filenames."""
    keep = " .-_()"
    result = "".join(c if c.isalnum() or c in keep else "_" for c in name).strip()
    # Guard against empty, dot-only, or whitespace-only results
    if not result or result.replace(".", "") == "":
        return "download"
    return result


def _print_progress(downloaded: int, total: int) -> None:
    if total > 0:
        pct = downloaded * 100 // total
        bar = "#" * (pct // 2) + "-" * (50 - pct // 2)
        print(f"\r  [{bar}] {pct}% ({downloaded // 1024}KB/{total // 1024}KB)", end="", file=sys.stderr)
    else:
        print(f"\r  {downloaded // 1024}KB downloaded", end="", file=sys.stderr)
