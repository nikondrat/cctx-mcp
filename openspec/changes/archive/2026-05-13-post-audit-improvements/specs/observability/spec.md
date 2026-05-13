## MODIFIED Requirements

### Requirement: Tool calls are instrumented for latency and errors
The system SHALL record every MCP tool invocation with timestamp, tool name, latency, and success/error status to a persistent JSONL events log at `~/.code-context-cache/metrics/events.jsonl`.

#### Scenario: All tools are instrumented via decorator
- **WHEN** any MCP tool function is called (e.g., `find_files`, `smart_read`, `semantic_search`)
- **THEN** the metrics system SHALL record the tool name, latency in milliseconds, and whether the call succeeded or errored
- **AND** the event SHALL be appended to `events.jsonl` as a single JSON line per call

#### Scenario: Events are visible via get_metrics_events tool
- **WHEN** the user calls `get_metrics_events(limit=25)`
- **THEN** the response SHALL contain the most recent tool-call events with fields: `ts`, `tool`, `latency_ms`, `ok`

### Requirement: Metrics report includes per-tool stats and usage hints
The `get_metrics_report` output SHALL include per-tool call counts, average latency, error counts, and actionable hints for optimizing tool usage.

#### Scenario: Report shows aggregated tool stats
- **WHEN** the user calls `get_metrics_report()`
- **THEN** the response SHALL include per-tool rows with call count, average latency, and error count

#### Scenario: Hints detect missing semantic_search in favor of code_search
- **WHEN** a session has >= 3 `code_search` calls and zero `semantic_search` calls
- **THEN** the report SHALL include a hint suggesting to use `semantic_search` first for natural-language queries

#### Scenario: Hints detect missing smart_read before raw reads
- **WHEN** a session has no `smart_read` calls but has file content searches
- **THEN** the report SHALL include a hint suggesting to use `smart_read` before raw file reads
