## ADDED Requirements

### Requirement: git_diff tool
The system SHALL provide a `git_diff` tool returning structured diff information.

#### Scenario: Unstaged diff
- **WHEN** the user calls `git_diff(project_path="/project")` without arguments
- **THEN** the system returns a structured JSON diff of unstaged changes (same format as `compact_change_intelligence` but accessible directly as `git_diff`)

#### Scenario: Staged diff
- **WHEN** the user calls `git_diff(project_path="/project", staged=True)`
- **THEN** the system returns a structured diff of staged changes only

#### Scenario: No changes
- **WHEN** there are no changes to report
- **THEN** the system returns `{"changes": [], "change_count": 0}`

### Requirement: git_log tool
The system SHALL provide a `git_log` tool returning recent commit history.

#### Scenario: Default log
- **WHEN** the user calls `git_log(project_path="/project")`
- **THEN** the system returns the last 10 commits with hash, author, date, and message

#### Scenario: Custom limit
- **WHEN** the user provides `limit=20`
- **THEN** the system returns up to 20 commits

### Requirement: git_status tool
The system SHALL provide a `git_status` tool returning working tree status.

#### Scenario: Working tree status
- **WHEN** the user calls `git_status(project_path="/project")`
- **THEN** the system returns a JSON object with `branch`, `staged` (list of files), `unstaged` (list of files), and `untracked` (list of files)
