## Context

Текущая архитектура `semantic_search`:

```
MCP call semantic_search(q)
  → server.py: get/create VectorIndex (lazy, per-project singleton)
    → VectorIndex.search(q)
      → _ensure_indexed()
        → _load_from_disk()         # ~/.code-context-cache/vectors/<hash>/
        → если чанков нет → index_project()
          → _iter_source_files()    # rglob по проекту
          → _extract_chunks()       # только top-level def/class
          → router.embed() chunk → Ollama nomic-embed-text
          → _save_to_disk()
      → router.embed(q)             # query embedding через Ollama
      → numpy cosine similarity     # O(N×D)
      → dedup by file               # только по имени файла, не по содержимому
      → return top-k normalized by max score
```

Проблемы:
1. **Ленивая индексация**: первый `search()` делает полный проход по проекту. Для code-context (36 файлов) это ~3-5с, для большого проекта — минуты.
2. **RuntimeError при ошибке эмбеддинга**: `vector_index.py:234` — `raise RuntimeError(...)`. Server ловит в `_instrument_tool` как exception, возвращает `Error: ...`.
3. **Смена модели между индексацией и поиском**: проверка есть (line 241), но при несовпадении делает `force=True` переиндекс — ещё один полный проход.
4. **Chunking по top-level символам**: функция с 10 методами — один chunk. Документация — по заголовкам, но код — только def/class.
5. **Дедупликация по файлу**: если два chunk из одного файла имеют одинаковый snippet, оба возвращаются.
6. **Нет нормализации score между запросами**: max_score нормирует к 1.0, но сравнение между разными запросами невозможно.
7. **Нет health check**: нельзя проверить, работает ли `semantic_search` без пробного запроса.

## Goals / Non-Goals

**Goals:**
- `get_health()`: вернуть статус Ollama (running?), модели (доступны?), index (построен?, актуален?)
- Server pre-builds vector index при старте (синхронно, перед MCP ready)
- Graceful degrade: вместо RuntimeError — информативное сообщение с инструкцией
- Chunking по методам/функциям (а не только top-level)
- Дедупликация по содержимому chunk'а (одинаковый snippet ≠ два результата)
- Интеграционный тест: реальный `semantic_search` через JSON-RPC с проверкой score и релевантности
- `uv run pre-index` — CLI команда для ручного pre-build индекса

**Non-Goals:**
- Асинхронный index build с прогресс-баром (слишком сложно для MCP stdio transport — нет streaming)
- Поддержка нескольких embedding моделей одновременно (одна модель на проект)
- Ранжирование результатов по сложным метрикам (BM25 + semantic hybrid) — только cosine similarity

## Decisions

1. **Pre-indexing при старте сервера**: синхронный вызов `index_project()` в `main()` перед `mcp.run()`. Для больших проектов добавить `--skip-index` флаг.
   - **Почему:** первый `semantic_search` всегда мгновенный. Без этого пользователь (агент) ждёт 5-30с без обратной связи.
   - **Рассмотрено:** асинхронный build в фоне → MCP не поддерживает прогресс через stdio transport, пользователь не знает, готов индекс или нет.
   - **Trade-off:** старт сервера дольше на время индексации. Но сервер рестартует редко.

2. **Graceful degrade вместо RuntimeError**: `vector_index.py` выбрасывает RuntimeError при ошибке эмбеддинга. Меняем на возврат пустого списка + `VectorIndex._last_error: str | None`. Server читает `_last_error` и формирует сообщение.
   - **Почему:** ошибка эмбеддинга не должна ронять запрос. Агент получает "semantic_search временно недоступен: Ollama не отвечает (http://localhost:11434). Решение: ollama pull nomic-embed-text"
   - **Рассмотрено:** retry fallback на OpenRouter → нет API key, fallback мёртв.

3. **Chunking по методам**: сейчас `_extract_chunks` chunk'ит только top-level def/class. Добавляем проход по AST через tree-sitter (уже есть в `search.py` analyzers). Для каждого метода/функции на любом уровне вложенности — отдельный chunk.
   - **Почему:** "semantic_search для функции `validate_token`" должен найти именно её, а не класс `AuthProvider` целиком.
   - **Trade-off:** больше чанков → больше эмбеддингов → дольше индексация. На code-context проекте (11k строк) ожидается ~200-300 чанков вместо ~80.

4. **Дедупликация по содержимому**: после получения top-k, перед возвратом, проверяем уникальность snippet (первые 100 символов как key).
   - **Почему:** если два chunk'а из разных мест файла имеют одинаковый код (например, import секции), результат бесполезен.
   - **Trade-off:** потеря разнообразия фрагментов. Компенсируем увеличением top_k.

5. **`get_health()` как aggregated status**: не раздувать количество инструментов, а сделать один диагностический entrypoint:
   ```json
   {
     "ollama": {"status": "ok", "model": "nomic-embed-text:latest", "latency_ms": 42},
     "vector_index": {"status": "ok", "chunks": 156, "files": 36, "stale": false},
     "tree_sitter": {"status": "ok", "version": "0.23.2"},
     "server": {"version": "0.3.0", "commit": "abc1234"}
   }
   ```

6. **Тесты качества поиска**: файл `tests/test_semantic_search_quality.py` запускает semantic_search через настоящий VectorIndex с реальным Ollama (skip если Ollama недоступен). Проверяет 5 запросов с известными ожидаемыми файлами и минимальным score.

## Risks / Trade-offs

- **[Risk] Pre-indexing увеличивает время старта сервера** → **Mitigation:** для больших проектов `--skip-index` flag или timeout на индексацию (30с). Index строится в фоновом потоке с low priority.
- **[Risk] Chunking по методам увеличивает размер индекса** → **Mitigation:** увеличивается линейно от числа функций. Для code-context: с 80 до ~250 чанков. Память: ~250 vectors × 768 dims × 4 bytes = ~0.8 MB. Приемлемо.
- **[Risk] Тесты качества хрупкие** → **Mitigation:** только skip если Ollama недоступен. Score threshold = 0.7 — conservative, реальные результаты выше. Если тест падает — это legitimate regression.
- **[Risk] `get_health()` может быть медленным** → **Mitigation:** health check не вызывает embedding, только ping Ollama API. Timeout 2s.
