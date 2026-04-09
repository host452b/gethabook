# gethatbook (gtb) 中文文档

一个命令行电子书聚合搜索下载工具。跨多个开放数据源并行搜索，按格式质量和标题相关性自动选择最佳结果并下载 —— 一条命令搞定。

[English](README.md)

## 功能特性

- **多源并行搜索** — 同时搜索多个电子书数据源，合并结果，按 MD5 去重
- **智能自动选择** — 按标题相关性 → 格式优先级（`文本PDF > md > epub > mobi > 扫描PDF`）→ 文件大小排序
- **扫描版 PDF 检测** — 基于每页字节数启发式检测扫描/OCR版PDF，自动降低优先级
- **自动降级** — 下载失败自动尝试下一个最优结果，直到成功
- **速率限制和重试** — 请求间隔限速，失败自动重试（线性退避）
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
- httpx — HTTP 客户端
- beautifulsoup4 + lxml — HTML 解析
- click — CLI 框架

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
gtb "Design Patterns" --list
```

输出示例：
```
Searching for: Design Patterns

62 results:
  1. [pdf] Design Patterns: Elements of Reusable Object-Oriented Software (5.2 MB, source-a)
  2. [epub] Design Patterns: Elements of Reusable Object-Oriented Software (1.8 MB, source-b)
  3. [pdf] Head First Design Patterns (12.3 MB, source-b)
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
       ├── 1. 并行搜索多个数据源
       │
       ├── 2. 按 MD5 哈希去重
       │
       ├── 3. 排序结果：
       │      ① 标题相关性（查询词重叠比例）
       │      ② 格式优先级（文本PDF > md > epub > 扫描PDF）
       │      ③ 文件大小（同级别优先选小的）
       │
       ├── 4. 通过镜像页解析下载链接
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
├── cli.py              # 命令行入口
├── models.py           # BookResult 数据类、FormatType 枚举
├── ranking.py          # 标题相关性 + 格式评分
├── search.py           # 并行搜索调度器
├── download.py         # 流式下载 + 进度显示
└── sources/
    ├── base.py         # Source 抽象基类、共享 HTTP 客户端（含重试/限速）
    ├── libgen.py       # 数据源 A：搜索 + 镜像页解析
    └── annas.py        # 数据源 B：搜索 + 两跳下载解析
```

## 测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

48 个测试覆盖模型、排序、搜索调度、下载管理、CLI 及两个数据源后端（全部使用 mock HTTP，无需网络）。

## 免责声明

本项目**仅供学习和测试使用**。用户应自行遵守所在地区的法律法规。**严禁将本工具用于侵犯版权、盗版或其他任何违法行为。** 作者不对因滥用本软件而产生的任何后果承担责任。如果您觉得某本书有价值，请购买正版以支持作者。

## 许可证

MIT
