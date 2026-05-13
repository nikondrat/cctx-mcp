## ADDED Requirements

### Requirement: Record real token counts per tool call
The system SHALL record actual input and output token counts for every instrumented tool call, replacing the current static `TOOL_SAVINGS_FACTOR` estimation method.

#### Scenario: record_call stores token counts
- **WHEN** `record_call()` is called with `tokens_input=50`, `tokens_output=200`, `tokens_baseline=4000`
- **THEN** these values SHALL be persisted in the events.jsonl entry for that call
- **AND** the computed `savings_tokens` SHALL be `4000 - (50 + 200) = 3750`

#### Scenario: tool decorator forwards token counts
- **WHEN** `_instrument_tool` wraps a tool that reports `tokens_input`, `tokens_output`, `tokens_baseline`
- **THEN** these values SHALL be passed to `record_call()`

#### Scenario: daily snapshot uses real savings
- **WHEN** `_daily_snapshot()` aggregates today's events
- **THEN** total savings SHALL be sum of `savings_tokens` (computed as `tokens_baseline - tokens_input - tokens_output`) across all events, not `TOOL_SAVINGS_FACTOR × 1500 × calls`

#### Scenario: backward compatibility with old events
- **WHEN** `_daily_snapshot()` encounters old events without token fields
- **THEN** those events SHALL use `TOOL_SAVINGS_FACTOR × 1500` as fallback estimate
- **AND** SHALL be flagged with `estimate: true` in the snapshot

### Requirement: smart_read reports file-level token savings
The `smart_read` tool SHALL report token baseline equal to the full file size in tokens.

#### Scenario: smart_read measures file size as baseline
- **WHEN** `smart_read` reads a file with 100 lines
- **THEN** `tokens_baseline` SHALL be approximately `100 × 4 = 400` tokens

#### Scenario: smart_read measures result size as actual
- **WHEN** `smart_read` returns a 200-token structured analysis
- **THEN** `tokens_output` SHALL be `200`

### Requirement: semantic_search reports search-vs-grep savings
The `semantic_search` tool SHALL estimate baseline as the token count of what a grep-based approach would return.

#### Scenario: semantic_search estimates baseline
- **WHEN** `semantic_search` finds matches in 5 files
- **THEN** `tokens_baseline` SHALL estimate the token cost of grepping and reading snippets from those files
- **AND** `tokens_output` SHALL be the total characters of returned results / 4

### Requirement: code_search reports grep-equivalent savings
The `code_search` tool SHALL report baseline equal to the raw grep output for the same pattern.

#### Scenario: code_search measures baseline
- **WHEN** `code_search` finds 10 matches across 3 files
- **THEN** `tokens_baseline` SHALL be estimated as lines_matched × context_window_lines × 4 tokens/line
