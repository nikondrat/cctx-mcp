## 1. Foundation — shared infrastructure

- [ ] 1.1 Bump `SERVER_VERSION` in `server.py` (minor version for new capabilities)
- [ ] 1.2 Create `src/code_context/editor.py` — file editing logic with diff generation, dry-run, and safety checks
- [ ] 1.3 Create `src/code_context/git_ops.py` — git command wrappers with structured output parsing
- [ ] 1.4 Add `editor.py` and `git_ops.py` to test suite discovery

## 2. code_search unbounded (cursor pagination)

- [ ] 2.1 Modify `ProjectSearch.code_search()` in `search.py` to support `cursor` parameter and return `next_cursor`
- [ ] 2.2 Implement cursor encoding/decoding (opaque string, internally encodes file+line position)
- [ ] 2.3 Update `tool_code_search` in `handlers.py` to accept and pass through `cursor` parameter
- [ ] 2.4 Format response as structured JSON with `matches`, `next_cursor`, `total_estimate` fields
- [ ] 2.5 Register updated tool signature in `server.py`
- [ ] 2.6 Write tests: pagination, cursor round-trip, unlimited mode

## 3. file_edit — replace_in_file tool

- [ ] 3.1 Implement `FileEditor` class in `editor.py` with: exact string replace, regex replace, replace_all
- [ ] 3.2 Implement dry-run mode that computes and returns diff without writing
- [ ] 3.3 Implement safety checks: read-before-edit validation (cache hash check), path traversal prevention
- [ ] 3.4 Implement `tool_replace_in_file` handler in `handlers.py`
- [ ] 3.5 Register `replace_in_file` tool in `server.py`
- [ ] 3.6 Write tests: exact replace, regex replace, dry-run, safety rejections, path traversal

## 4. compound operations — investigate_symbol

- [ ] 4.1 Implement `CompoundOps` class with `investigate_symbol` method that calls find_symbols → trace_calls → smart_read
- [ ] 4.2 Run sub-operations in parallel via `concurrent.futures.ThreadPoolExecutor`
- [ ] 4.3 Structure response JSON with per-operation timing (`latency_ms` per sub-op)
- [ ] 4.4 Implement `tool_investigate_symbol` handler in `handlers.py`
- [ ] 4.5 Register `investigate_symbol` tool in `server.py`
- [ ] 4.6 Write tests: full investigation, symbol not found, partial failure

## 5. live-search fallback

- [ ] 5.1 Implement `LiveSearcher` utility class with ripgrep subprocess and pure-Python fallback
- [ ] 5.2 Integrate fallback into `ProjectSearch.code_search()` — call live search when index returns 0 results
- [ ] 5.3 Add `_fallback: "live-disk"` and `_fallback_method` indicators to response
- [ ] 5.4 Write tests: rg fallback, Python-re fallback, no fallback when results exist

## 6. git operations — diff, log, status

- [ ] 6.1 Implement `git_diff()` in `git_ops.py` — wraps `git diff` with staged/unstaged support, returns structured JSON
- [ ] 6.2 Implement `git_log()` in `git_ops.py` — wraps `git log --oneline --format=...` with limit parameter
- [ ] 6.3 Implement `git_status()` in `git_ops.py` — wraps `git status --porcelain`, parses into branch/staged/unstaged/untracked
- [ ] 6.4 Implement three tool handlers (`tool_git_diff`, `tool_git_log`, `tool_git_status`) in `handlers.py`
- [ ] 6.5 Register all three git tools in `server.py`
- [ ] 6.6 Write tests: diff with/without changes, log history, status parsing

## 7. smart_read enhanced — offset, limit, symbol

- [ ] 7.1 Extend `tool_smart_read` in `handlers.py` with optional `offset: int`, `limit: int`, `symbol: str` parameters
- [ ] 7.2 When `symbol` is provided, look up the symbol's line range in the analysis and scope output to that range
- [ ] 7.3 When `offset`/`limit` is provided, clip analysis output to those line boundaries
- [ ] 7.4 Validate backward compatibility: default behavior unchanged
- [ ] 7.5 Write tests: line-range read, symbol-scoped read, offset beyond file, backward compatibility

## 8. batch operations — batch_run tool

- [ ] 8.1 Implement `batch_run` dispatcher in `handlers.py` — accepts `tool`, `params` array, runs sequentially
- [ ] 8.2 Implement per-item error isolation (errors in one param set don't affect others)
- [ ] 8.3 Implement max batch size enforcement (default 10, configurable)
- [ ] 8.4 Support batch for: `code_search`, `find_symbols`, `trace_calls`
- [ ] 8.5 Register `batch_run` tool in `server.py`
- [ ] 8.6 Write tests: multi-item batch, single-item batch, partial failure, size limit exceeded

## 9. Integration & verification

- [ ] 9.1 Run existing test suite to confirm no regressions
- [ ] 9.2 Run `ruff check` and fix any linting issues
- [ ] 9.3 Verify all new tools are discoverable via MCP tool list
- [ ] 9.4 Update `AGENTS.md` priority rules to reflect new capabilities
