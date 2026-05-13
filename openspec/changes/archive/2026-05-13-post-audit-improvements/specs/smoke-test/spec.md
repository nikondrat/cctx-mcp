## ADDED Requirements

### Requirement: MCP server starts and responds to tool calls
The smoke test SHALL start the MCP server as a subprocess via `uv run python -m src.server`, wait for it to be ready, and perform basic tool calls via JSON-RPC over stdio.

#### Scenario: Server starts and responds to find_symbols
- **WHEN** the MCP server subprocess is launched and ready
- **THEN** a JSON-RPC request for `find_symbols` with a known project path SHALL return a valid response with `result` containing a list of symbols

#### Scenario: Server responds to semantic_search with empty result
- **WHEN** the MCP server subprocess is launched with no Ollama available and no CC_OPENROUTER_API_KEY
- **THEN** a JSON-RPC request for `semantic_search` SHALL return an error message indicating the service is unavailable, not crash or hang

#### Scenario: Six core tools respond without exception
- **WHEN** calling each of the six core MCP tools (`find_symbols`, `semantic_search`, `code_search`, `smart_read`, `get_config`, `get_metrics_report`)
- **THEN** each tool SHALL return a non-empty string response without raising an exception

#### Scenario: Test is skipped when uv is not in PATH
- **WHEN** the smoke test detects that `shutil.which("uv")` returns None
- **THEN** the test SHALL be skipped with `unittest.SkipTest` and a message explaining uv is required
