## 1. Fallback Reliability — Graceful Degrade

- [x] 1.1 Verify `vector_index.py:233-234` — confirm `_run_embed` raises `RuntimeError(error_reason)` not empty list when router.embed returns error
- [x] 1.2 Verify `server.py:448` try/except catches RuntimeError from `index.search()` and returns `semantic_search error:` text
- [x] 1.3 Add unit test in `tests/test_vector_index.py` for search when `router.embed` returns `LLMResponse(error_reason=...)`
- [x] 1.4 Add integration test in `tests/test_integration.py` for semantic_search with both Ollama unreachable and OpenRouter API key missing

## 2. Smoke Test — MCP Server Integration

- [x] 2.1 Create `tests/test_smoke_server.py`: launch server via `uv run python -m src.server` as subprocess, detect ready signal on stdio
- [x] 2.2 Skip test if `shutil.which("uv")` is None with descriptive message
- [x] 2.3 Validate `find_symbols` via JSON-RPC returns a list for the code-context project itself
- [x] 2.4 Validate `semantic_search` returns unavailable message when both Ollama and OpenRouter are down
- [x] 2.5 Validate six core tools (`find_symbols`, `semantic_search`, `code_search`, `smart_read`, `get_config`, `get_metrics_report`) respond without exception

## 3. Final Commits

- [x] 3.1 Commit 1 — `feat(llm):` LLM domain layer + routing + all LLM tests: llm/ contracts, providers, router; commit_generator, vector_index, config, server routing wiring; test_openrouter_provider.py, test_llm_router.py
- [x] 3.2 Commit 2 — `feat(observability):` metrics instrumentation decorator, get_metrics_events tool, test_metrics.py, AGENTS.md observability docs
- [x] 3.3 Commit 3 — `fix(audit):` trace_calls dotted-symbol resolution in search.py, test_search_trace_calls.py, AGENTS.md trace_calls docs

## 4. tree-sitter Bootstrap

- [x] 4.1 Run `uv sync` and verify tree-sitter installs cleanly
- [x] 4.2 Verify `uv run python -c "import tree_sitter; print(tree_sitter.__version__)"` prints a version
- [x] 4.3 Run full test suite `uv run --with pytest pytest tests/` — confirm all tests pass including test_summaries.py

## 5. Verification

- [x] 5.1 Run full test suite: `uv run --with pytest pytest tests/`
- [x] 5.2 Confirm `git status` shows clean working tree (zero modified, zero untracked)
- [x] 5.3 Confirm `git log --oneline` shows exactly 3 conventional commits: feat(llm), feat(observability), fix(audit)
