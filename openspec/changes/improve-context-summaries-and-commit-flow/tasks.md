## 1. Semantic summary data model and cache lifecycle

- [ ] 1.1 Define semantic summary schema (summary text, purpose/behavior fields, dependencies, source, confidence, last_updated).
- [ ] 1.2 Extend cache key/version strategy to include symbol identity, file hash, analyzer version, and summary model version.
- [ ] 1.3 Implement cache invalidation triggers for file content changes and analyzer/model version changes.
- [ ] 1.4 Add cache bounds/eviction and stale-entry cleanup hooks for summary entries.

## 2. Summary generation and MCP integration

- [ ] 2.1 Implement lazy summary generation path that runs only for requested symbols or explicitly requested files.
- [ ] 2.2 Add summary provenance/confidence population rules (doc/heuristic/model) with deterministic fallback behavior.
- [ ] 2.3 Expose summary metadata in MCP tool responses (smart read / symbol-oriented endpoints) behind a compatibility-safe response extension.
- [ ] 2.4 Add regression tests validating summary presence, provenance fields, and fallback to structural context when summary is unavailable.

## 3. Compact change-intelligence tooling

- [ ] 3.1 Implement a compact git-delta summarizer that returns structured change intelligence (files, change types, intent cues).
- [ ] 3.2 Add repository hygiene filters to keep summaries compact (ignore noise paths and non-relevant generated artifacts).
- [ ] 3.3 Define and document a stable JSON contract for compact change output consumed by local drafting.
- [ ] 3.4 Add tests for representative change sets (single-file fix, multi-module feature, refactor-heavy update).

## 4. Local commit drafting and gated commit flow

- [ ] 4.1 Implement local commit draft generation from compact change intelligence with candidate message + short rationale.
- [ ] 4.2 Add confidence scoring and fallback behavior when local model/runtime is unavailable.
- [ ] 4.3 Integrate cloud/user approval-edit gate so commit creation cannot proceed without explicit approval.
- [ ] 4.4 Add integration tests for end-to-end flow: summarize → local draft → cloud/user approve/edit → commit command execution.

## 5. Rollout, observability, and deferred prompt-rewriter tracking

- [ ] 5.1 Add feature flags/config for semantic summaries and local commit drafting to allow incremental rollout.
- [ ] 5.2 Add metrics/logging for latency, cache hit rate, token reduction, and draft-acceptance rate.
- [ ] 5.3 Add operator documentation for enabling/disabling local model components and troubleshooting fallbacks.
- [ ] 5.4 Create a follow-up backlog item/change stub for interactive prompt clarification-rewriter (explicitly out of scope here).
