## ADDED Requirements

### Requirement: Agent detects stale server and prompts restart
After bumping `SERVER_VERSION`, the agent SHALL call `get_version()` and compare the returned version with the expected version. If they differ, the server is stale and the agent SHALL inform the user.

#### Scenario: Agent detects stale version
- **WHEN** the agent bumps `SERVER_VERSION` from `0.1.0` to `0.1.1`
- **AND** calls `get_version()` which returns `"0.1.0"`
- **THEN** the agent SHALL inform the user: "Server is running stale code (v0.1.0, expected v0.1.1). Please restart opencode to pick up changes."

#### Scenario: Agent confirms server is current
- **WHEN** the agent bumps `SERVER_VERSION` and calls `get_version()`
- **AND** the returned version matches the expected version
- **THEN** the agent MAY proceed with the next step

### Requirement: AGENTS.md documents version protocol
AGENTS.md SHALL contain a section describing the server version protocol, including bump policy, staleness check, and restart prompt.

#### Scenario: Protocol section exists
- **WHEN** an agent reads AGENTS.md
- **THEN** it SHALL find instructions to bump `SERVER_VERSION` after source edits
- **AND** SHALL find instructions to call `get_version()` and compare versions
- **AND** SHALL find instructions to prompt user for restart on mismatch
