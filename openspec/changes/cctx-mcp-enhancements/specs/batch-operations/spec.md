## ADDED Requirements

### Requirement: batch_run tool
The system SHALL provide a `batch_run` tool that accepts an array of parameter sets for the same tool and returns an array of results.

#### Scenario: Batch search queries
- **WHEN** the user calls `batch_run(tool="code_search", params=[{"pattern": "foo"}, {"pattern": "bar"}], project_path="/project")`
- **THEN** the system returns an array of `code_search` results, one per input, in the same order

#### Scenario: Batch find_symbols queries
- **WHEN** the user calls `batch_run(tool="find_symbols", params=[{"name": "login"}, {"name": "logout"}], project_path="/project")`
- **THEN** the system returns an array of `find_symbols` results, one per input

### Requirement: Batch size limit
The `batch_run` tool SHALL enforce a configurable maximum batch size to prevent resource exhaustion.

#### Scenario: Exceeds max batch size
- **WHEN** the number of `params` exceeds the configured maximum (default 10)
- **THEN** the system rejects the call with an error message indicating the limit and how to increase it

#### Scenario: Single-item batch
- **WHEN** the `params` array contains exactly one item
- **THEN** the system returns a single-element array, consistent with multi-item behavior

### Requirement: Per-item error isolation
Errors in one batch item SHALL NOT affect other items.

#### Scenario: Partial failure
- **WHEN** one `params` item causes an error (e.g., file not found)
- **THEN** the system returns results for all other items, with the failed item containing an `error` field
