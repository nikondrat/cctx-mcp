## Why

The cctx-mcp server eliminates the need for native tools (grep, find, cat, git) in AI coding sessions — but it falls short in 7 areas, forcing fallback to bash/rg/edit/write. These gaps waste tokens and break flow. Closing them makes cctx-mcp a true single-stop tool.

## What Changes

- **code_search unbounded**: Support `max_results: 0` (unlimited) and cursor-based pagination for large result sets
- **file_edit tool**: Add `replace_in_file` capability — find-and-replace by exact string or regex, with dry-run mode
- **compound operations**: Add compound tools like `find_symbols + trace_calls` in one call, or a unified `investigate_symbol` tool
- **live-search fallback**: When index-based search returns empty, fall back to live-disk `rg`/ripgrep search transparently
- **git integrations**: Add `git_diff`, `git_log`, `git_status` as first-class MCP tools
- **smart_read enhanced**: Support `offset`/`limit` parameters, target specific symbol ranges, and context-level control
- **batch operations**: Accept arrays of inputs for search tools to parallelize N queries in one MCP call

## Capabilities

### New Capabilities
- `code-search-unbounded`: Unlimited paginated search with cursor support
- `file-edit`: Find-and-replace editing with dry-run and safety checks
- `compound-operations`: Chained tool calls (e.g. find-symbol + trace-calls)
- `live-search-fallback`: Transparent fallback from index to live filesystem search
- `git-operations`: git diff, log, status as MCP tools
- `smart-read-enhanced`: Fine-grained read control with line ranges and symbol targeting
- `batch-operations`: Parallel multi-query execution in single MCP calls

### Modified Capabilities
*(none — all new capabilities)*

## Impact

- **server.py**: New tool registrations, compound operation dispatcher, batch executor
- **handlers.py**: ~5 new tool handler functions, compound/batch routing logic
- **search.py**: Paginated results in `code_search`, live-disk fallback in `code_search` and `find_symbols`
- **new file**: `src/code_context/editor.py` — file editing logic with safety checks
- **new file**: `src/code_context/git_ops.py` — git command wrappers
- **tests/**: New test files for each capability
- **dependencies**: Potential addition of `ripgrep` (optional, for live fallback)
- **AGENTS.md**: Updated priority rules reflecting new capabilities
