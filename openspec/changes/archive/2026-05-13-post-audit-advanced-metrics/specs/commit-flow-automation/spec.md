## ADDED Requirements

### Requirement: AGENTS.md enforces MCP commit flow as mandatory
The AGENTS.md SHALL contain a section "## Commit Flow — ABSOLUTE REQUIREMENT" with MUST-level language. It SHALL specify that agents MUST use `compact_change_intelligence` → `draft_commit` → `approve_commit_draft` for ALL git commit operations, with a documented fallback for when the MCP server is unavailable.

#### Scenario: Commit flow section exists with mandatory language
- **WHEN** an agent reads AGENTS.md
- **THEN** the "Commit Flow" section SHALL contain MUST-level language requiring `compact_change_intelligence`, `draft_commit`, and `approve_commit_draft`
- **AND** SHALL explicitly forbid direct `git commit` without going through this flow

#### Scenario: Fallback strategy documented
- **WHEN** the MCP server returns an error for `compact_change_intelligence` or `draft_commit`
- **THEN** the documented fallback SHALL be: use `approve_commit_draft(project_path, message="...")` with a manually written conventional commit message
- **AND** SHALL NOT fall back to bash `git commit`

### Requirement: Test validates AGENTS.md commit flow section
The system SHALL have a test `tests/test_commit_flow.py` that parses AGENTS.md and verifies the commit flow section contains the required tool names and mandatory language.

#### Scenario: Test checks for required tool names
- **WHEN** running `tests/test_commit_flow.py`
- **THEN** the test SHALL verify AGENTS.md contains strings `compact_change_intelligence`, `draft_commit`, `approve_commit_draft`
- **AND** SHALL verify the section header contains `ABSOLUTE REQUIREMENT`

#### Scenario: Test fails if commit flow section missing
- **WHEN** AGENTS.md lacks the mandatory commit flow section
- **THEN** the test SHALL fail with a descriptive error message
