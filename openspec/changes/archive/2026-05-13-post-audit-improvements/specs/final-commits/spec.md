## ADDED Requirements

### Requirement: All changes are committed with conventional commit messages
All changes from the LLM routing implementation + observability wiring + audit fixes SHALL be committed to git with proper Conventional Commits format: `type(scope): description`.

#### Scenario: LLM routing changes committed as feat(llm)
- **WHEN** committing the LLM domain layer (`src/llm/`, `src/commit_generator.py`, `src/vector_index.py`, `src/config.py`, `src/server.py` routing changes)
- **AND** all LLM-related test files (`test_openrouter_provider.py`, `test_llm_router.py`)
- **THEN** the commit message SHALL use type `feat(llm):` with a description

#### Scenario: Observability changes committed as feat(observability)
- **WHEN** committing the metrics wiring (`src/metrics.py`, `src/server.py` instrumentation decorator, `tests/test_metrics.py`, `AGENTS.md` observability section)
- **THEN** the commit message SHALL use type `feat(observability):` with a description

#### Scenario: Audit fix changes committed as fix(audit)
- **WHEN** committing the `trace_calls` dotted-symbol fix in `src/search.py` and `tests/test_search_trace_calls.py`
- **AND** the `AGENTS.md` update for trace_calls documentation
- **THEN** the commit message SHALL use type `fix(audit):` with a description

#### Scenario: git log shows exactly 3 conventional commits
- **WHEN** all commits are made
- **THEN** `git log --oneline` SHALL show exactly 3 commits with types `feat(llm)`, `feat(observability)`, `fix(audit)`
- **AND** working tree SHALL be clean (`git status` shows no untracked or modified files)
