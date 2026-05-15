## ADDED Requirements

### Requirement: investigate_symbol tool
The system SHALL provide a compound `investigate_symbol` tool that combines find-symbols, trace-calls, and smart-read in a single call.

#### Scenario: Full symbol investigation
- **WHEN** the user calls `investigate_symbol(name="AuthProvider.login", project_path="/project")`
- **THEN** the system returns a JSON object with: `definition` (find_symbols result), `usages` (trace_calls result), and `summary` (smart_read of the definition file, scoped to the symbol's line range)

#### Scenario: Symbol not found
- **WHEN** `investigate_symbol` cannot find the symbol in any file
- **THEN** the system returns `{"definition": null, "usages": [], "summary": null}` with a message indicating the symbol was not found

### Requirement: Compound tool response format
All compound tools SHALL return structured JSON responses with standardized fields.

#### Scenario: Response structure
- **WHEN** any compound tool completes
- **THEN** the response is a JSON object with a `results` key containing named sub-results, and a `latency_ms` key with per-sub-operation timing
