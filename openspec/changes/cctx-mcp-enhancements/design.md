## Context

cctx-mcp currently provides 20 read-only tools (search, symbols, change intel, metrics). Users must fall back to native tools (bash rg, edit, write, git) for 7 common operations that cctx-mcp should handle. The server uses a tree-sitter-based index for fast searches but has no live-disk fallback, no editing support, no git integration, no compound operations, limited search caps, and no batch execution. Each gap forces an MCP exit — costing tokens and breaking flow.

## Goals / Non-Goals

**Goals:**
- Eliminate native tool fallback for code_search, file editing, git operations, and multi-step investigations
- Paginated/unbounded search to handle large result sets without truncation
- Transparent live-disk fallback when the vector index misses a symbol
- Compound operations combining find-symbols + trace-calls into one MCP call
- Batch operations to parallelize N inputs in a single MCP round trip
- Fine-grained smart_read with offset/limit/symbol-range control

**Non-Goals:**
- Full git porcelain — only diff, log, status (not push, rebase, merge)
- Full IDE editing — only find-and-replace by string/regex with safety checks
- Parallel execution across multiple MCP calls — batch is within one call
- File creation or deletion — only content modification within existing files

## Decisions

1. **Cursor-based pagination over offset-based** for code_search. Cursors are stable under concurrent writes (unlikely here but good practice) and don't require counting total matches. Each response includes a `next_cursor` field; `max_results: 0` returns the first page of matches with a cursor.

2. **`replace_in_file` via exact string match + regex** with dry-run mode. Safety: require the user to read the file first (we can verify via cache), provide a `dry_run: true` flag showing diff before applying, and reject edits outside the project root.

3. **Live-disk fallback via subprocess `rg` (ripgrep)** with graceful degradation. When `code_search` or `find_symbols` returns 0 results from the index, fall back to `rg` on the live filesystem. Log the fallback so users know. If `rg` is not installed, surface a clear message.

4. **Compound operations via a new `investigate_symbol` tool** that runs find-symbols → trace-calls → smart-read in a single call. Returns a structured JSON combining all results. Future compound tools follow the same pattern.

5. **Git operations as thin wrappers** around `git diff`, `git log`, `git status` via subprocess. Parse output into structured JSON. `git_status` already partially exists in `compact_change_intelligence`; align naming.

6. **Batch operations via a new `batch_run` tool** that accepts `{"tool": "...", "params": [...]}` — an array of parameter sets for the same tool. Returns an array of results. Executes sequentially within the call (parallel internally via threads if performance demands).

7. **smart_read enhanced** via optional `offset`, `limit`, `symbol` parameters. `symbol="ClassName.methodName"` reads only that symbol's range. `offset`/`limit` pin line ranges. Default behavior unchanged.

## Risks / Trade-offs

- [Risk] `rg` dependency for live fallback → Mitigation: use built-in Python `os.walk` + `re` as fallback if `rg` is unavailable. `rg` is just an optimization.
- [Risk] `replace_in_file` could introduce bugs → Mitigation: always require dry-run first (configurable), and always read file before edit (validate via cache hash).
- [Risk] Compound operations increase latency → Mitigation: internal parallelism via `concurrent.futures` for sub-operations within a compound call.
- [Risk] Batch operations may consume significant resources → Mitigation: impose configurable per-item timeout and max batch size (default 10 items).
- [Risk] Git wrappers may produce inconsistent output across git versions → Mitigation: use `--no-color`, `--no-pager`, stable flags. Parse with git's `--format` options rather than free-text.
- [Trade-off] Cursor pagination is marginally more complex than offset but avoids the "stale page" problem and integrates naturally with infinite-scroll UX patterns.
