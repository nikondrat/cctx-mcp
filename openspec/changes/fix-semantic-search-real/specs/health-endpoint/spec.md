## ADDED Requirements

### Requirement: get_health returns aggregated system status
The system SHALL provide a `get_health()` MCP tool that returns a JSON object with the status of all critical dependencies: Ollama, embedding model, vector index, tree-sitter, and server version.

#### Scenario: Returns full health report
- **WHEN** the agent calls `get_health()`
- **THEN** the response SHALL be a JSON string containing fields: `ollama`, `vector_index`, `tree_sitter`, `server`
- **AND** each field SHALL contain `status` ("ok" | "degraded" | "error")

#### Scenario: Ollama status reflects real availability
- **WHEN** Ollama is running and responds to API ping
- **THEN** `ollama.status` SHALL be `"ok"`
- **AND** `ollama.model` SHALL contain the detected embedding model name
- **AND** `ollama.latency_ms` SHALL be the ping latency

#### Scenario: Ollama unavailable
- **WHEN** Ollama is not running or connection refused
- **THEN** `ollama.status` SHALL be `"error"`
- **AND** `ollama.error` SHALL contain actionable message (e.g., "ollama не запущен. Запусти: ollama serve")

#### Scenario: Vector index status reflects build state
- **WHEN** vector index is built and loaded
- **THEN** `vector_index.status` SHALL be `"ok"`
- **AND** `vector_index.chunks` SHALL be the number of indexed chunks
- **AND** `vector_index.files` SHALL be the number of indexed files

#### Scenario: Vector index not built yet
- **WHEN** server just started and index is being built
- **THEN** `vector_index.status` SHALL be `"building"` or `"not_built"`

#### Scenario: Health check timeout safety
- **WHEN** Ollama ping exceeds 2 seconds
- **THEN** health check SHALL timeout and report `ollama.status` as `"degraded"`
- **AND** SHALL NOT block the MCP tool response
