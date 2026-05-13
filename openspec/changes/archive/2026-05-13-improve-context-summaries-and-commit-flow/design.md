## Context

The current MCP server is strong at structural analysis (symbols, dependencies, file discovery) but weak at fast semantic recall: agents still need to open and interpret raw code to understand intent. In parallel, commit preparation currently relies on expensive cloud-side diff reading, which increases latency and token cost. This change introduces a local-first enrichment layer (semantic summaries + compact change intelligence) while keeping cloud models in a supervisory role for final approval.

## Goals / Non-Goals

**Goals:**
- Add durable, cacheable semantic summaries for symbols that improve context quality without forcing full file reads.
- Ensure summaries auto-refresh when relevant code changes (no stale semantic metadata).
- Add a compact, structured git-delta summary path suitable for local commit-draft generation.
- Keep prompt-rewriter work explicitly deferred and tracked as follow-up.

**Non-Goals:**
- No autonomous commit execution without cloud/user approval.
- No fully generic semantic search platform across arbitrary external repos in this change.
- No automatic prompt rewriting pipeline in this change.

## Decisions

1. **Semantic summary generation is lazy + cached, not eager for entire repositories.**
   - **Why:** avoids expensive upfront indexing and keeps cost proportional to real agent usage.
   - **Alternative considered:** full-repo precompute on startup (faster reads later, but high startup cost and stale-data pressure).

2. **Cache keys include content/version dimensions (`symbol_id`, `file_hash`, `analyzer_version`, `summary_model_version`).**
   - **Why:** guarantees invalidation on parser or model upgrades and any symbol-level code edits.
   - **Alternative considered:** time-based TTL only (simpler, but allows stale summaries and non-deterministic refresh behavior).

3. **Summary provenance is first-class (`source`, `confidence`, `last_updated`).**
   - **Why:** downstream agents can trust and prioritize context based on certainty.
   - **Alternative considered:** opaque summary text only (smaller payload, but weaker reliability controls).

4. **Compact change intelligence is a dedicated module/tool, not embedded in generic `git diff` handling.**
   - **Why:** enables stable JSON contracts for local commit draft models and keeps cloud interactions minimal.
   - **Alternative considered:** continue raw git operations from cloud model (lowest implementation effort, highest recurring token cost).

5. **Local commit drafting outputs candidate message + rationale + confidence, while cloud model remains gatekeeper.**
   - **Why:** balances cost reduction with safety and style consistency.
   - **Alternative considered:** local model commits directly (cheaper but higher risk of wrong scope/style without oversight).

## Risks / Trade-offs

- **[Risk] Summary quality drift across languages/frameworks** → **Mitigation:** start with conservative templates + provenance/confidence; allow fallback to structural context.
- **[Risk] Cache growth and stale entries** → **Mitigation:** bounded cache size, eviction policy, and periodic cleanup hooks.
- **[Risk] Local model availability/performance variability** → **Mitigation:** feature flag + graceful fallback path (cloud-only commit prep).
- **[Risk] Commit draft may miss subtle intent from large refactors** → **Mitigation:** include touched-module and change-type signals; require cloud/user approval before commit.
