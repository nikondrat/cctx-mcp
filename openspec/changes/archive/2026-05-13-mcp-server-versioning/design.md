## Context

The MCP server runs as a subprocess of the AI client (opencode). When the server's source code is modified (e.g., bug fixes, new tools), the running process still has the old code. There is currently no mechanism to detect this mismatch — the agent silently calls stale tools, gets failures, and neither agent nor user understands why.

## Goals / Non-Goals

**Goals:**
- Expose server version via a `get_version()` MCP tool
- Include version string, git commit hash, and build timestamp in the response
- Define a clear protocol: after editing source files, agent bumps version and checks for staleness
- Document the protocol in AGENTS.md so all agents follow the same flow

**Non-Goals:**
- Auto-restart the MCP server from within opencode (not possible via MCP protocol)
- Block tool calls when server is stale (informative only — agent decides what to do)
- Version pinning or compatibility checks between agent and server

## Decisions

1. **Version source**: Hardcoded `SERVER_VERSION` in `server.py`. Semver string (`MAJOR.MINOR.PATCH`). Git commit hash is read dynamically at import time via `subprocess.run(["git", "rev-parse", "HEAD"])`. Two sources give both human-readable and machine-verifiable identity.

2. **get_version() output format**: JSON string for machine readability:

   ```json
   {"version": "0.2.0", "commit": "abc123", "built": "2026-05-13T20:00:00"}
   ```

   Agent can parse this and compare `version` with expected value.

3. **Version bump policy**: Agent bumps `PATCH` for bug fixes, `MINOR` for new features (tools), `MAJOR` for breaking changes. After bumping, agent immediately calls `get_version()`. If mismatch → user asked to restart.

4. **No persistent state**: Version lives in source code only. No separate version file. This keeps it simple and avoids sync issues.

## Risks / Trade-offs

- **Git hash unavailable** → If git is not installed or not a git repo, `GIT_COMMIT` defaults to `"unknown"`. get_version() still works, but staleness detection is less precise.
- **Agent must remember to bump** → Protocol is documented as MUST in AGENTS.md, but compliance is best-effort. The version check provides a safety net: if agent bumps but server is stale, the check catches it. If agent doesn't bump at all, staleness goes undetected.
