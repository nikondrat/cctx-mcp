## ADDED Requirements

### Requirement: All MCP tools have unit tests
Every MCP tool exposed by the server SHALL have at least one unit test verifying its behavior.

#### Scenario: analyze_project has unit tests
- **WHEN** `analyze_project` is called with a valid project path
- **THEN** the response SHALL contain project name, file count, and language breakdown
- **WHEN** called with a non-existent path
- **THEN** the response SHALL contain "Error: Project not found"

#### Scenario: code_search has unit tests
- **WHEN** `code_search` is called with a pattern that matches files
- **THEN** results SHALL contain file paths and line numbers with matched content
- **WHEN** called with a non-matching pattern
- **THEN** the response SHALL contain "No matches found"

#### Scenario: find_files has unit tests
- **WHEN** `find_files` is called with an extension filter
- **THEN** results SHALL only include files with that extension
- **WHEN** called with no matching files
- **THEN** the response SHALL contain "No files found"

#### Scenario: dir_summary has unit tests
- **WHEN** `dir_summary` is called with depth=1
- **THEN** the response SHALL show file counts by type and total size
- **WHEN** called with a non-existent subdirectory
- **THEN** the response SHALL handle it gracefully

#### Scenario: get_dependencies has unit tests
- **WHEN** `get_dependencies` is called on a Python file with imports
- **THEN** the response SHALL include imported modules

### Requirement: trace_calls has integration tests
The `trace_calls` tool SHALL have integration tests that verify it finds cross-file symbol usage.

#### Scenario: trace_calls finds cross-file references
- **WHEN** `trace_calls` searches for a function defined in file A and used in file B
- **THEN** the response SHALL include the usage in file B with correct line numbers

### Requirement: All get_metrics tools have unit tests
Every metrics-related MCP tool SHALL have unit tests.

#### Scenario: get_metrics_events returns events
- **WHEN** `get_metrics_events` is called with events recorded
- **THEN** it SHALL return recent events sorted by timestamp

#### Scenario: get_metrics_slowest returns sorted tools
- **WHEN** `get_metrics_slowest` is called
- **THEN** it SHALL return tools sorted by average latency descending
