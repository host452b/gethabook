# gethatbook (gtb)

A command-line tool that aggregates ebook search across multiple open sources, auto-selects the best result by format quality and title relevance, and downloads it — all in one command.

[中文文档](README_CN.md)

## Features

- **Multi-source parallel search** — Searches multiple ebook sources simultaneously, merges results, deduplicates by MD5
- **Smart auto-selection** — Ranks results by title relevance, format priority (`pdf(text) > md > epub > mobi > pdf(scanned)`), and file size
- **Scanned PDF detection** — Heuristic detection of scanned/OCR PDFs based on bytes-per-page ratio, automatically deprioritized
- **Auto-fallback** — If download fails, automatically tries the next-best result until one succeeds
- **Rate limiting & retry** — Polite delay between requests, automatic retry with backoff on failure
- **Browse mode** — `--list` flag to preview all results without downloading
- **Format filter** — `--format pdf` to restrict results to a specific format
- **Progress bar** — Real-time download progress in terminal

## Installation

```bash
git clone https://github.com/host452b/gethabook.git
cd gethabook
pip install -e .
```

### Dependencies

- Python 3.10+
- httpx — HTTP client
- beautifulsoup4 + lxml — HTML parsing
- click — CLI framework

All dependencies are installed automatically via `pip install`.

## Usage

### Basic: search and download

```bash
gtb "Clean Code"
```

Searches all sources, picks the best text PDF, downloads to current directory.

### Specify format

```bash
gtb "Clean Code" --format epub
```

### Browse results without downloading

```bash
gtb "Design Patterns" --list
```

Output:
```
Searching for: Design Patterns

62 results:
  1. [pdf] Design Patterns: Elements of Reusable Object-Oriented Software (5.2 MB, source-a)
  2. [epub] Design Patterns: Elements of Reusable Object-Oriented Software (1.8 MB, source-b)
  3. [pdf] Head First Design Patterns (12.3 MB, source-b)
  ...
```

### Download to a specific directory

```bash
gtb "The Art of Game Design" --output ~/Books/
```

### Check version

```bash
gtb --version
```

## How It Works

```
gtb "book title"
       │
       ├── 1. Parallel search across multiple sources
       │
       ├── 2. Deduplicate by MD5 hash
       │
       ├── 3. Rank results:
       │      ① Title relevance (query word overlap)
       │      ② Format priority (text PDF > md > epub > scanned PDF)
       │      ③ File size (smaller preferred within same tier)
       │
       ├── 4. Resolve download URL via mirror pages
       │
       └── 5. Download (auto-fallback on failure → try next result)
```

## Format Priority

| Priority | Format | Detection |
|----------|--------|-----------|
| 1 (best) | PDF (text) | Default for PDF, unless flagged as scanned |
| 2 | Markdown | `.md` extension |
| 3 | EPUB | `.epub` extension |
| 4 | MOBI/AZW3 | `.mobi` / `.azw3` extension |
| 5 | PDF (scanned) | Heuristic: >80KB/page or >100MB without page info |
| 6 | Other | Everything else (djvu, cbr, etc.) |

## Project Structure

```
src/gtb/
├── cli.py              # CLI entry point
├── models.py           # BookResult dataclass, FormatType enum
├── ranking.py          # Title relevance + format scoring
├── search.py           # Parallel search orchestrator
├── download.py         # Stream download with progress
└── sources/
    ├── base.py         # Source ABC, shared HTTP client with retry/rate-limit
    ├── libgen.py       # Source A: search + mirror page resolution
    └── annas.py        # Source B: search + two-hop download resolution
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

48 tests covering models, ranking, search orchestrator, download manager, CLI, and both source backends (all with mocked HTTP — no network required).

## Disclaimer

This project is provided **for educational and testing purposes only**. Users are solely responsible for complying with all applicable laws and regulations in their jurisdiction. **Any use of this tool for copyright infringement, piracy, or other illegal activities is strictly prohibited.** The authors assume no liability for misuse of this software. If you find a book useful, please support the authors by purchasing a legitimate copy.

## License

MIT
