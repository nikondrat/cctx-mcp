## ADDED Requirements

### Requirement: smart_read with offset and limit
The `smart_read` tool SHALL support optional `offset` and `limit` parameters for line-range control.

#### Scenario: Read with line range
- **WHEN** the user calls `smart_read(file_path="foo.py", offset=10, limit=20)`
- **THEN** the system returns the smart_read analysis scoped to lines 10–29

#### Scenario: Read beyond file length
- **WHEN** the `offset` exceeds the file length
- **THEN** the system returns an empty analysis with a message indicating the offset is beyond the file

### Requirement: smart_read with symbol targeting
The `smart_read` tool SHALL support a `symbol` parameter to scope analysis to a specific symbol.

#### Scenario: Read by symbol name
- **WHEN** the user calls `smart_read(file_path="foo.py", symbol="AuthProvider.login")`
- **THEN** the system returns smart_read analysis scoped to the definition range of that symbol (class/method/function)

#### Scenario: Symbol not found in file
- **WHEN** the specified `symbol` is not found in the file
- **THEN** the system returns the full analysis with a message that the symbol was not found

### Requirement: Backward compatibility
The `smart_read` tool SHALL maintain backward compatibility when no new parameters are used.

#### Scenario: Default behavior unchanged
- **WHEN** the user calls `smart_read(file_path="foo.py")` without offset, limit, or symbol
- **THEN** the system returns the full analysis, identical to current behavior
