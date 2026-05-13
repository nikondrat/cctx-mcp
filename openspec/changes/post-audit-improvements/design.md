## Context

MCP server — `mcp.server.fastmcp` — запускается как subprocess. Тулзы вызываются через JSON-RPC. На данный момент нет ни одного теста, который запускает сервер реально и проверяет ответы. Unit-тесты покрывают внутренние модули, но не сквозной путь.

`src/vector_index.py` при неудаче эмбеддинга кидает `RuntimeError` — fallback невозможен. Нужен graceful degrade.

tree-sitter — C-extension. pyproject.toml уже содержит зависимости. На arm64 wheels есть начиная с 0.23.2.

Последняя сессия: ~740 новых строк, ~250 измененных. Без коммитов diff растет.

## Goals / Non-Goals

**Goals:**
- Smoke test: MCP сервер через subprocess + JSON-RPC для 6 ключевых тулзов
- Fallback: без Ollama и OpenRouter → `semantic_search` возвращает сообщение, не exception
- tree-sitter: `uv sync` ставит без ручной возни
- Коммиты: conventional messages, каждый логический блок отдельно

**Non-Goals:**
- Не меняем LLMProvider/LLMRouter контракты
- Не добавляем новых MCP tools (get_metrics_events уже добавлен)
- Не рефакторим существующие тулзы

## Decisions

1. **Smoke test через subprocess + `uv run`**
   - Даёт real end-to-end: импорт, инициализация, JSON-RPC сериализация
   - Требует uv в PATH — skip теста если uv не найден (через `shutil.which`)
   - **6 фиксированных тулзов**: `find_symbols`, `semantic_search`, `code_search`, `smart_read`, `get_config`, `get_metrics_report` — не "all registered tools"

2. **Fallback для semantic_search**
   - Не менять `index.search()` сигнатуру
   - Ловить `RuntimeError` на уровне `server.py:448` — уже сделано
   - Дополнительно: проверить что `vector_index.py:233-234` возвращает `RuntimeError` с `error_reason`, а не пустой список
   - Тест: mock router.embed → LLMResponse(error_reason=...)

3. **tree-sitter**
   - Не pre-commit hook — слишком дорого
   - `uv sync` генерирует `uv.lock` с зафиксированными wheels
   - Только проверить что тесты проходят, не править код

4. **Коммиты — пересмотренный порядок:**
   - `feat(llm):` — LLM domain + routing + все тесты LLM слоя (включая test_openrouter_provider.py, test_llm_router.py)
   - `feat(observability):` — metrics instrumentation, get_metrics_events, AGENTS.md docs, test_metrics.py
   - `fix(audit):` — trace_calls dotted-symbol + test_search_trace_calls.py
   - Проверка: `git log --oneline` показывает 3 conventional commits (chore не нужен)

5. **AGENTS.md обновление для trace_calls и smoke-test** — добавить описание улучшенного поиска dotted symbols

## Risks / Trade-offs

- **Smoke test flaky** → skip если uv не найден, random port через `--port 0`
- **tree-sitter wheel на arm64** → версия `>=0.23.2` гарантирует pre-built wheels
- **Коммиты с историей** → `git status` покажет, какие файлы уже изменены до этой сессии
