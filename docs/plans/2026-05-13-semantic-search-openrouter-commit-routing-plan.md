# Реализация: гибридный routing для LLM (Ollama → OpenRouter) + улучшение embeddings

## 0) Цели

1. Уменьшить затраты на токены для поиска по коду: сначала semantic retrieval через локальные индексы и эмбеддинги, потом отправлять в модель только релевантные чанки.
2. Добавить абстракцию провайдеров LLM с единым интерфейсом `embed/generate`.
3. Внедрить OpenRouter как удалённый fallback/альтернатива, включая бесплатные модели, для окружений без локальной модели.
4. Поддержать гибридную стратегию: локальная модель = приоритет для приватности/скорости, удалённый провайдер = fallback по доступности и качеству.

## 1) Важный вопрос: будет ли меньше тратиться токенов у облака?

Да, при корректной архитектуре затраты в облачной модели будут заметно ниже.

- Без semantic index: агент отправляет в облако большой и шумный контекст.
- С `semantic_search` + top-k: модель видит короткие релевантные чанки, а не сырые результаты `grep`/`cat`.

Практически это обычно даёт **экономию порядка 60–90%** на входных токенах в сценариях, где раньше модель читала много файлов.

Важно: это не нулевая стоимость. Облако всё равно получает:
- сам пользовательский prompt;
- `compact_change`/`summary` + top-k chunks;
- иногда fallback-текстовое объяснение при invalid output.

## 2) Что реализовываем

### 2.1 Архитектурный срез LLM

Новый домен: `src/llm/`

- `src/llm/contracts.py`
  - `LLMProvider` protocol: `is_available()`, `embed(text, model)`, `generate(prompt, model, options)`.
  - унифицированный `LLMResponse` (provider, model, latency_ms, error_reason).

- `src/llm/providers/ollama.py`
  - обертка над текущим `OllamaClient` без бизнес-логики.

- `src/llm/providers/openrouter.py`
  - клиент OpenRouter: `https://openrouter.ai/api/v1`.
  - поддержка Chat Completions для commit и Embeddings (если модель это поддерживает).
  - API-ключ берется только из env.

- `src/llm/router.py`
  - стратегия выбора провайдера:
    - embed: `local-first` по умолчанию, fallback на OpenRouter;
    - commit: `local-first`, fallback на OpenRouter;
  - единые правила таймаута/ошибок/fallback.

### 2.2 Конфигурация

- `CC_LLM_ROUTER=local-first|local-only|remote-first|remote-only`
- `CC_LOCAL_PROVIDER=ollama`
- `CC_REMOTE_PROVIDER=openrouter`
- `CC_OLLAMA_URL`
- `CC_OLLAMA_TIMEOUT`
- `CC_OPENROUTER_API_KEY`
- `CC_OPENROUTER_BASE_URL`
- `CC_OPENROUTER_EMBED_MODEL`
- `CC_OPENROUTER_COMMIT_MODEL`
- `CC_OPENROUTER_MAX_TOKENS`, `CC_OPENROUTER_TEMPERATURE`

### 2.3 Коммитный конвейер

- `CommitGenerator` и `CompactChange` не зависят от конкретного провайдера.
- Генерация:
  1) попытка локально;
  2) валидация conventional-commit;
  3) fallback в OpenRouter;
  4) fallback на heuristic, если обе модели недоступны.

### 2.4 Semantic Search и индекс

- В `VectorIndex` сохранить метаданные: `provider_name`, `model`, `embedding_dim`.
- При смене пары `provider/model` запускать rebuild.
- Дальше: поддержать rebuild policy и stale index invalidation.

## 3) Пошаговый план (чеклист)

### Этап 1 — foundation
1. Ввести `src/llm/contracts.py` и adapter для текущего Ollama.
2. Реализовать `src/llm/providers/openrouter.py` с тестами на моках HTTP.
3. Реализовать `src/llm/router.py` (local-first + fallback policy + метрики).

### Этап 2 — интеграция
4. Подключить router к `draft_commit`.
5. Подключить router к `semantic_search` и `get_config`.
6. Добавить единый путь ошибок: `provider unavailable`, `invalid response`, `timeout`.

### Этап 3 — качество
7. Улучшить chunking для `.md`/документов (по заголовкам), чтобы реально находился `AGENTS.md`.
8. Добавить дедупликацию по файлу и нормализацию score.

### Этап 4 — валидация
9. Новые интеграционные тесты:
   - локально доступен Ollama → local provider используется;
   - Ollama недоступен → OpenRouter fallback;
   - OpenRouter недоступен → heuristic fallback;
   - отсутствует токен → ясное сообщение и безопасный fail.

10. Обновить AGENTS.md (новые флаги, стратегии маршрутизации, требования к ключу).

## 4) Acceptance-критерии

- `semantic_search` проходит локальный smoke-test на текущем репозитории с релевантностью top-3 >= 70% по ручной разметке 10 запросов.
- При включенном `local-first` и выключенном Ollama автоматически срабатывает OpenRouter.
- Коммит корректно помечается полем `source` (`ollama:*`, `openrouter:*`, или `heuristic`).
- Встроенные таймауты не блокируют CLI/инструмент дольше 10–15 секунд в обычном случае.
- Нет утечки `CC_OPENROUTER_API_KEY` в логах.

## 5) Следующий шаг после плана

Согласуешь ли приоритеты этапов? Рекомендую стартовать по этапу 1 и 2 и потом включать этап 3 после валидации качества routing.
