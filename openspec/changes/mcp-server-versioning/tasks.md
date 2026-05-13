## 1. server.py — version constants and get_version() tool

- [x] 1.1 Add `SERVER_VERSION`, `GIT_COMMIT`, `BUILD_TIMESTAMP` constants to server.py
- [x] 1.2 Add `get_version() -> str` MCP tool that returns JSON with version, commit, built fields

## 2. AGENTS.md — version protocol documentation

- [x] 2.1 Add "Server Version Protocol" section: bump policy, staleness check, restart prompt
- [x] 2.2 Add red flag: "I just fixed the code, the server will pick it up" → version check catches staleness

## 3. Tests

- [x] 3.1 Create `tests/test_version.py` — verify `get_version()` returns valid JSON with expected fields
- [x] 3.2 Verify SERVER_VERSION matches expected format (semver)

## 4. Verification

- [x] 4.1 Run full test suite: 79 passed
- [x] 4.2 Bump version to `0.2.0` and commit
