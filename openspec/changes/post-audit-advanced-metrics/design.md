## Context

Текущая система метрик (`metrics.py`) записывает события в JSONL, но не предоставляет:
- агрегированного view "какие инструменты самые медленные"
- сводки ошибок по инструментам
- дневного тренда — как меняется экономия день ото дня

Кроме того, commit flow (`compact_change_intelligence` → `draft_commit` → `approve_commit_draft`) описан в AGENTS.md как recommended, но built-in system prompt предписывает bash-команды. Нужен механизм принуждения: AGENTS.md становится source of truth, а fallback-стратегия покрывает случай недоступности MCP server.

## Goals / Non-Goals

**Goals:**
- `get_metrics_slowest(limit=5)`: возвращает топ-N инструментов по avg latency, отсортированные по убыванию
- `get_metrics_errors()`: возвращает список инструментов с ненулевым error count + суммарный error rate
- `get_metrics_daily_trend(days=7)`: возвращает daily снепшоты: per-tool call count, total latency, error count, estimated token savings
- Ежедневный авто-снепшот при первом вызове инструмента metrics в день
- AGENTS.md: commit flow становится MUST, добавляется блок "Enforcement & Fallback"
- Тест: verify что агент не использует bash git commit без вызова compact_change_intelligence

**Non-Goals:**
- Не добавляем external dependencies (все через stdlib)
- Не меняем формат events.jsonl (обратная совместимость)
- Не создаем Pre-commit hook для enforcement (только документация + тест)

## Decisions

1. **Slowest tools**: `metrics.py` уже хранит `_call_latency_ms` и `_call_errors`. Новый метод просто сортирует и возвращает топ. Никакого дополнительного сбора не нужно.

2. **Daily snapshot**: при первом вызове `get_metrics_daily_trend()` за сегодня — вычисляется снепшот из `events.jsonl` за сегодня, пишется в `daily/YYYY-MM-DD.json`. Последующие вызовы читают из файла. Формат:
   ```json
   {"date": "2026-05-13", "tools": {"smart_read": {"calls": 5, "total_latency_ms": 120, "errors": 0}}, "total_savings_estimate_tokens": 15000}
   ```
   Оценка экономии: `calls * avg_file_size_tokens_without_tool * savings_factor_per_tool`.

3. **Commit flow enforcement**: AGENTS.md получает блок "Commit Flow (MANDATORY)" перед существующим разделом. Правило: "Никогда не используй `git commit` напрямую. Всегда вызывай `compact_change_intelligence` → покажи пользователю → `draft_commit` → покажи → `approve_commit_draft`. Если `draft_commit` возвращает ошибку сервера — используй `approve_commit_draft(project_path, message="...")` с manually написанным message."

4. **Тест для enforcement**: `tests/test_commit_flow.py` — парсит AGENTS.md, проверяет что секция "Commit Flow" содержит фразы `compact_change_intelligence`, `draft_commit`, `approve_commit_draft`, `fallback`.

## Risks / Trade-offs

- **Daily snapshot race condition** → два параллельных вызова могут писать в один файл. Mitigation: write to temp file + atomic rename.
- **Token savings estimate — всегда приблизительная** → документируем как "estimate" с пометкой о погрешности.
- **Enforcement только документацией** → нельзя заставить агента читать AGENTS.md. Mitigation: добавить тест, который проверяет AGENTS.md на актуальность; но compliance остается на уровне best effort.
