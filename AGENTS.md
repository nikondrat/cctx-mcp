# Code Context — AI Agent Guide

## MANDATORY: Use These Tools First

This MCP server exists to **replace expensive native operations**. Using `cat`, `grep`, `find`, or reading entire files when these tools are available wastes tokens and is the wrong approach.

### Priority Rules (non-negotiable)

| Instead of this | Use this | Token savings |
|-----------------|----------|---------------|
| `Read` / `cat` entire file | `smart_read` | ~87% |
| `Grep` / searching for a symbol | `find_symbols` or `semantic_search` | ~90% |
| `Glob` / `find` for files | `find_files` or `dir_summary` | ~80% |
| Manual import parsing | `get_dependencies` | ~95% |
| Searching call sites by grep | `trace_calls` | ~90% |
| `git diff` + manual parsing | `compact_change_intelligence` | ~75% |
| Reading file to understand structure | `smart_read` → then read only if needed | ~87% |
| Exploring unfamiliar codebase | `analyze_project` → `smart_read` per file | ~85% |

**The only exception:** read a file directly only when you need the full implementation body to make an edit. Even then, use `smart_read` first to locate the exact symbol, then read only the relevant line range.

---

## Decision Tree: Which Tool to Use

```
Need to understand code?
├── Unfamiliar codebase → analyze_project
├── Specific file structure → smart_read
├── Find a function/class by name → find_symbols
├── Natural language query ("where is auth handled?") → semantic_search
├── Find callers of a function → trace_calls
├── Understand imports → get_dependencies
└── Browse directory → dir_summary

Need to commit?
├── Understand what changed → compact_change_intelligence
├── Generate message → draft_commit
└── Execute commit → approve_commit_draft
```

---

## Tools Reference

### `smart_read(file_path, project_path?)`
Structured file analysis: symbol hierarchy, dependencies, line ranges, doc comments.
Use before reading any file. Only read full file if you need implementation details after seeing the structure.

```
smart_read(file_path="src/auth/provider.py", project_path="/project")
```

### `semantic_search(query, project_path, top_k?)`
Natural language search over indexed codebase using embeddings.
Fastest path for "find where X is done" questions — returns relevant code chunks, not full files.

```
semantic_search(query="user authentication token validation", project_path="/project", top_k=5)
```

### `find_symbols(project_path, name?, symbol_type?)`
Exact symbol search by name or type (function, class, method, interface, struct, enum, protocol).

```
find_symbols(project_path="/project", name="login", symbol_type="function")
```

### `get_dependencies(file_path, project_path?)`
All imports/dependencies of a file without reading it.

```
get_dependencies(file_path="src/server.py", project_path="/project")
```

### `trace_calls(symbol_name, project_path)`
Every call site of a symbol across the project. Use for impact analysis before changing anything.

```
trace_calls(symbol_name="AuthProvider.login", project_path="/project")
```

### `analyze_project(project_path, max_depth?)`
Project-wide structure: file counts, languages, directory tree. Always start here on unfamiliar projects.

```
analyze_project(project_path="/project", max_depth=2)
```

### `get_symbol_summaries(file_path, project_path?)`
Semantic summaries per symbol: purpose, behavior, confidence, provenance. Lazy + cached.

```
get_symbol_summaries(file_path="src/server.py", project_path="/project")
```

### `find_files(project_path, name_pattern?, extension?, path_contains?)`
Find files by name pattern, extension, or path substring.

```
find_files(project_path="/project", name_pattern="*Controller*", extension="py")
```

### `dir_summary(project_path, dir_path?, depth?)`
Directory listing with file counts and sizes — `ls -la` replacement.

```
dir_summary(project_path="/project", dir_path="src/api", depth=2)
```

### `code_search(project_path, pattern, use_regex?, file_pattern?, context_lines?)`
Regex/text search across files with context. Use when `find_symbols` isn't specific enough.

```
code_search(project_path="/project", pattern="TODO|FIXME", file_pattern="*.py")
```

---

## Commit Flow (always use this sequence)

```
1. compact_change_intelligence(project_path)   → understand what changed
2. draft_commit(project_path)                  → generate candidate message (Ollama if available)
3. approve_commit_draft(project_path, message?) → execute git commit
```

Never run `git commit` directly. The gate ensures message quality and prevents accidental commits.

---

## Observability

### `get_config()`
Current feature flag state (which Ollama models active, flags enabled/disabled).

### `get_metrics_report()`
Cache hit rate, summary latency, token reduction estimates, draft acceptance rate.

---

## Feature Flags

| Env var | Default | Effect |
|---------|---------|--------|
| `CC_SEMANTIC_SUMMARIES` | `1` | Enable semantic symbol summaries |
| `CC_COMMIT_DRAFTING` | `1` | Enable commit draft generation |
| `CC_COMMIT_MODEL` | `gemma4:latest` | Ollama model for commit messages (`""` = heuristic fallback) |
| `CC_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings (`""` = disable semantic_search) |
| `CC_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `CC_OLLAMA_TIMEOUT` | `10` | Request timeout in seconds |

---

## Token Budget Reference

| Operation | Native approach | With code-context | Savings |
|-----------|----------------|-------------------|---------|
| Read 500-line file | ~1500 tokens | ~200 tokens (smart_read) | **87%** |
| Find function across project | ~5000 tokens (grep + reads) | ~50 tokens (find_symbols) | **99%** |
| Understand imports | ~800 tokens | ~30 tokens (get_dependencies) | **96%** |
| Semantic query | ~8000 tokens (read many files) | ~300 tokens (semantic_search) | **96%** |
| Analyze project structure | ~10000 tokens | ~150 tokens (analyze_project) | **98%** |

---

## Supported Languages

Swift · Python · TypeScript · JavaScript · Rust · Go · Dart

---

## MCP Configuration

```json
{
  "mcpServers": {
    "code-context": {
      "command": "uv",
      "args": ["--directory", "/path/to/code-context", "run", "server.py"],
      "env": {
        "CC_COMMIT_MODEL": "gemma3:1b-it-qat",
        "CC_EMBED_MODEL": "nomic-embed-text"
      }
    }
  }
}
```
