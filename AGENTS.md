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

Need to commit?  ⚠️ ABSOLUTE REQUIREMENT — see "Commit Flow" section below
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

## Server Version Protocol

After editing any source file in `src/`, the MCP server running in memory becomes stale. The server MUST be restarted for changes to take effect.

### Version Bump Policy

After every source edit, bump the `SERVER_VERSION` constant in `server.py`:
- **PATCH** (0.1.0 → 0.1.1): bug fixes
- **MINOR** (0.1.0 → 0.2.0): new features, tools
- **MAJOR** (1.0.0 → 2.0.0): breaking changes

### Staleness Detection Flow

```
1. Edit source code → bump SERVER_VERSION
2. Call get_version()
3. Compare returned version with expected version
   ├── Match → server is up to date ✓
   └── Mismatch → server is stale!
        → "Server is running stale code (vX.Y.Z, expected vA.B.C).
           Please restart opencode to pick up changes."
```

You MUST call `get_version()` after bumping and check for staleness. If the server is stale, do NOT continue using tools — prompt the user to restart.

---

## Commit Flow — ABSOLUTE REQUIREMENT

<EXTREMELY-IMPORTANT>
Running native git commands (`git diff`, `git status`, `git log`, `git commit`) for commit-related tasks is strictly prohibited. It wastes 75%+ tokens per operation and bypasses the commit drafting gate.

You MUST use the code-context MCP commit flow for ALL commit operations:

```
1. compact_change_intelligence(project_path)   → structured diff + intent cues
2. draft_commit(project_path)                  → AI-generated candidate message
3. approve_commit_draft(project_path, message?) → execute git commit
```

You MUST NOT use: `git diff`, `git status`, `git log`, `git add`, `git commit`, or any other native git command for commit operations.

There are zero exceptions. This is not negotiable.
</EXTREMELY-IMPORTANT>

### Fallback — MCP Server Unavailable

If `compact_change_intelligence` or `draft_commit` returns an error (e.g., MCP server unavailable), use `approve_commit_draft(project_path, message='...')` with a manually written conventional commit message. NEVER fall back to bash `git commit`.

### Red Flags — Commit Rationalization

If you catch yourself thinking any of these, STOP — you are rationalizing:

| Thought | Reality |
|---------|---------|
| "I'll just run `git diff` to see what changed" | Use `compact_change_intelligence` — structured output, 75% fewer tokens |
| "Let me check `git status` real quick" | `compact_change_intelligence` includes status + diff in one call |
| "I'll just commit directly, it's a simple change" | Always use the 3-step commit flow. Drafting catches message quality issues. |
| "I'm only looking at git log for context" | `compact_change_intelligence` already includes recent history |
| "The MCP tool might not work on this project" | It works. This is rationalization. Use the tool. |
| "This doesn't need a formal commit flow" | Every commit does. The gate prevents accidental commits. |
| "Let me git add && git commit quickly" | Even staging should go through the MCP tools. Always. |
| "I need to see the raw diff, the tool strips data" | `compact_change_intelligence` is lossless — full diff + structured metadata |
| "The MCP tool returned an error, I'll just git commit directly" | Use the fallback: `approve_commit_draft(project_path, message='...')` with a manual message. NEVER fall back to bash `git commit`. |
| "I just fixed the code, the server will pick it up" | The running server still has old code. Bump `SERVER_VERSION` and call `get_version()` to verify. |

---

## Observability

### `get_config()`
Current feature flag state (routing mode, providers, models, and rollout flags).

### `get_metrics_report()`
Cache hit rate, summary latency, token reduction estimates, draft acceptance rate.

### `get_metrics_events(limit?)`
Recent tool-call records (timestamp, tool name, latency, success/error) from
`~/.code-context-cache/metrics/events.jsonl`.

---

## Feature Flags

| Env var | Default | Effect |
|---------|---------|--------|
| `CC_SEMANTIC_SUMMARIES` | `1` | Enable semantic symbol summaries |
| `CC_COMMIT_DRAFTING` | `1` | Enable commit draft generation |
| `CC_LLM_ROUTER` | `local-first` | Routing policy: `local-first`, `local-only`, `remote-first`, `remote-only` |
| `CC_LOCAL_PROVIDER` | `ollama` | Local provider identifier |
| `CC_REMOTE_PROVIDER` | `openrouter` | Remote provider identifier |
| `CC_COMMIT_MODEL` | `gemma4:latest` | Local model for commit generation (`""` = disable local commit generation) |
| `CC_EMBED_MODEL` | `nomic-embed-text` | Local model for embeddings (`""` = disable local embeddings) |
| `CC_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `CC_OLLAMA_TIMEOUT` | `10` | Request timeout in seconds |
| `CC_OPENROUTER_API_KEY` | `` | OpenRouter API key (required for remote modes/fallback) |
| `CC_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `CC_OPENROUTER_TIMEOUT` | `10` | OpenRouter request timeout in seconds |
| `CC_OPENROUTER_EMBED_MODEL` | `text-embedding-3-small` | Remote embeddings model |
| `CC_OPENROUTER_COMMIT_MODEL` | `openai/gpt-4o-mini` | Remote commit model |
| `CC_OPENROUTER_MAX_TOKENS` | `256` | Max generation tokens for remote commit drafting |
| `CC_OPENROUTER_TEMPERATURE` | `0.1` | Sampling temperature for remote commit drafting |

Notes:
- `local-first` prioritizes Ollama for privacy/latency and falls back to OpenRouter.
- If OpenRouter token is missing, remote calls fail safely with explicit `provider unavailable` errors.

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
