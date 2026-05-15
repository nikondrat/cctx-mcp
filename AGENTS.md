# Code Context — AI Agent Guide

> **CCTX-MCP** (`uvx cctx-mcp`) — replace expensive native operations with structured analysis tools for 80-99% token savings.

---

## MANDATORY: Use These Tools First

This MCP server exists to **replace expensive native operations** (`Read`, `grep`, `find`, `cat`, `git diff`). When any of these tools are available, you MUST prefer them over native alternatives.

### Tool Naming

Tool names may be **prefixed** depending on your MCP client:
- **opencode**: `code-context_smart_read`, `code-context_find_symbols`, `code-context_get_version`, etc.
- **Claude Desktop**: `smart_read`, `find_symbols`, `get_version`, etc. (no prefix)
- **Cursor**: depends on configuration

When in doubt, check your available tool list for the prefix.

### Priority Rules

Each MCP tool's **description** (visible in your tool list) states what native operation it replaces and the token savings. Read those descriptions — they guide tool selection at decision time.

| Instead of this | Use this | Savings |
|-----------------|----------|---------|
| `Read` / `cat` entire file | `smart_read` | ~87% |
| `Grep` for a symbol across project | `find_symbols` | ~99% |
| Manual import parsing | `get_dependencies` | ~96% |
| Searching call sites by grep | `trace_calls` | ~90% |
| Exploring unfamiliar codebase | `analyze_project` | ~98% |
| Reading file just to understand symbols | `smart_read` first | ~87% |
| `git diff` + `git status` | `compact_change_intelligence` | ~75% |
| Writing commit message from scratch | `draft_commit` | ~90% |
| Forgetting available tools | `list_tools` | — |

### Tool Selection Hierarchy (CCTX > Subagent > Native)

For **research / exploration / analysis**:
1. **CCTX tools first** — `find_symbols`, `smart_read`, `trace_calls`, `get_dependencies`, `analyze_project`
2. **Subagents last** — only for tasks CCTX cannot do (mutating code, multi-file refactoring)

Rationale: subagents have only grep/glob/read — they load full files and waste context. CCTX understands project structure and loads only what's needed. Defaulting to subagents for research is a known bad pattern.

**The only exception**: read a file directly only when you need the full implementation body to make an edit. Even then, use `smart_read` first to locate the exact symbol, then read only the relevant line range.

---

## Tool Reference

### `smart_read(file_path, project_path?)`
Structured file analysis: symbol hierarchy, dependencies, line ranges, doc comments.
**Use before reading any file.** Only read full file if you need implementation details.

```
smart_read(file_path="src/auth/provider.py", project_path="/project")
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
Project-wide structure: file counts, languages, directory tree.

```
analyze_project(project_path="/project", max_depth=2)
```

### `get_symbol_summaries(file_path, project_path?)`
Semantic summaries per symbol: purpose, behavior, confidence, provenance.

```
get_symbol_summaries(file_path="src/server.py", project_path="/project")
```

### `compact_change_intelligence(project_path)`
Structured diff + intent cues. Replaces `git diff` + `git status`.

```
compact_change_intelligence(project_path="/project")
```

### `draft_commit(project_path)`
AI-generated conventional commit message from working changes.

```
draft_commit(project_path="/project")
```

### `approve_commit_draft(project_path, message?)`
Execute git commit after reviewing draft. If message is provided, uses it instead.

```
approve_commit_draft(project_path="/project")
```

### `get_version()`
Server version for staleness detection. Call after any edit to verify server picked it up.

### `get_health()`
System dependency health: Ollama, embeddings, vector index, tree-sitter.

### `list_tools()`
List all available cctx commands with descriptions. Call this when you forget what tools exist.

### `get_config()`
Current feature flags and provider settings.

---

## Integration in Other Projects

Copy this section into any project's `.opencode/AGENTS.md` to make AI agents use CCTX-MCP tools:

### Agent Instructions Template

```
## MANDATORY: CCTX-MCP Tools (80-99% Token Savings)

CCTX-MCP is configured as an MCP server. Its tools MUST be preferred over native operations.

| Instead of this | Use this |
|-----------------|----------|
| `Read` entire file | `smart_read` |
| `Grep` for symbols | `find_symbols` |
| Manual call site search | `trace_calls` |
| Project exploration | `analyze_project` |
| `git diff` / `git status` | `compact_change_intelligence` |
| Writing commit messages | `draft_commit` |

Tool names may be prefixed (e.g. `code-context_smart_read`). Check your available tool list.
```

---

## Commit Flow — ABSOLUTE REQUIREMENT

You MUST NOT use:
- `git commit` or `git add` directly. Use these tools instead:

| Instead of this | Use this |
|-----------------|----------|
| `git diff` + `git status` | `compact_change_intelligence` |
| Writing commit message | `draft_commit` |
| `git commit` | `approve_commit_draft` |

Flow:
1. `git add <files>` — stage what you want to commit
2. `compact_change_intelligence(project_path)` to see what changed
3. `draft_commit(project_path)` to generate a commit message (only looks at staged)
4. `approve_commit_draft(project_path)` or `approve_commit_draft(project_path, message='...')` to commit

**NEVER fall back to bash `git commit`**. If the tools fail, report the error — don't use native git commands.

> Important: `draft_commit` now analyzes only **staged** changes (like `git commit`). Stage your changes with `git add` first. The old auto-staging behavior (`git add -A` before commit) has been removed — you control what goes in.

---

## Development Logging

Tool calls are logged to `~/.code-context-cache/debug.jsonl` with args, result preview, latency, and status. Watch in real-time:

```bash
tail -f ~/.code-context-cache/debug.jsonl
```

Set `CC_DEBUG_LOG` env var to change the log path.
