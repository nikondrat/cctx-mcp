## ADDED Requirements

### Requirement: get_metrics_slowest returns top-N tools by latency
The system SHALL provide a tool `get_metrics_slowest(limit: int = 5)` that returns the N slowest MCP tools ranked by average latency, including error count per tool.

#### Scenario: Returns tools sorted by avg latency descending
- **WHEN** the user calls `get_metrics_slowest(limit=3)`
- **THEN** the response SHALL contain at most 3 tools, sorted by average latency (highest first)
- **AND** each entry SHALL include: tool name, call count, total latency, error count, avg latency

#### Scenario: Returns empty list when no metrics recorded
- **WHEN** the user calls `get_metrics_slowest()` with no events in the log
- **THEN** the response SHALL indicate no data available

### Requirement: get_metrics_errors returns error summary
The system SHALL provide a tool `get_metrics_errors()` that returns all tools with at least one recorded error, plus the overall error rate across all tools.

#### Scenario: Returns tools with errors and error rate
- **WHEN** the user calls `get_metrics_errors()` and events exist with errors
- **THEN** the response SHALL list each tool with non-zero errors
- **AND** SHALL include total calls, total errors, and error rate percentage
