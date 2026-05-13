## Why

Agents currently get mostly structural context (symbols, signatures, dependencies) and still spend extra tokens/time inferring intent from raw code. Commit preparation is also expensive because cloud models inspect large git diffs directly instead of using compact local summaries. We need a tighter context+commit pipeline that improves relevance while reducing cost.

## What Changes

- Add cached semantic symbol summaries (purpose, behavior, key dependencies, confidence/source metadata) that are refreshed when code changes.
- Add a compact change-summary tool for git deltas so higher-level models can consume minimal, structured commit context.
- Add a local commit-drafting step that generates candidate commit messages from compact summaries; cloud model only approves/edits and triggers commit.
- Define prompt-rewriter as deferred follow-up work: only interactive clarification/confirmation flow, no automatic rewrite in this change.

## Capabilities

### New Capabilities
- `symbol-semantic-summaries`: Generate and cache concise semantic descriptions for symbols and expose them via MCP responses.
- `compact-change-intelligence`: Produce structured, low-token change summaries and local commit message drafts from staged/unstaged diffs.

### Modified Capabilities
- None.

## Impact

- Affected code: analyzers/cache/search/server layers, plus new local change-intelligence module.
- APIs: MCP tool outputs gain optional summary metadata; new tool(s) for compact diff summary and local commit draft.
- Dependencies/systems: local embedding/model runtime hooks (configurable), cache versioning, and invalidation strategy tied to file/symbol hashes.
- Workflow: commit flow shifts from cloud-heavy diff inspection to local summarization + cloud confirmation.
