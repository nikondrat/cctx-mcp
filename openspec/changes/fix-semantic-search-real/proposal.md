## Why

`semantic_search` — ключевой инструмент экономии токенов (обещает -96%), но реально работает нестабильно: первая попытка всегда холодный старт (10-30с), при рестарте сервера индекс перестраивается, при изменении файлов индекс не обновляется, нет прогресс-бара, нет тестов качества поиска, а ошибки при падении Ollama — RuntimeError вместо человеческого сообщения. Инструмент есть, но доверия к нему нет.

## What Changes

- `nomic-embed-text:latest` подключена, но `CC_COMMIT_MODEL=gemma4:latest` в конфиге — неверное название (реальная модель `gemma4:latest` или с суффиксом `stable`). Исправить названия моделей в конфиге и AGENTS.md
- Добавить `get_health()` — единый эндпоинт здоровья: Ollama (running?), embedding модель (доступна?), vector index (построен?, свежий?)
- Переписать `_ensure_indexed` — индекс строится при старте сервера, а не при первом search(). Либо асинхронно с прогрессом, либо синхронно до старта MCP
- Решить проблему холодного старта: `uv run pre-index` CLI или server startup build
- Добавить `semantic_search` с таймаутом: если Ollama не отвечает за N секунд — возвращать "Ollama unavailable. Запусти: ollama pull nomic-embed-text"
- Заменить RuntimeError в vector_index.py на возврат пустого результата + diagnostic message
- Добавить chunking по функциям/методам (не только top-level), а не только по def/class на первом уровне
- Добавить дедупликацию результатов по содержимому (одинаковые сниппеты из разных чанков)
- Интеграционный тест: реальный `semantic_search` через MCP server, проверка что результаты релевантны (score > 0.7)
- Проверка: `semantic_search` на code-context проекте возвращает корректные результаты на 5 разных запросов

## Capabilities

### New Capabilities
- `health-endpoint`: единый MCP tool `get_health()`, возвращающий статус Ollama, embedding model, vector index, tree-sitter
- `pre-indexing`: сервер строит векторный индекс при старте (не лениво), с опцией `uv run pre-index` для ручного запуска
- `search-quality-tests`: тесты с реальным semantic_search, проверкой score > 0.7 и релевантности результатов
- `incremental-reindex`: детект изменений файлов (mtime/hash) при каждом search(), автоматический переиндекс только изменённых файлов
- `graceful-degrade`: semantic_search не кидает RuntimeError, а возвращает понятное сообщение с инструкцией

### Modified Capabilities
- (none)

## Impact

- `src/server.py`: новый tool `get_health()`, изменение `semantic_search` подписи/обработки ошибок, pre-indexing при старте
- `src/vector_index.py`: переписать `_ensure_indexed` на eager mode, добавить warmup, graceful degrade вместо RuntimeError
- `src/config.py`: исправить commit_model на корректное имя (проверить `nomic-embed-text`), добавить health check route
- `tests/test_semantic_search_real.py`: новый файл — integration tests с реальным запуском MCP и проверкой релевантности
- `AGENTS.md`: обновить список моделей, добавить команду `uv run pre-index`
