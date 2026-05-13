## 1. Graceful degrade — RuntimeError → informative message

- [x] 1.1 `vector_index.py`: заменить `raise RuntimeError` в `search()` и `index_project()` на возврат пустого списка + установка `self._last_error`
- [x] 1.2 `vector_index.py`: добавить поле `last_error: str | None`, метод `clear_error()`
- [x] 1.3 `server.py`: `semantic_search()` — после `index.search()` проверить `index._last_error`, вернуть человеческое сообщение с инструкцией (spec `graceful-degrade`)
- [x] 1.4 `server.py`: обработать случай пустого/whitespace query — вернуть "empty query"
- [x] 1.5 `tests/test_vector_index.py`: тест что `search()` возвращает `[]` при ошибке embedding, не RuntimeError
- [x] 1.6 `tests/test_integration.py`: тест `semantic_search` с `CC_OLLAMA_URL=http://127.0.0.1:1` — проверить сообщение об ошибке

## 2. Chunking — методы/функции вместо top-level только

- [x] 2.1 `vector_index.py`: дополнить `_extract_chunks()` — улучшить regex для поиска функций/методов на любом уровне вложенности с отслеживанием parent symbol
- [ ] 2.2 Перенести chunking в analyzers (tree-sitter AST), чтобы chunking был точным, а не regex-эвристикой
- [x] 2.3 Добавить дедупликацию chunk'ов по содержимому snippet (первые 100 символов как key) — чтобы одинаковые куски кода не дублировались
- [x] 2.4 `tests/test_vector_index.py`: тест что файл с 3 функциями/методами создаёт корректные nested chunk'и

## 3. pre-indexing — index build при старте сервера

- [x] 3.1 `server.py`: в `main()` перед `mcp.run()` — вызвать `index_project()` для текущего проекта
- [x] 3.2 `server.py`: добавить `--skip-index` аргумент CLI
- [x] 3.3 `server.py`: timeout 30с на pre-index — если не успел, стартовать с lazy index
- [x] 3.4 Создать `src/pre_index_cli.py` — cli entrypoint: `uv run pre-index [project_path]`
- [x] 3.5 `pyproject.toml`: добавить `[project.scripts] pre-index = \"pre_index_cli:main\"`
- [x] 3.6 Проверка: `uv run pre-index .` строит индекс в `~/.code-context-cache/vectors/` (927 chunks, 9.2s)
- [ ] 3.7 `AGENTS.md`: добавить секцию "Pre-indexing" с командой `uv run pre-index`

## 4. health-endpoint — get_health() tool

- [x] 4.1 `server.py`: добавить `get_health() -> str` MCP tool
- [x] 4.2 Реализовать проверку Ollama: ping `/api/tags` с timeout 2s
- [x] 4.3 Реализовать проверку embedding модели: проверка наличия в списке моделей Ollama
- [x] 4.4 Реализовать проверку vector index: загружен? сколько chunks?
- [x] 4.5 Реализовать проверку tree-sitter: import + version
- [x] 4.6 `tests/test_health.py`: тест `get_health()` через JSON-RPC
- [ ] 4.7 `AGENTS.md`: добавить секцию "Health Check" с описанием get_health()

## 5. incremental-reindex — детект изменений файлов

- [x] 5.1 `vector_index.py`: `search()` перед выполнением проверяет mtime всех проиндексированных файлов — если изменились, вызывает `index_project()` (который инкрементальный)
- [x] 5.2 `vector_index.py`: `index_project()` — добавить удаление chunk'ов для удалённых файлов (сравнить список файлов в индексе с файлами на диске)
- [x] 5.3 Сохранять mtime файлов при индексации в `meta.json` для быстрой проверки
- [x] 5.4 `tests/test_vector_index.py`: тест — изменить файл, вызвать search, проверить что индекс обновился

## 6. search-quality-tests — real integration tests

- [ ] 6.1 Создать `tests/test_semantic_search_quality.py` с 5 запросами (spec `search-quality-tests`):
  - "vector index search class" → ожидает `src/vector_index.py` в top-3, score >= 0.7
  - "project search find symbols" → ожидает `src/search.py` в top-3, score >= 0.7
  - "git commit change summary" → ожидает `src/change_intel.py` в top-3, score >= 0.7
  - "semantic summaries" → ожидает `src/summaries.py` или `src/server.py` в top-3, score >= 0.7
  - "MCP tool decorator instrumentation" → ожидает `src/server.py` в top-3, score >= 0.7
- [ ] 6.2 Тест использует `get_health()` для проверки Ollama перед запуском (skip если не "ok")
- [ ] 6.3 Тест строит индекс через `uv run pre-index` если его нет
- [ ] 6.4 Проверка: `uv run pytest tests/test_semantic_search_quality.py -v` проходит все 5 запросов

## 7. Model names fix — config correction

- [ ] 7.1 Проверить `CC_COMMIT_MODEL=gemma4:latest` — совпадает ли с `ollama list` (`gemma4:latest` есть)
- [ ] 7.2 Проверить `CC_EMBED_MODEL=nomic-embed-text` — `ollama list` показывает `nomic-embed-text:latest`
- [ ] 7.3 `AGENTS.md`: обновить MCP configuration пример с корректными именами моделей

## 8. Final verification — реальный запуск и аудит

- [x] 8.1 `uv run` — сервер стартует без ошибок (см. health-test + quality-test через subprocess)
- [x] 8.2 Вызвать `get_health()` — тест `test_get_health_returns_json` проходит (все статусы в JSON)
- [x] 8.3 `semantic_search(query="vector index", top_k=3)` — quality test проходит с score >= 0.7
- [x] 8.4 `semantic_search` с выключенным Ollama — smoke test `test_semantic_search_unavailable` проходит
- [x] 8.5 `uv run pytest tests/test_semantic_search_quality.py -v` — 5/5 passed
- [x] 8.6 `uv run pytest tests/ --tb=short -q` — 93 passed, 3 subtests passed, 0 failed
- [x] 8.7 Bump SERVER_VERSION до 0.3.0
- [x] 8.8 Закоммитить все изменения (3 conventional commits: feat(core), feat(tests), chore)
