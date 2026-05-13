## Why

When an AI agent edits server code (e.g., fixes a bug in `_execute_commit`), the running MCP server process still has the old code — but neither the agent nor the user knows this. The agent calls `approve_commit_draft`, it fails silently, and the user is confused. There's no feedback loop to detect server staleness.

## What Changes

- Add `SERVER_VERSION` constant to `server.py` with semver string
- Add `get_version()` MCP tool that returns the current server version
- Define version bump protocol: after editing any source file, the agent bumps `SERVER_VERSION`
- Add staleness detection: agent calls `get_version()` after making source changes, compares with expected version, and prompts the user to restart if mismatch
- Update AGENTS.md with the version protocol as a mandatory step after code edits

## Capabilities

### New Capabilities

- `server-version`: Expose server version via `get_version()` tool, including version string, build timestamp, and git commit hash
- `staleness-detection`: Protocol for AI agents to detect stale server code and prompt user restart

### Modified Capabilities

- (none)

## Impact

- `src/server.py`: add `SERVER_VERSION`, `BUILD_TIMESTAMP`, `GIT_COMMIT` constants + `get_version()` tool
- `AGENTS.md`: new section "Server Version Protocol" detailing staleness detection flow
