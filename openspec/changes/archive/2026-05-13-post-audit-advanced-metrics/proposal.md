## Why

После аудита code-context выяснилось: нет инструмента для быстрого выявления "где тормозит" (top slow tools + error hotspots) и нет автоматического трекинга экономии токенов в динамике (daily trend). Кроме того, commit flow в AGENTS.md описан, но не enforced — агенты продолжают использовать bash для коммитов вместо MCP инструментов, потому что system prompt имеет приоритет над AGENTS.md.

## What Changes

- **top-slow-tools**: новый MCP tool `get_metrics_slowest()` — возвращает топ-N инструментов по latency и error rate
- **daily-trend**: автоматический daily summary в `~/.code-context-cache/metrics/daily/YYYY-MM-DD.json` с агрегацией экономии по инструментам
- **commit-flow-automation**: инструкция в AGENTS.md и механизм принуждения — агент ОБЯЗАН использовать `compact_change_intelligence` → `draft_commit` → `approve_commit_draft` для всех git commit операций, с fallback если MCP server не отвечает

## Capabilities

### New Capabilities

- `top-slow-tools`: MCP tools `get_metrics_slowest()` + `get_metrics_errors()` для диагностики производительности
- `daily-trend`: персистентный daily summary-файл с трендом экономии токенов по каждому инструменту
- `commit-flow-automation`: enforce-инструкция в AGENTS.md, fallback-стратегия, и тест что агент не делает git commit в обход MCP flow

### Modified Capabilities

- (none)

## Impact

- `src/metrics.py`: новый метод `slowest(limit=5)` + `errors_summary()` + `daily_snapshot()`
- `src/server.py`: новые tools `get_metrics_slowest`, `get_metrics_errors`, `get_metrics_daily_trend`
- `AGENTS.md`: раздел "Commit Flow" становится MUST (не recommended), добавляется описание fallback
- `~/.code-context-cache/metrics/daily/`: новая директория для daily снепшотов
