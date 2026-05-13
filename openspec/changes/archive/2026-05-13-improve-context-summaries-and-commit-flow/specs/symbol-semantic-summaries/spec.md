## ADDED Requirements

### Requirement: Symbol semantic summaries MUST be available as structured metadata
The system MUST provide a concise semantic summary for analyzed symbols, including purpose, primary behavior, and key dependencies, in a structured response format that can be consumed by agents without reading full source files.

#### Scenario: Summary returned for known symbol
- **WHEN** a client requests symbol information for a symbol that has summary data available
- **THEN** the response includes a semantic summary object with summary text and related dependency/context fields

### Requirement: Semantic summaries MUST carry provenance and confidence
The system MUST include summary provenance metadata (`source`) and confidence metadata (`confidence`) for every semantic summary so downstream consumers can decide trust level and fallback behavior.

#### Scenario: Provenance fields present
- **WHEN** a semantic summary is returned
- **THEN** the payload includes `source`, `confidence`, and `last_updated` metadata fields

### Requirement: Summary cache MUST invalidate on code or model evolution
The system MUST invalidate or regenerate cached symbol summaries whenever symbol content changes or summary/analyzer versions change.

#### Scenario: Invalidate after code update
- **WHEN** a symbol's underlying file hash changes
- **THEN** previously cached summary entries for that symbol are not reused and a fresh summary is generated before returning

#### Scenario: Invalidate after analyzer or model update
- **WHEN** summary generation version metadata differs from cached entry metadata
- **THEN** the cached summary is treated as stale and replaced with a summary generated under current versions
