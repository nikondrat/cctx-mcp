## Why

Current metrics show ~267k tokens/day "saved" but these are static estimates (TOOL_SAVINGS_FACTOR × 1500 × calls), not real measurements. There is no counterfactual — no data on what would have been spent WITHOUT the tools. This makes the metrics unusable for real decision-making, reporting, or optimization.

At the same time, 5 tools lack unit tests, chunking uses regex instead of tree-sitter AST, and the remaining open tasks from fix-semantic-search-real are still pending.

## What Changes

- Replace static TOOL_SAVINGS_FACTOR estimates with real per-call token measurement
- Add A/B instrumentation: measure what the agent would do without the tool (counterfactual)
- Clean old metric records and establish a clean baseline
- Switch _extract_chunks from regex to tree-sitter AST analyzers
- Add missing unit tests for untested tools
- Update AGENTS.md with new metrics capabilities and model names
- Archive and reset events.jsonl to start fresh with real data

## Capabilities

### New Capabilities
- `real-token-savings`: Per-tool-call measurement of actual token savings vs baseline (smart_read savings = file_size - result_size, semantic_search = equivalent grep+read volume minus search result volume)
- `ab-instrumentation`: Counterfactual estimation — log what native operation would have been needed, compare actual tool cost, compute real savings per session
- `metrics-cleanup`: Purge old events.jsonl and daily snapshots, establish clean baseline with schema migration for new metric fields
- `ast-chunking`: Replace regex-based _extract_chunks with tree-sitter AST analyzers (from src/analyzers/), enabling accurate nested symbol extraction across all 6 supported languages
- `tool-test-coverage`: Unit tests for code_search, find_files, dir_summary, get_dependencies, analyze_project; integration tests for trace_calls

### Modified Capabilities
- (metrics from post-audit-advanced-metrics): Replace static TOOL_SAVINGS_FACTOR with real per-call input/output token counters; add fields for baseline_estimate_tokens, actual_result_tokens, savings_tokens to events schema

## Impact

- `src/metrics.py`: New fields in record_call() for token counts; new _savings_estimate_real() method; events.jsonl schema migration
- `src/vector_index.py`: Replace _extract_chunks regex with tree-sitter analyzers
- `src/server.py`: _instrument_tool decorator enhanced with token measurement
- `tests/`: 5+ new unit test files; update existing tests for new metric fields
- `~/.code-context-cache/metrics/`: Events schema change; old data archive/cleanup script
- `AGENTS.md`: New metrics documentation sections
