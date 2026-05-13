## ADDED Requirements

### Requirement: semantic_search never raises unhandled exceptions
The `semantic_search` tool SHALL never propagate RuntimeError or other exceptions to the MCP transport. All errors SHALL be caught and converted to descriptive string messages.

#### Scenario: Ollama connection refused
- **WHEN** Ollama is not running (connection refused)
- **AND** OpenRouter API key is not configured
- **THEN** `semantic_search` SHALL return: "semantic_search unavailable: Ollama не отвечает (http://localhost:11434). Решение: запусти 'ollama serve'"
- **AND** SHALL NOT crash the server

#### Scenario: Embedding model not found
- **WHEN** the configured embedding model (e.g., `nomic-embed-text`) is not pulled in Ollama
- **THEN** `semantic_search` SHALL return: "semantic_search unavailable: модель 'nomic-embed-text' не найдена. Решение: запусти 'ollama pull nomic-embed-text'"

#### Scenario: Index not yet built
- **WHEN** `semantic_search` is called but the vector index has not been built yet (pre-index skipped or timeout)
- **THEN** the system SHALL build the index synchronously (lazy init, current behavior)
- **AND** return results after index build completes
- **AND** if index build fails, return descriptive error message

### Requirement: RuntimeError in vector_index.py is replaced with graceful return
The `VectorIndex.search()` method SHALL NOT raise `RuntimeError` under any error condition. Instead SHALL return an empty list and set `_last_error`.

#### Scenario: Embedding failure returns empty list
- **WHEN** `router.embed()` returns an error response
- **THEN** `search()` SHALL NOT raise RuntimeError
- **AND** SHALL return an empty list
- **AND** SHALL set `self._last_error` to the error description

#### Scenario: Empty query handled gracefully
- **WHEN** `semantic_search` is called with an empty or whitespace-only query
- **THEN** the tool SHALL return "empty query" message
- **AND** SHALL NOT attempt embedding or search
