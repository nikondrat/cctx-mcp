## ADDED Requirements

### Requirement: Integration test validates real semantic_search quality
The system SHALL have an integration test that starts the MCP server via subprocess, calls `semantic_search` with real queries, and validates result relevance by score and expected file matches.

#### Scenario: Test runs 5 queries against code-context project
- **WHEN** the integration test starts the MCP server and calls `semantic_search` with 5 pre-defined queries
- **THEN** each query SHALL return at least one result with score >= 0.7
- **AND** each query SHALL return the expected file in top-3 results

#### Scenario: Test queries and expected results
- **WHEN** query is "vector index search class"
- **THEN** `src/vector_index.py` SHALL be in top-3 results with score >= 0.7
- **WHEN** query is "project search find symbols"
- **THEN** `src/search.py` SHALL be in top-3 results with score >= 0.7
- **WHEN** query is "git commit change summary"
- **THEN** `src/change_intel.py` SHALL be in top-3 results with score >= 0.7
- **WHEN** query is "semantic summaries get_symbol_summaries"
- **THEN** `src/summaries.py` or `src/server.py` SHALL be in top-3 results with score >= 0.7
- **WHEN** query is "MCP tool decorator instrumentation"
- **THEN** `src/server.py` SHALL be in top-3 results with score >= 0.7

#### Scenario: Test is skipped when Ollama unavailable
- **WHEN** `get_health()` returns `ollama.status != "ok"`
- **THEN** the test SHALL be skipped with clear message

#### Scenario: Test builds index first
- **WHEN** the test starts
- **THEN** it SHALL ensure the vector index is built (call `semantic_search` with warmup query first)
- **AND** SHALL wait for index to be ready before running quality queries
