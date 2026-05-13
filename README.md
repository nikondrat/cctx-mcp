<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/%E2%96%B0%20MCP%20Code%20Context-0F172A?style=for-the-badge&logo=python&logoColor=3B82F6&labelColor=1E293B">
    <img src="https://img.shields.io/badge/%E2%96%B0%20MCP%20Code%20Context-F1F5F9?style=for-the-badge&logo=python&logoColor=2563EB&labelColor=FFFFFF" alt="MCP Code Context">
  </picture>
</p>

<p align="center">
  <strong>Cut AI agent token usage by 87%.</strong>
  Structure-aware code analysis via the <a href="https://modelcontextprotocol.io">Model Context Protocol</a> —
  returns symbol hierarchies, dependencies, and docs instead of raw file contents.
</p>

<p align="center">
  <a href="https://pypi.org/project/mcp-code-context/"><img src="https://img.shields.io/pypi/v/mcp-code-context?style=flat-square&logo=pypi&logoColor=white&label=PyPI&labelColor=1E293B&color=3B82F6" alt="PyPI"></a>
  <a href="https://pypi.org/project/mcp-code-context/"><img src="https://img.shields.io/pypi/pyversions/mcp-code-context?style=flat-square&logo=python&logoColor=white&label=Python&labelColor=1E293B&color=3B82F6" alt="Python"></a>
  <a href="https://github.com/nikondrat/code-context"><img src="https://img.shields.io/github/stars/nikondrat/code-context?style=flat-square&logo=github&logoColor=white&label=Stars&labelColor=1E293B&color=3B82F6" alt="Stars"></a>
  <a href="https://github.com/nikondrat/code-context/actions"><img src="https://img.shields.io/github/actions/workflow/status/nikondrat/code-context/ci.yml?style=flat-square&logo=githubactions&logoColor=white&label=CI&labelColor=1E293B&color=3B82F6" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3B82F6?style=flat-square&labelColor=1E293B" alt="License"></a>
  <img src="https://img.shields.io/badge/Status-Beta-3B82F6?style=flat-square&labelColor=1E293B" alt="Beta">
</p>

---

## Overview

**MCP Code Context** is an [MCP](https://modelcontextprotocol.io) server that gives AI agents a structured view of source code — symbol trees, dependency graphs, documentation comments, and line counts — without reading entire files.

Built for **Claude**, **Cursor**, **OpenCode**, and any MCP-compatible AI coding tool.

<p align="center">
  <a href="#-quick-start"><code>Get started →</code></a>
  &nbsp;&nbsp;
  <a href="#%EF%B8%8F-tools"><code>Browse all tools →</code></a>
  &nbsp;&nbsp;
  <a href="#-token-savings"><code>See savings →</code></a>
</p>

---

## Quick Start

```bash
# One command — no clone, no install
uvx mcp-code-context
```

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "code-context": {
      "command": "uvx",
      "args": ["mcp-code-context"]
    }
  }
}
```

> Compatible with: Claude Desktop · Cursor · OpenCode · Windsurf · VS Code (Cline/Continue) · any MCP client

---

## Installation

Choose your preferred method:

### uvx (zero-config, automatic updates)

```json
{
  "mcpServers": {
    "code-context": {
      "command": "uvx",
      "args": ["mcp-code-context"]
    }
  }
}
```

### pip (versioned releases)

```bash
pip install mcp-code-context
```

```json
{
  "mcpServers": {
    "code-context": {
      "command": "python",
      "args": ["-m", "code_context.server"]
    }
  }
}
```

### source (bleeding edge)

```bash
git clone https://github.com/nikondrat/code-context.git
cd code-context
uv sync
uv run python -m code_context.server --skip-index
```

---

## Tools

Every tool replaces an expensive native operation. Together they save **75–99%** per call.

### Code Analysis

| Tool | What it returns | Replaces | Savings |
|------|-----------------|----------|---------|
| `smart_read` | symbol hierarchy, deps, docs, line counts | `cat` + manual parsing | ~87% |
| `find_symbols` | symbol locations by name or type across project | `grep -r` + file reads | ~99% |
| `get_dependencies` | all imports of a file in one shot | `grep ^import` | ~96% |
| `trace_calls` | every call site with file + line | `grep` across repo | ~90% |
| `get_symbol_summaries` | AI-generated semantic descriptions per symbol | reading implementation | ~85% |

### Search

| Tool | What it returns | Replaces | Savings |
|------|-----------------|----------|---------|
| `analyze_project` | language breakdown, file counts, directory tree | `find` + `wc` | ~98% |
| `code_search` | regex matches with context lines | `grep` + `cat` | ~90% |
| `semantic_search` | natural language query over indexed codebase | reading everything | ~96% |
| `dir_summary` | directory listing with sizes | `ls -la` | ~80% |
| `find_files` | files matching name, extension, path | `find` | ~80% |

### Git & Commits

| Tool | What it returns | Replaces | Savings |
|------|-----------------|----------|---------|
| `compact_change_intelligence` | structured git diff with intent cues | `git diff` + `git status` | ~75% |
| `draft_commit` | AI-generated conventional commit message | writing from scratch | ~90% |
| `approve_commit_draft` | executes the commit after review | `git add` + `git commit` | — |

### Observability

| Tool | What it returns |
|------|-----------------|
| `get_config` | all feature flags and routing config |
| `get_health` | aggregated status of Ollama, embeddings, tree-sitter |
| `get_metrics_report` | token savings, cache hit rate, latencies |
| `get_metrics_events` | recent tool-call log |
| `get_metrics_daily_trend` | day-by-day usage and savings |
| `get_metrics_slowest` | top-N slowest tools |
| `get_version` | server version for staleness detection |

---

## Token Savings

Measured against the cheapest native alternative for each operation:

| Operation | Without code-context | With code-context | Savings |
|-----------|--------------------:|------------------:|--------:|
| Read 500-line file | ~1,500 tokens | ~200 tokens | **87%** |
| Find function across project | ~5,000 tokens | ~50 tokens | **99%** |
| Understand imports | ~800 tokens | ~30 tokens | **96%** |
| Semantic query across codebase | ~8,000 tokens | ~300 tokens | **96%** |
| Analyze project structure | ~10,000 tokens | ~150 tokens | **98%** |
| Git change summary | ~3,000 tokens | ~750 tokens | **75%** |

Savings compound with every tool call. In a typical session: **80%+ aggregate savings**.

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

Parsed via [tree-sitter](https://tree-sitter.github.io/) AST — not regex. Each language gets a dedicated analyzer with complete grammar support.

---

## Architecture

```
src/code_context/
├── server.py                # MCP server — 20+ tools
├── cache.py                 # version-aware disk cache
├── search.py                # cross-project symbol/file search
├── config.py                # feature flags (env-based)
├── metrics.py               # token savings instrumentation
├── vector_index.py          # semantic search via embeddings
├── change_intel.py          # git diff intelligence
├── commit_generator.py      # AI commit drafting
├── pre_index_cli.py         # CLI for pre-building index
├── analyzers/               # language AST parsers
│   ├── base.py              # abstract interface
│   ├── swift.py · python.py · typescript.py
│   ├── rust.py · go.py · dart.py
└── llm/                     # provider abstraction
    ├── router.py            # local-first → remote fallback
    ├── contracts.py
    └── providers/
        ├── ollama.py
        └── openrouter.py
```

Routing policy: `local-first` — Ollama for privacy/latency, OpenRouter for fallback. Configurable via `CC_LLM_ROUTER`.

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
# setup
uv sync

# test
uv run pytest tests/ -v

# type check (coming soon)
# uv run mypy src/
```

PRs welcome. See [open issues](https://github.com/nikondrat/code-context/issues).

---

## License

MIT — free for any use. No attribution required, but appreciated.
