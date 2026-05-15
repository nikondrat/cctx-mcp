## ADDED Requirements

### Requirement: replace_in_file tool
The system SHALL provide a `replace_in_file` tool for find-and-replace edits in existing files.

#### Scenario: Replace by exact string
- **WHEN** the user provides an exact `old_string` and `new_string` with `file_path`
- **THEN** the system replaces the first occurrence of `old_string` with `new_string` and returns a diff of the change

#### Scenario: Replace all occurrences
- **WHEN** the user sets `replace_all: true`
- **THEN** the system replaces every occurrence of `old_string` with `new_string`

#### Scenario: Regex replacement
- **WHEN** the user sets `use_regex: true` and provides a regex `old_string` and a replacement `new_string`
- **THEN** the system performs regex substitution and returns the diff

#### Scenario: Dry-run mode
- **WHEN** the user sets `dry_run: true`
- **THEN** the system returns the diff of what would change without writing to disk

### Requirement: Edit safety
The system SHALL guard against destructive edits and project-escape.

#### Scenario: File must be read first
- **WHEN** the user attempts to edit a file that has not been read via `smart_read` in this session
- **THEN** the system rejects the edit with a message instructing the user to read the file first

#### Scenario: Path traversal protection
- **WHEN** the `file_path` resolves to a location outside the project root
- **THEN** the system rejects the edit with a security warning

#### Scenario: Old string not found
- **WHEN** the `old_string` is not found in the file content
- **THEN** the system returns a clear error indicating no match found, listing nearby content for context
