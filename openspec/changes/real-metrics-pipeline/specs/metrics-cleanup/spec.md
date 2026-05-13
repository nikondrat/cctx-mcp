## ADDED Requirements

### Requirement: Old metric records are archived before migration
The system SHALL archive existing events and daily snapshots before applying the new schema.

#### Scenario: events.jsonl archived atomically
- **WHEN** the cleanup runs
- **THEN** `events.jsonl` SHALL be renamed to `events.jsonl.bak`
- **AND** a new empty `events.jsonl` SHALL be created
- **AND** old daily snapshots in `daily/` SHALL be moved to `daily/archive/`

#### Scenario: cleanup is idempotent
- **WHEN** cleanup runs but `events.jsonl` does not exist
- **THEN** it SHALL NOT fail
- **AND** SHALL still create a new empty `events.jsonl`

### Requirement: In-memory metrics reset after cleanup
The system SHALL reset in-memory counters after archiving old data.

#### Scenario: counters reset on cleanup
- **WHEN** cleanup completes
- **THEN** `cache_hit_rate`, `summary_count`, `draft_count`, and `_calls` SHALL be reset to zero or empty
- **AND** `get_metrics_report()` SHALL show no recorded calls

### Requirement: Cleanup is a callable MCP tool
The cleanup operation SHALL be exposed as an MCP tool.

#### Scenario: reset_metrics tool available
- **WHEN** `reset_metrics` MCP tool is called
- **THEN** it SHALL archive old events, reset counters, and return confirmation with archive location
