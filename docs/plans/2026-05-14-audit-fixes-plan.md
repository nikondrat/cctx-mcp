# Audit Fixes Plan

Date: 2026-05-14
Server version: 0.5.0
Commit: 93f6f0d

## Status: 8/11 completed

| # | Priority | Area | Status |
|---|----------|------|--------|
| P1 | HIGH | Test pollution of production metrics | ✅ Done |
| P2 | HIGH | N+1 embedding → batch /api/embed | ✅ Done |
| P3 | HIGH | Query embed LRU cache | ✅ Done |
| P4 | MEDIUM | Remove force-reindex on provider mismatch | ✅ Done |
| P5 | HIGH | Retry/backoff on embed failure | ✅ Done |
| P6 | LOW | Hardcoded baseline for token savings | ⏳ Pending |
| P7 | LOW | Wire cache hit/miss to metrics | ⏳ Pending |
| P8 | LOW | CC_OPENROUTER_TIMEOUT cross-provider fallback | ✅ Done |
| P9 | MEDIUM | Missing tests | ✅ Done |
| P10 | LOW | _file_hash full SHA256 | ✅ Done |
| P11 | LOW | Typo "Deduplicate" | ✅ No-op (spelling was correct) |

---

## Completed

### P1: Test pollution of production metrics

**Problem:** `Metrics.__init__()` always wrote to `events.jsonl`, 4 tests created
`Metrics()` without overriding path.

**Fix:**
- `Metrics.__init__(events_path: Optional[Path] = None)` — tests pass isolated path
- `CC_TEST_MODE` guard raises RuntimeError if no path provided in test mode
- All tests use `_metrics()` helper with `tempfile.mkdtemp()`
- Polluted data archived to `events.jsonl.bak`

**Files:** `metrics.py`, `tests/test_metrics.py`

### P2: Batch embedding

**Problem:** `index_project()` embedded one chunk per HTTP request (N+1).

**Fix:**
- `OllamaClient.embed_batch(model, texts)` — uses `/api/embed` (batched), falls
  back to per-item `/api/embeddings` on HTTP 404 (older Ollama)
- `OllamaProvider.embed_batch(texts, model)` → `list[LLMResponse]`
- `OpenRouterProvider.embed_batch(texts, model)` — OpenAI-compatible batched
  `/embeddings` with `input: [...]`
- `LLMRouter.embed_batch()` — routes to first available provider
- `VectorIndex.index_project()` — batches of 20 chunks

**Files:** `ollama_client.py`, `llm/contracts.py`, `llm/providers/ollama.py`,
`llm/providers/openrouter.py`, `llm/router.py`, `vector_index.py`

### P3: Query embed LRU cache

**Problem:** Repeated identical query text → N HTTP calls per search.

**Fix:** `VectorIndex.search()` caches query embeddings in
`OrderedDict` (max 100 entries, LRU eviction).

**Files:** `vector_index.py`

### P4: Removed force-reindex on provider mismatch

**Problem:** Query via different provider → full index rebuild.

**Fix:** Query embedding is used as-is against existing vectors. No reindex
on metadata mismatch.

**Files:** `vector_index.py`

### P5: Retry with exponential backoff

**Problem:** 30% error rate on semantic_search (Ollama timeouts).

**Fix:** `VectorIndex.search()` retries 3× with 1s/2s/4s backoff on
embed failure.

**Files:** `vector_index.py`

### P8: CC_OPENROUTER_TIMEOUT default

**Problem:** Fell back to `CC_OLLAMA_TIMEOUT`, cross-provider coupling.

**Fix:** Separate default of `"15"`.

**Files:** `config.py`

### P9: New tests (7 added, 45 total)

- `TestRegexExtractChunks` (3 tests): direct regex fallback, nested methods,
  unsupported language
- `TestChunkMarkdown` (2 tests): heading splitting, single section
- `TestOllamaClientEmbedBatch` (3 tests): success, 404 fallback, mismatch
- `test_query_cache_reuses_embeddings`

### P10: Full SHA256 file hash

**Problem:** `_file_hash` truncated SHA256 to 16 chars (64 bits).

**Fix:** Full `hexdigest()` (64 chars).

**Files:** `vector_index.py`

---

## Remaining

### P6: Hardcoded token savings baseline (LOW)

**Files:** `metrics.py`, `server.py`

Each tool reports `tokens_baseline` via `_tool_token_ctx`, but many tools
report 0. Audit all `@_instrument_tool` call sites.

### P7: Wire cache hit/miss to metrics (LOW)

**Files:** `server.py`, `search.py`

`get_cache().hit` / `get_cache().miss` exist but are never reported to
`get_metrics()`.
