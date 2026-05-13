## ADDED Requirements

### Requirement: Tool calls log baseline alternative operation
Each instrumented tool SHALL log what native operation it replaces, enabling analysis of "with vs without" the tool.

#### Scenario: tool logs baseline operation type
- **WHEN** `smart_read` is called
- **THEN** the event SHALL include `baseline_op: "read_file"` and `baseline_estimate_tokens: <estimated file size in tokens>`

#### Scenario: aggregated comparison available
- **WHEN** `get_metrics_report` is called
- **THEN** the report SHALL include a comparison section showing per-tool: `calls`, `total_baseline_tokens`, `total_actual_tokens`, `total_savings`, `avg_savings_per_call`

#### Scenario: savings shown as percentage
- **WHEN** `get_metrics_daily_trend` displays savings
- **THEN** each tool SHALL show `savings_pct` = `(tokens_baseline - tokens_output) / tokens_baseline × 100`

### Requirement: Savings factor is data-driven, not hardcoded
The `TOOL_SAVINGS_FACTOR` dict SHALL be replaced by computed averages from real data.

#### Scenario: factor computed from last 7 days
- **WHEN** calculating savings factor for a tool
- **THEN** the factor SHALL be the 7-day rolling average of `savings_tokens / tokens_baseline`
- **AND** SHALL be available via `get_metrics_report`
