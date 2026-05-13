## Why

Полный аудит code-context выявил пробелы: метрики инструментов не подключены (было), `trace_calls` не находит dotted symbol, нет ни одного интеграционного smoke-теста, tree-sitter не собирается в голом окружении. Все это подрывает доверие к observability и качеству поставки.

Необходимо закрыть все дыры аудита, добавить персистентную observability и закоммитить результаты предыдущей сессии + новые фиксы.

## What Changes

- Добавить smoke-тест MCP сервера: запуск, базовые вызовы find_symbols / semantic_search / trace_calls через реальный JSON-RPC
- Добавить интеграционный тест для маршрута `semantic_search` с выключенным Ollama и отсутствующим OpenRouter API key
- tree-sitter: обеспечить сборку в `uv sync` + автоматическую установку wheels через pyproject.toml
- Закоммитить все изменения предыдущей сессии (LLM routing, vector index, config) + новую observability (wired metrics, events.jsonl, _instrument_tool, get_metrics_events)

## Capabilities

### New Capabilities

- `smoke-test`: integration smoke test that starts MCP server via subprocess, calls tools via JSON-RPC, validates responses
- `fallback-reliability`: unit + integration tests for semantic_search when Ollama down + OpenRouter unconfigured
- `tree-sitter-bootstrap`: ensure tree-sitter native wheels compile in `uv sync` without manual intervention
- `final-commits`: conventional commit messages covering all delta files from LLM routing + observability + audit fixes

### Modified Capabilities

- `observability`: `get_metrics_events()` tool added, decorator-based call instrumentation in server.py, persisted JSONL events log

## Impact

- `src/server.py`: smoke test import / subprocess launch
- `src/vector_index.py`: fallback path currently raises RuntimeError on embed failure — needs graceful degrade
- `pyproject.toml`: tree-sitter versions may need adjustment
- No API breaks, no schema changes, no backward incompatibility
