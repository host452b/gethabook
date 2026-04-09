# gethatbook (gtb)

A command-line tool that aggregates ebook search across multiple sources (Anna's Archive, Library Genesis), auto-selects the best result by format quality and title relevance, and downloads it — all in one command.

## Features

- **Multi-source parallel search** — Searches Anna's Archive and LibGen simultaneously, merges results, deduplicates by MD5
- **Smart auto-selection** — Ranks results by title relevance → format priority (`pdf(text) > md > epub > mobi > pdf(scanned)`) → file size
- **Scanned PDF detection** — Heuristic detection of scanned/OCR PDFs based on bytes-per-page ratio, automatically deprioritized
- **Auto-fallback** — If download fails, automatically tries the next-best result until one succeeds
- **Rate limiting & retry** — Polite 0.5s delay between requests, automatic retry with backoff on failure
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
- [httpx](https://www.python-httpx.org/) — HTTP client
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) — HTML parsing
- [click](https://click.palletsprojects.com/) — CLI framework

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
gtb "Godot 4 Game Development Cookbook" --list
```

Output:
```
Searching for: Godot 4 Game Development Cookbook
  [annas] found 46 results
  [libgen] found 0 results

46 results:
  1. [pdf] Godot 4 Game Development Cookbook: Over 50 solid recipes... (9.0 MB, annas)
  2. [pdf] Godot 4 Game Development Cookbook: Over 50 solid recipes... (25.1 MB, annas)
  3. [epub] Godot 4 Game Development Cookbook: Over 50 solid recipes... (20.1 MB, annas)
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
       ├── 1. Parallel search ──┬── Anna's Archive (annas-archive.gl)
       │                        └── Library Genesis (libgen.is)
       │
       ├── 2. Deduplicate by MD5 hash
       │
       ├── 3. Rank results:
       │      ① Title relevance (query word overlap)
       │      ② Format priority (text PDF > md > epub > scanned PDF)
       │      ③ File size (smaller preferred within same tier)
       │
       ├── 4. Resolve download URL:
       │      Anna's Archive → detail page → libgen mirror → GET link
       │      LibGen → mirror page (library.lol) → GET link
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
├── cli.py              # Click CLI entry point
├── models.py           # BookResult dataclass, FormatType enum
├── ranking.py          # Title relevance + format scoring
├── search.py           # Parallel search orchestrator (ThreadPoolExecutor)
├── download.py         # Stream download with progress
└── sources/
    ├── base.py         # Source ABC, shared HTTP client with retry/rate-limit
    ├── libgen.py       # LibGen search + mirror page resolution
    └── annas.py        # Anna's Archive search + two-hop download resolution
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

48 tests covering models, ranking, search orchestrator, download manager, CLI, and both source backends (all with mocked HTTP — no network required).

## Limitations

- **Anna's Archive anti-bot protection** — Cloudflare/DDoS-Guard may block requests in some environments. The tool uses a realistic User-Agent and rate limiting to mitigate this.
- **LibGen mirror availability** — Mirror domains change frequently. If downloads fail, it's likely a network/DNS issue. VPN may help.
- **No captcha solving** — Anna's Archive "slow download" links require captcha and cannot be automated. The tool uses external LibGen mirror links instead.
- **Metadata accuracy** — Scanned PDF detection is heuristic-based and may occasionally misclassify.

## License

MIT

---

# gethatbook (gtb) 中文文档

一个命令行电子书聚合搜索下载工具。跨多个数据源（Anna's Archive、Library Genesis）并行搜索，按格式质量和标题相关性自动选择最佳结果并下载 —— 一条命令搞定。

## 功能特性

- **多源并行搜索** — 同时搜索 Anna's Archive 和 LibGen，合并结果，按 MD5 去重
- **智能自动选择** — 按标题相关性 → 格式优先级（`文本PDF > md > epub > mobi > 扫描PDF`）→ 文件大小排序
- **扫描版 PDF 检测** — 基于每页字节数启发式检测扫描/OCR版PDF，自动降低优先级
- **自动降级** — 下载失败自动尝试下一个最优结果，直到成功
- **速率限制和重试** — 请求间隔 0.5s，失败自动重试（线性退避）
- **浏览模式** — `--list` 参数预览所有结果，不下载
- **格式过滤** — `--format pdf` 限制返回特定格式
- **下载进度条** — 实时显示下载进度

## 安装

```bash
git clone https://github.com/host452b/gethabook.git
cd gethabook
pip install -e .
```

### 依赖

- Python 3.10+
- [httpx](https://www.python-httpx.org/) — HTTP 客户端
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) — HTML 解析
- [click](https://click.palletsprojects.com/) — CLI 框架

所有依赖通过 `pip install` 自动安装。

## 使用方法

### 基本用法：搜索并下载

```bash
gtb "Clean Code"
```

搜索所有数据源，选择最佳文本 PDF，下载到当前目录。

### 指定格式

```bash
gtb "Clean Code" --format epub
```

### 浏览搜索结果（不下载）

```bash
gtb "Godot 4 Game Development Cookbook" --list
```

输出示例：
```
Searching for: Godot 4 Game Development Cookbook
  [annas] found 46 results
  [libgen] found 0 results

46 results:
  1. [pdf] Godot 4 Game Development Cookbook: Over 50 solid recipes... (9.0 MB, annas)
  2. [pdf] Godot 4 Game Development Cookbook: Over 50 solid recipes... (25.1 MB, annas)
  3. [epub] Godot 4 Game Development Cookbook: Over 50 solid recipes... (20.1 MB, annas)
  ...
```

### 下载到指定目录

```bash
gtb "The Art of Game Design" --output ~/Books/
```

### 查看版本

```bash
gtb --version
```

## 工作原理

```
gtb "书名"
       │
       ├── 1. 并行搜索 ──┬── Anna's Archive (annas-archive.gl)
       │                  └── Library Genesis (libgen.is)
       │
       ├── 2. 按 MD5 哈希去重
       │
       ├── 3. 排序结果：
       │      ① 标题相关性（查询词重叠比例）
       │      ② 格式优先级（文本PDF > md > epub > 扫描PDF）
       │      ③ 文件大小（同级别优先选小的）
       │
       ├── 4. 解析下载链接：
       │      Anna's Archive → 详情页 → libgen 镜像 → GET 链接
       │      LibGen → 镜像页（library.lol）→ GET 链接
       │
       └── 5. 下载（失败自动降级 → 尝试下一个结果）
```

## 格式优先级

| 优先级 | 格式 | 检测方式 |
|--------|------|----------|
| 1（最优） | PDF（文本版） | PDF 默认判定为文本版，除非被标记为扫描版 |
| 2 | Markdown | `.md` 扩展名 |
| 3 | EPUB | `.epub` 扩展名 |
| 4 | MOBI/AZW3 | `.mobi` / `.azw3` 扩展名 |
| 5 | PDF（扫描版） | 启发式：每页 >80KB 或无页数信息时 >100MB |
| 6 | 其他 | djvu、cbr 等 |

## 项目结构

```
src/gtb/
├── cli.py              # Click 命令行入口
├── models.py           # BookResult 数据类、FormatType 枚举
├── ranking.py          # 标题相关性 + 格式评分
├── search.py           # 并行搜索调度器（ThreadPoolExecutor）
├── download.py         # 流式下载 + 进度显示
└── sources/
    ├── base.py         # Source 抽象基类、共享 HTTP 客户端（含重试/限速）
    ├── libgen.py       # LibGen 搜索 + 镜像页解析
    └── annas.py        # Anna's Archive 搜索 + 两跳下载解析
```

## 测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

48 个测试覆盖模型、排序、搜索调度、下载管理、CLI 及两个数据源后端（全部使用 mock HTTP，无需网络）。

## 已知限制

- **Anna's Archive 反爬保护** — Cloudflare/DDoS-Guard 可能在某些网络环境下拦截请求。工具已使用真实 User-Agent 和速率限制来缓解。
- **LibGen 镜像可用性** — 镜像域名经常变更。如果下载失败，通常是网络/DNS 问题，使用 VPN 可能有帮助。
- **无验证码破解** — Anna's Archive "慢速下载" 需要验证码，无法自动化。工具改用外部 LibGen 镜像链接。
- **元数据准确性** — 扫描版 PDF 检测基于启发式算法，偶尔可能误判。

## 许可证

MIT
