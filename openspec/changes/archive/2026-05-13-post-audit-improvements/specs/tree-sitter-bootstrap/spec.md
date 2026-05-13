## ADDED Requirements

### Requirement: tree-sitter native wheels compile on `uv sync`
The `tree-sitter` Python package SHALL install successfully via `uv sync` without requiring manual compilation steps or pre-installed system libraries.

#### Scenario: uv sync installs tree-sitter on macOS arm64
- **WHEN** a developer runs `uv sync` from the project root
- **THEN** the command SHALL succeed with exit code 0
- **AND** `uv run python -c "import tree_sitter; print(tree_sitter.__version__)"` SHALL print a version string without error

#### Scenario: All tests pass with tree-sitter installed
- **WHEN** tree-sitter wheels are compiled and installed
- **AND** the developer runs `uv run --with pytest pytest tests/`
- **THEN** all 50+ tests SHALL pass (no ImportError for tree_sitter)
