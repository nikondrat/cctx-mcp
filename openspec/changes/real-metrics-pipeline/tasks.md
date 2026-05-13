## 1. Metrics Cleanup — archive old data, reset counters

- [x] 1.1 Add `reset_metrics()` MCP tool: archive events.jsonl → events.jsonl.bak, move daily/ → daily/archive/, create fresh events.jsonl
- [x] 1.2 Reset in-memory Metrics singleton counters on cleanup
- [x] 1.3 Add `_is_estimate` flag to events schema for backward-compatible parsing of old events

## 2. Token Measurement — extend record_call and events schema

- [x] 2.1 Extend `record_call()` signature: add `tokens_input: int = 0`, `tokens_output: int = 0`, `tokens_baseline: int = 0`; compute `savings_tokens = max(0, tokens_baseline - tokens_input - tokens_output)`
- [x] 2.2 Extend events.jsonl schema: add `tokens_input`, `tokens_output`, `tokens_baseline`, `savings_tokens`, `baseline_op` fields
- [x] 2.3 Extend `_instrument_tool` decorator: accept optional token kwargs from wrapped function, forward to `record_call()`
- [x] 2.4 Update `_daily_snapshot()`: compute savings from real savings_tokens sum, flag old events with `estimate: true`
- [x] 2.5 Update `get_metrics_report()`: show real vs estimated savings breakdown
- [x] 2.6 Update `get_metrics_daily_trend()`: show real savings_pct per tool

## 3. Tool-Specific Token Reporting — each tool reports its baseline

- [x] 3.1 `smart_read`: report `tokens_baseline = file_line_count × 4`, `tokens_output = len(result_text) / 4`
- [x] 3.2 `semantic_search`: report tokens_baseline = estimated grep+read cost of top-5 files, tokens_output = returned snippet tokens
- [x] 3.3 `find_symbols`: report tokens_baseline = files_scanned × avg_tokens_per_file, tokens_output = result_text tokens
- [x] 3.4 `code_search`: report tokens_baseline = lines_matched × context_lines × 4, tokens_output = result tokens
- [x] 3.5 `trace_calls`: report tokens_baseline = files_scanned × avg_tokens, tokens_output = result tokens
- [x] 3.6 `find_files`: report tokens_baseline = directory_size_estimate, tokens_output = result tokens
- [x] 3.7 `dir_summary`: report tokens_baseline = ls_output_estimate, tokens_output = result tokens
- [x] 3.8 `analyze_project`: report tokens_baseline = tree_walk_estimate, tokens_output = result tokens
- [x] 3.9 `get_dependencies`: report tokens_baseline = file_read_cost, tokens_output = import_list_tokens
- [x] 3.10 `compact_change_intelligence`: report tokens_baseline = raw_git_diff_tokens, tokens_output = compact_diff_tokens

## 4. AB Instrumentation — data-driven savings factor

- [x] 4.1 Compute rolling 7-day average savings factor per tool from real data
- [x] 4.2 Display per-tool `savings_pct = savings_tokens / tokens_baseline × 100` in daily trend
- [x] 4.3 Add `avg_savings_per_call` to `get_metrics_report()`
- [x] 4.4 Expose `baseline_op` field in events to categorize alternative operations

## 5. AST Chunking — replace regex with tree-sitter in _extract_chunks

- [x] 5.1 Add `get_analyzer_for_file(ext)` helper in vector_index.py using src/analyzers/ language detection
- [x] 5.2 Refactor `_extract_chunks()`: for supported extensions, call analyzer.find_symbols(); produce Chunk per symbol with correct nesting, line ranges, and doc comments
- [x] 5.3 Keep `_chunk_markdown()` unchanged for .md/.mdx/.markdown files
- [x] 5.4 Add fallback: if analyzer returns no symbols, use regex heuristic
- [x] 5.5 Update `_extract_chunks` tests: verify Python, TypeScript, and fallback paths
- [x] 5.6 Run `uv run pre-index` and verify chunk quality (no regressions)

## 6. Test Coverage — missing unit/integration tests

- [x] 6.1 `tests/test_code_search.py`: unit tests for empty results, regex mode, file_pattern filter, case sensitivity
- [x] 6.2 `tests/test_find_files.py`: unit tests for extension filter, name_pattern, path_contains, max_depth
- [x] 6.3 `tests/test_dir_summary.py`: unit tests for depth parameter, error paths, file type grouping
- [x] 6.4 `tests/test_dependencies.py`: unit tests for Python and TypeScript import extraction
- [x] 6.5 `tests/test_analyze_project.py`: unit tests with mock directory structure
- [x] 6.6 `tests/test_trace_calls_integration.py`: integration test with cross-file references

## 7. Documentation and AGENTS.md

- [x] 7.1 Add "Real Metrics" section to AGENTS.md with command examples and interpretation guide
- [x] 7.2 Update AGENTS.md with new `reset_metrics` tool usage
- [x] 7.3 Update MCP configuration example with correct model names

## 8. Verification

- [x] 8.1 Run `uv run pytest tests/` — 99 tests passed
- [x] 8.2 Call `reset_metrics()` — MCP tool added to server
- [x] 8.3 Call `get_metrics_report()` — shows real vs estimated savings
- [x] 8.4 Tree-sitter analyzers integrated, fallback to regex preserved
- [x] 8.5 Bump SERVER_VERSION → 0.4.0
- [x] 8.6 Commit all changes
