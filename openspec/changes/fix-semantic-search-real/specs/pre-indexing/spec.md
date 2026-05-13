## ADDED Requirements

### Requirement: Vector index is pre-built at server startup
The server SHALL automatically build the vector index for the configured project before starting to accept MCP tool calls. This ensures the first `semantic_search` call is fast.

#### Scenario: Index builds on server start
- **WHEN** the MCP server starts
- **THEN** `VectorIndex.index_project()` SHALL be called before `mcp.run()`
- **AND** the server SHALL NOT accept tool calls until index build completes (or times out)

#### Scenario: Index build timeout
- **WHEN** index build exceeds 30 seconds
- **THEN** the server SHALL proceed to start anyway (lazy index)
- **AND** `vector_index.status` in health check SHALL be `"not_built"`

#### Scenario: Skip index via CLI flag
- **WHEN** the server is started with `--skip-index` flag
- **THEN** pre-indexing SHALL be skipped
- **AND** index SHALL be built lazily on first `semantic_search` call (current behavior)

### Requirement: CLI command for manual pre-indexing
The system SHALL provide a CLI command `uv run pre-index` to manually build the vector index for a project.

#### Scenario: CLI builds index and exits
- **WHEN** user runs `uv run pre-index /path/to/project`
- **THEN** the system SHALL build the vector index and save it to disk
- **AND** exit with code 0 on success, non-zero on error

#### Scenario: CLI shows progress
- **WHEN** `uv run pre-index` is building the index
- **THEN** the CLI SHALL print progress per file (e.g., "src/server.py... 12 chunks")
- **AND** SHALL print total summary at the end
