## ADDED Requirements

### Requirement: semantic_search degrades gracefully when both providers are unavailable
The `semantic_search` tool SHALL never raise an unhandled exception when both Ollama and OpenRouter are unavailable. It SHALL return a descriptive message explaining why the service is unavailable.

#### Scenario: Both Ollama down and OpenRouter missing API key
- **WHEN** the LLMRouter is configured with `local-first` mode
- **AND** Ollama is unreachable (connection refused or timeout)
- **AND** CC_OPENROUTER_API_KEY is not set
- **WHEN** a user calls `semantic_search(query="test")`
- **THEN** the tool SHALL return a string starting with `semantic_search unavailable` or `semantic_search error:`
- **AND** SHALL NOT raise an unhandled RuntimeError or similar exception

#### Scenario: Embedding fails mid-query with provider unavailable
- **WHEN** the vector index is loaded from disk
- **AND** the router returns an LLMResponse with `error_reason` for the query embedding
- **THEN** `semantic_search` SHALL catch the error at `server.py:448` and return a human-readable error message
