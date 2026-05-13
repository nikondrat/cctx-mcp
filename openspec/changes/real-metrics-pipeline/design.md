## Context

Current metrics collect call count, latency, and errors per tool, but token savings are estimated via static `TOOL_SAVINGS_FACTOR × 1500 × calls`. This is not real data — the factor is theoretical, and 1500 is an arbitrary average file size.

The `_instrument_tool` decorator wraps all MCP tools but captures no context about what the tool saved vs a native alternative. `_extract_chunks` in vector_index.py uses regex instead of tree-sitter AST analyzers, causing inaccurate chunking.

## Goals / Non-Goals

**Goals:**
- Replace `TOOL_SAVINGS_FACTOR` estimates with real per-call token measurements
- Capture baseline (what native operation would cost) and actual (what tool returned) per call
- Switch `_extract_chunks` from regex to tree-sitter AST analyzers
- Clean old events.jsonl and daily snapshots, start fresh with new schema
- Add unit tests for all untested tools

**Non-Goals:**
- No real-time dashboard or visualization
- No per-user/session tracking (only global and daily aggregates)
- No changes to commit flow metrics

## Decisions

### 1. Token measurement strategy: tool-reported baseline

Each tool knows its own "native alternative" cost. The `_instrument_tool` decorator signature expands to `record_call(tool, latency_ms, ok, tokens_input, tokens_output, tokens_baseline)`. Each tool reports:

| Tool | Baseline (tokens_baseline) | Actual (tokens_input + tokens_output) |
|------|---------------------------|--------------------------------------|
| smart_read | file size in tokens (lines × ~4 tokens/line) | result length in tokens |
| semantic_search | estimated grep+read of top-5 files that keyword search would return | chunk snippets length in tokens |
| find_symbols | diff-based estimate: files scanned × avg file tokens | symbol list result length |
| code_search | same as grep output size | match results length |
| trace_calls | files scanned × avg tokens | call sites result length |
| find_files | `find` equivalent directory scan | file list length |
| dir_summary | `ls -la` equivalent listing | directory summary length |
| analyze_project | tree walk equivalent | project stats length |
| get_dependencies | file read + manual import parse | dependency list length |
| get_health | N/A (zero baseline) | system status length |
| get_config | N/A (zero baseline) | config output length |
| get_version | N/A | version JSON length |
| compact_change_intelligence | git diff equivalent | structured diff length |
| draft_commit | N/A (AI generation, no native alternative) | draft text length |
| approve_commit_draft | N/A | commit result length |

Baseline for file-reading tools is estimated as `line_count × 4 tokens` (avg ~4 tokens per line of code).

### 2. Chunking migration: regex → tree-sitter

Add a `get_analyzer_for_file()` helper in `vector_index.py` that maps file extension to existing analyzers in `src/analyzers/`. Use `analyzer.parse_file()` and `analyzer.find_symbols()` to extract symbols with accurate line ranges. Fall back to regex for markdown files and unknown extensions.

The existing `_extract_chunks` regex approach (`_def_re`) is replaced. The analyzers already handle: Python, TypeScript/JavaScript, Swift, Go, Rust, Dart.

### 3. Events schema migration

New fields appended to events.jsonl:
```json
{
  "ts": 1234567890,
  "tool": "smart_read",
  "latency_ms": 12,
  "ok": true,
  "tokens_input": 45,
  "tokens_output": 180,
  "tokens_baseline": 4200
}
```

Savings computed as `tokens_baseline - (tokens_input + tokens_output)`, or `max(0, tokens_baseline - tokens_output)` for read-only tools where input is negligible.

### 4. Cleanup strategy

- Archive old events.jsonl → events.jsonl.bak
- Start fresh events.jsonl with new schema
- Archive old daily snapshots → daily/archive/
- Reset in-memory Metrics counters
- Bump SERVER_VERSION

## Risks / Trade-offs

- [Baseline estimation is inherently imprecise] → Use conservative estimates (lower bound). Document methodology so numbers are reproducible.
- [Tool overhead may increase latency slightly] → Token counting is O(result_length), negligible vs Ollama/embed latency.
- [tree-sitter analyzers may miss some patterns regex caught] → Add fallback: if analyzer returns no symbols, fall back to regex heuristic.
- [Events schema change breaks daily trend continuity] → Acceptable — old data is estimates, new data is real measurements.
