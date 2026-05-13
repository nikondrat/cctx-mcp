<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/CCTX%E2%80%93MCP-0F172A?style=for-the-badge&logo=python&logoColor=3B82F6&labelColor=1E293B">
    <img src="https://img.shields.io/badge/CCTX%E2%80%93MCP-F1F5F9?style=for-the-badge&logo=python&logoColor=2563EB&labelColor=FFFFFF" alt="CCTX-MCP">
  </picture>
</p>

<p align="center">
  <strong>Cut AI agent token usage by 87%.</strong><br>
  Structure-aware code analysis via the <a href="https://modelcontextprotocol.io">Model Context Protocol</a> —
  returns symbol trees, dependencies, and docs instead of raw file contents.
</p>

<p align="center">
  <a href="https://pypi.org/project/cctx-mcp/"><img src="https://img.shields.io/pypi/v/cctx-mcp?style=flat-square&logo=pypi&logoColor=white&label=PyPI&labelColor=1E293B&color=3B82F6" alt="PyPI"></a>
  <a href="https://pypi.org/project/cctx-mcp/"><img src="https://img.shields.io/pypi/pyversions/cctx-mcp?style=flat-square&logo=python&logoColor=white&label=Python&labelColor=1E293B&color=3B82F6" alt="Python"></a>
  <a href="https://github.com/nikondrat/cctx-mcp"><img src="https://img.shields.io/github/stars/nikondrat/cctx-mcp?style=flat-square&logo=github&logoColor=white&label=Stars&labelColor=1E293B&color=3B82F6" alt="Stars"></a>
  <a href="https://github.com/nikondrat/cctx-mcp/actions"><img src="https://img.shields.io/github/actions/workflow/status/nikondrat/cctx-mcp/ci.yml?style=flat-square&logo=githubactions&logoColor=white&label=CI&labelColor=1E293B&color=3B82F6" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3B82F6?style=flat-square&labelColor=1E293B" alt="License"></a>
  <img src="https://img.shields.io/badge/Status-Beta-3B82F6?style=flat-square&labelColor=1E293B" alt="Beta">
</p>

---

## Overview

**CCTX-MCP** — Code ConTeXt via Model Context Protocol. An MCP server that gives AI agents a structured view of source code without reading entire files.

Built for **Claude**, **Cursor**, **OpenCode**, and any MCP-compatible AI coding tool.

<p align="center">
  <code>uvx cctx-mcp</code>
  &nbsp;·&nbsp;
  <a href="#%EF%B8%8F-tools">Tools</a>
  &nbsp;·&nbsp;
  <a href="#-token-savings">Savings</a>
  &nbsp;·&nbsp;
  <a href="#-install">Install</a>
</p>

---

## Quick Start

```bash
uvx cctx-mcp
```

Add to your MCP client config:

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "uvx",
      "args": ["cctx-mcp"]
    }
  }
}
```

---

## Tools

### Code Analysis

| Tool | Returns | Replaces | Savings |
|------|---------|----------|---------|
| `smart_read` | symbol hierarchy, deps, docs, line counts | `cat` + manual parsing | ~87% |
| `find_symbols` | symbol locations by name or type | `grep -r` + file reads | ~99% |
| `get_dependencies` | all imports of a file in one shot | `grep ^import` | ~96% |
| `trace_calls` | every call site with file + line | `grep` across repo | ~90% |
| `get_symbol_summaries` | AI semantic descriptions per symbol | reading implementation | ~85% |

### Search & Navigation

| Tool | Returns | Replaces | Savings |
|------|---------|----------|---------|
| `analyze_project` | language breakdown, file counts, tree | `find` + `wc` | ~98% |
| `code_search` | regex matches with context lines | `grep` + `cat` | ~90% |
| `semantic_search` | natural language query over indexed codebase | reading everything | ~96% |
| `dir_summary` | directory listing with sizes | `ls -la` | ~80% |
| `find_files` | files matching name, extension, path | `find` | ~80% |

### Git & Commits

| Tool | Returns | Replaces | Savings |
|------|---------|----------|---------|
| `compact_change_intelligence` | structured git diff with intent cues | `git diff` + `git status` | ~75% |
| `draft_commit` | AI-generated conventional commit message | writing from scratch | ~90% |
| `approve_commit_draft` | executes the commit after review | `git add` + `git commit` | — |

### Observability

`get_config` · `get_health` · `get_metrics_report` · `get_metrics_events` · `get_metrics_daily_trend` · `get_metrics_slowest` · `get_version`

---

## Token Savings

| Operation | Native | With CCTX-MCP | Savings |
|-----------|-------:|--------------:|--------:|
| Read 500-line file | ~1,500 tokens | ~200 tokens | **87%** |
| Find function across project | ~5,000 tokens | ~50 tokens | **99%** |
| Understand imports | ~800 tokens | ~30 tokens | **96%** |
| Semantic query across codebase | ~8,000 tokens | ~300 tokens | **96%** |
| Analyze project structure | ~10,000 tokens | ~150 tokens | **98%** |
| Git change summary | ~3,000 tokens | ~750 tokens | **75%** |

Typical session: **80%+ aggregate savings**.

---

## Supported Languages

<p>
  <img src="https://img.shields.io/badge/Swift-FA7343?style=flat-square&logo=swift&logoColor=white" alt="Swift">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Rust-000000?style=flat-square&logo=rust&logoColor=white" alt="Rust">
  <img src="https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go">
  <img src="https://img.shields.io/badge/Dart-0175C2?style=flat-square&logo=dart&logoColor=white" alt="Dart">
</p>

Powered by [tree-sitter](https://tree-sitter.github.io/) AST — each language has a dedicated parser.

---

## Install

### uvx (recommended)

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "uvx",
      "args": ["cctx-mcp"]
    }
  }
}
```

### pip

```bash
pip install cctx-mcp
```

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "python",
      "args": ["-m", "code_context.server"]
    }
  }
}
```

### source

```bash
git clone https://github.com/nikondrat/cctx-mcp.git
cd cctx-mcp
uv sync
uv run python -m code_context.server --skip-index
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CC_OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `CC_OPENROUTER_API_KEY` | — | Remote inference key |
| `CC_LLM_ROUTER` | `local-first` | `local-first`, `local-only`, `remote-first`, `remote-only` |
| `CC_COMMIT_MODEL` | `gemma4:latest` | Local model for commit drafting |
| `CC_EMBED_MODEL` | `nomic-embed-text` | Local model for embeddings |
| `CC_SEMANTIC_SUMMARIES` | `1` | Enable AI symbol summaries |

---

## Development

```bash
uv sync
uv run pytest tests/ -v
```

PRs welcome. [Open issues](https://github.com/nikondrat/cctx-mcp/issues).

---

## License

MIT — free for any use.
