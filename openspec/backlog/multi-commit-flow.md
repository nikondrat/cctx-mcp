# Multi-commit Flow: разбивка на логические коммиты

**Заметил:** 2026-05-13 (после fix-semantic-search-real)
**Статус:** backlog

## Проблема

Текущий commit flow (`compact_change_intelligence` → `draft_commit` → `approve_commit_draft`) предполагает ровно один коммит, который коммитит всё сразу (`git add -A`). Когда изменений много (20+ файлов, разные логические группы — фикс, тесты, docs), невозможно разбить на несколько conventional commits.

## Варианты решения

### A. auto-grouping в compact_change_intelligence ✅

Сервер сам классифицирует файлы по логическим группам — агенту не нужно разбираться.

- `compact_change_intelligence` — возвращает группы: `{"source": [...], "tests": [...], "config": [...], "docs": [...], "openspec": [...]}`
- `draft_multi_commit(path)` — генерирует N сообщений (по одному на группу)
- `approve_commit_draft(path, group=0, message="feat(core): ...")` — коммитит первую группу и помечает её как done
- Агент просто вызывает `approve_commit_draft` с `group=0`, `group=1`, `group=2` — сервер сам делает `git add <files>` для конкретной группы

### ~~B. stage-manager tool~~ ❌ — не решает проблему

Идея: `stage_files` / `unstage_files` / `commit_staged` — те же `git add` под MCP-обёрткой. Агент тратит те же токены на выбор файлов вручную. Не лучше bash-коммитов.

### C. Commit grouping в `compact_change_intelligence`

- `compact_change_intelligence` возвращает grouped changes (по change type: source/test/docs/config)
- `draft_multi_commit(path)` — генерирует N сообщений для N логических групп
- `approve_commits(path, messages: list[str])` — коммитит по группам последовательно

## Acceptance

- [ ] Агент может закоммитить только часть изменений, оставив остальные для следующего commit
- [ ] Несколько conventional commit'ов из одного working tree
- [ ] Каждый commit содержит логически связанные файлы
- [ ] Все commit'ы проходят pre-commit hooks
