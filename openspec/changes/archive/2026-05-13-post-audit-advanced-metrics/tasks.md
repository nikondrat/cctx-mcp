## 1. metrics.py — slowest + errors + daily snapshot

- [x] 1.1 Add `slowest(limit=5) -> list[dict]` method to Metrics class: aggregate per-tool from `_calls` + `_call_latency_ms` + `_call_errors`, sort by avg latency descending
- [x] 1.2 Add `errors_summary() -> dict` method: filter tools with errors > 0, compute total error rate
- [x] 1.3 Implement `_savings_estimate(tool_name: str, calls: int) -> int`: estimate token savings per tool using `TOOL_SAVINGS_FACTOR` dict (smart_read=0.87, find_symbols=0.99, semantic_search=0.96, etc.)
- [x] 1.4 Add `_daily_snapshot() -> dict`: aggregate today's events from `events.jsonl`, compute per-tool stats + savings estimate, write to `daily/YYYY-MM-DD.json` with atomic rename
- [x] 1.5 Add `get_daily_trend(days=7) -> list[dict]`: read daily snapshot files for last N days, return as list

## 2. server.py — new MCP tools

- [x] 2.1 Add `get_metrics_slowest(limit: int = 5) -> str` tool
- [x] 2.2 Add `get_metrics_errors() -> str` tool
- [x] 2.3 Add `get_metrics_daily_trend(days: int = 7) -> str` tool that triggers `_daily_snapshot()` on first call today

## 3. AGENTS.md — commit flow enforcement

- [x] 3.1 Restructure "## Commit Flow (always use this sequence)" to "## Commit Flow (MANDATORY)" with MUST-level language before the existing section
- [x] 3.2 Add "Fallback: if compact_change_intelligence or draft_commit return an error, use approve_commit_draft(project_path, message='...') with a manually written message. NEVER fall back to bash git commit."
- [x] 3.3 Update the existing numbered list to explicitly forbid direct `git commit`

## 4. Tests

- [x] 4.1 Unit tests: `tests/test_metrics.py` — test `slowest()`, `errors_summary()`, `_savings_estimate()`, `get_daily_trend()`
- [x] 4.2 Unit tests: `tests/test_metrics.py` — test `_daily_snapshot()` with mock events.jsonl
- [x] 4.3 Create `tests/test_commit_flow.py` — parse AGENTS.md, verify `compact_change_intelligence` + `draft_commit` + `approve_commit_draft` strings exist under "## Commit Flow (MANDATORY)" header
- [x] 4.4 Create `tests/test_commit_flow.py` — verify AGENTS.md explicitly forbids direct `git commit`

## 5. Verification

- [x] 5.1 Run full test suite: `uv run --with pytest env PYTHONPATH=src pytest -q tests/`
- [x] 5.2 Live test: call `get_metrics_slowest()`, `get_metrics_errors()`, `get_metrics_daily_trend()` via server
- [x] 5.3 Verify `~/.code-context-cache/metrics/daily/` contains today's snapshot
