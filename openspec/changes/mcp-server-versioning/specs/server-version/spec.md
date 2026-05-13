## ADDED Requirements

### Requirement: Server exposes version via get_version() tool
The system SHALL provide a `get_version()` MCP tool that returns the current server version, git commit hash, and build timestamp.

#### Scenario: Returns version info as JSON
- **WHEN** the agent calls `get_version()`
- **THEN** the response SHALL be a JSON string containing `version` (semver), `commit` (git hash), and `built` (ISO timestamp)
- **AND** the version SHALL match the `SERVER_VERSION` constant in `server.py`

#### Scenario: Git hash defaults to "unknown" when unavailable
- **WHEN** `git rev-parse HEAD` fails (no git, no repo, or error)
- **THEN** the commit field SHALL be `"unknown"`
- **AND** the tool SHALL still return version and built fields normally

### Requirement: SERVER_VERSION is bumped after source edits
The `SERVER_VERSION` constant in `server.py` SHALL be incremented after every source code edit. Patch for bug fixes, minor for new features, major for breaking changes.

#### Scenario: Agent bumps after edit
- **WHEN** the agent modifies any file in `src/`
- **THEN** the agent SHALL increment the patch version (or minor/major as appropriate)
- **AND** SHALL immediately call `get_version()` to check staleness
