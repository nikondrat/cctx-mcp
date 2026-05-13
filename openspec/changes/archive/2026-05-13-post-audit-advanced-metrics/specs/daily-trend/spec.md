## ADDED Requirements

### Requirement: Daily snapshot is persisted on first daily tool call
The system SHALL automatically create a daily snapshot at `~/.code-context-cache/metrics/daily/YYYY-MM-DD.json` on the first call to any metrics tool on a new calendar day.

#### Scenario: First call creates today's snapshot
- **WHEN** `get_metrics_daily_trend()` is called for the first time today
- **THEN** the system SHALL read all events from `events.jsonl` with today's timestamp
- **AND** SHALL write `daily/YYYY-MM-DD.json` with aggregated per-tool stats
- **AND** SHALL estimate token savings per tool using predefined savings factors

#### Scenario: Subsequent calls read from cached file
- **WHEN** `get_metrics_daily_trend()` is called again on the same day
- **THEN** the system SHALL read from `daily/YYYY-MM-DD.json` without re-processing events

### Requirement: get_metrics_daily_trend returns multi-day trend
The system SHALL provide a tool `get_metrics_daily_trend(days: int = 7)` that returns daily snapshots for the last N days, showing call volume, latency, and estimated token savings trend.

#### Scenario: Returns trend for last N days
- **WHEN** the user calls `get_metrics_daily_trend(days=3)`
- **THEN** the response SHALL contain up to 3 daily snapshots with date, per-tool stats, and total estimated token savings

#### Scenario: Handles missing days gracefully
- **WHEN** some days in the range have no snapshot file
- **THEN** those days SHALL be reported as "no data" rather than causing an error
