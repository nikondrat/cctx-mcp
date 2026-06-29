<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/CCTX%E2%80%93MCP-0F172A?style=for-the-badge&logo=python&logoColor=3B82F6&labelColor=1E293B">
    <img src="https://img.shields.io/badge/CCTX%E2%80%93MCP-F1F5F9?style=for-the-badge&logo=python&logoColor=2563EB&labelColor=FFFFFF" alt="CCTX-MCP">
  </picture>
</p>

<p align="center">
  <strong>Структура, а не простыня.</strong><br>
  MCP-сервер, который даёт AI-агенту скелет кода —
  чтобы он тратил контекст на работу, а не на ориентирование.
</p>

<p align="center">
  Работает с <strong>opencode</strong> · <strong>Claude Desktop</strong> · <strong>Cursor</strong> · любым MCP-клиентом
  <br><br>
  <a href="https://github.com/nikondrat/cctx-mcp"><img src="https://img.shields.io/github/stars/nikondrat/cctx-mcp?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/cctx-mcp/"><img src="https://img.shields.io/pypi/v/cctx-mcp?style=flat-square&logo=pypi&logoColor=white&label=PyPI&labelColor=1E293B&color=3B82F6" alt="PyPI"></a>
  <a href="https://pypi.org/project/cctx-mcp/"><img src="https://img.shields.io/pypi/pyversions/cctx-mcp?style=flat-square&logo=python&logoColor=white&label=Python&labelColor=1E293B&color=3B82F6" alt="Python"></a>
  <a href="https://github.com/nikondrat/cctx-mcp"><img src="https://img.shields.io/github/stars/nikondrat/cctx-mcp?style=flat-square&logo=github&logoColor=white&label=Stars&labelColor=1E293B&color=3B82F6" alt="Stars"></a>
  <a href="https://github.com/nikondrat/cctx-mcp/actions"><img src="https://img.shields.io/github/actions/workflow/status/nikondrat/cctx-mcp/ci.yml?style=flat-square&logo=githubactions&logoColor=white&label=CI&labelColor=1E293B&color=3B82F6" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-3B82F6?style=flat-square&labelColor=1E293B" alt="License"></a>
  <img src="https://img.shields.io/badge/Status-Beta-3B82F6?style=flat-square&labelColor=1E293B" alt="Beta">
</p>

---

## Зачем это

Я 10 месяцев работаю исключительно через AI-агентов. Собрал несколько агентных систем с нуля. Прошёл путь Cursor → opencode и урезал месячный расход с $200 до $10 — без потери качества в своих задачах.

За эти 10 месяцев я видел прозрачно: что агент вызывает, что видит, где тратит контекст впустую, чего ему не хватает.

Картина повторялась:

1. Агент заходит в новый файл → `Read` 500 строк кода
2. Нужно найти функцию → `grep` по всему проекту
3. Нужно понять импорты → читает тот же файл снова
4. Коммит → парсит `git diff` на 3000 токенов

Проблема не в стоимости токенов — токены дёшевы. Проблема в **налоге на ориентирование**: агент сжигает контекстное окно на попытки понять, где он находится, вместо того чтобы делать реальную работу.

**code-context — не продукт. Это запись того, чего мне не хватало как пользователю AI-агентов.** Каждый инструмент здесь появился потому, что я смотрел, как агент тупит, и думал: «это должно делаться в один вызов».

---

## Что он реально делает

### Структура вместо простыни

Незнакомый файл? Не читай — просканируй.

`smart_read` возвращает скелет: иерархия символов, зависимости, диапазоны строк, doc-комментарии. Агент видит `class Foo на строке 42, method bar() на строке 85, импортов: 3` — а не 500 строк кода, которые ему надо ментально распарсить.

То же самое: `get_symbol_body` когда нужна одна функция, `find_symbols` когда нужно одно определение по всему проекту, `get_dependencies` когда нужны импорты без чтения файла.

### Diff без простыни

`compact_change_intelligence` заменяет `git diff` + `git status`: «4 файла изменено, добавлена login(), переименован AuthProvider.validate()». Агент видит картину целиком в 10 строках вместо 200.

В паре с `draft_commit` — AI генерирует conventional commit message из структурированных изменений. Без парсинга сырого diff.

### Аннотации функций (в разработке)

`get_symbol_summaries` уже генерирует однострочные AI-описания для каждой функции: `bar() — валидирует ввод, возвращает токен сессии`.

Идея — встроить эти аннотации прямо в вывод `smart_read`, чтобы модель видела `bar()  // валидирует ввод` при сканировании файла и не тратила токены на догадки о том, что делает функция. Сейчас это отдельный вызов — работаю над объединением.

---

### Когда это НЕ нужно

code-context даёт структуру. Он не поможет с:

- **Редактированием кода.** Он read-only. Инструменты записи (`edit`, `write`) остаются нативными.
- **Запуском тестов и сборкой.** Нет раннера тестов, нет компилятора.
- **Деплоем.** Нет CI/CD интеграции.
- **Работой с сырым содержимым файла.** Если нужен полный текст файла — `Read` всё ещё правильный инструмент.

Используй для **ориентирования, поиска, анализа и коммитов**. Всё остальное — вне его зоны.

---

## Инструменты

| Инструмент | Заменяет | Статус |
|------------|----------|--------|
| `smart_read` | `Read` + ручной разбор | ✅ |
| `find_symbols` | `grep` + чтение файлов | ✅ |
| `get_dependencies` | `Read` + извлечение импортов | ✅ |
| `trace_calls` | `grep` по всему репозиторию | ✅ |
| `analyze_project` | `find` + `ls` + `wc` | ✅ |
| `get_symbol_body` | `Read` целого файла | ✅ |
| `get_symbol_summaries` | Чтение реализации | ✅ нужна LLM |
| `compact_change_intelligence` | `git diff` + `git status` | ✅ |
| `draft_commit` | Написание commit message | ✅ нужна LLM |
| `approve_commit_draft` | `git commit` | ✅ |
| `stage_changes` / `unstage_changes` | `git add` / `git restore --staged` | ✅ |
| `get_config` · `get_health` · `get_version` | — | ✅ |
| **Аннотации в smart_read** | — | **В планах** |
| `semantic_search` · `code_search` · `find_files` | grep + read | Реализовано, не зарегистрировано |

Я выкатываю только то, чем реально пользуюсь. Незарегистрированные инструменты есть в коде, но не торчат наружу, пока я не убежусь, что они заслуживают своё место.

---

## Быстрый старт

```bash
uvx cctx-mcp
```

Добавь в конфиг MCP-клиента:

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "uvx",
      "args": ["cctx-mcp"]
    }
  }
}
```

Не нужны API-ключи и внешние сервисы для базового функционала. Требуется Python 3.10+. LLM нужна для commit drafting и семантических суммари — использует Ollama (локально) или OpenRouter (облако).

---

## Поддерживаемые языки

<p>
  <img src="https://img.shields.io/badge/Swift-FA7343?style=flat-square&logo=swift&logoColor=white" alt="Swift">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Rust-000000?style=flat-square&logo=rust&logoColor=white" alt="Rust">
  <img src="https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go">
  <img src="https://img.shields.io/badge/Dart-0175C2?style=flat-square&logo=dart&logoColor=white" alt="Dart">
</p>

Работает на [tree-sitter](https://tree-sitter.github.io/) AST — для каждого языка отдельный парсер.

---

## Установка

### uvx (рекомендуется)

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "uvx",
      "args": ["cctx-mcp"]
    }
  }
}
```

### pip

```bash
pip install cctx-mcp
```

```json
{
  "mcpServers": {
    "cctx-mcp": {
      "command": "python",
      "args": ["-m", "code_context.server"]
    }
  }
}
```

### из исходников

```bash
git clone https://github.com/nikondrat/cctx-mcp.git
cd cctx-mcp
uv sync
uv run python -m code_context.server --skip-index
```

---

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `CC_OLLAMA_URL` | `http://localhost:11434` | Адрес Ollama |
| `CC_OLLAMA_TIMEOUT` | `10` | Таймаут запросов к Ollama (сек) |
| `CC_COMMIT_MODEL` | `gemma4:latest` | Локальная модель для commit drafting |
| `CC_EMBED_MODEL` | `nomic-embed-text` | Локальная модель для эмбеддингов |
| `CC_SEMANTIC_SUMMARIES` | `1` | Включить AI-суммари символов |
| `CC_COMMIT_DRAFTING` | `1` | Включить AI-генерацию коммитов |
| `CC_LLM_ROUTER` | `local-first` | `local-first`, `local-only`, `remote-first`, `remote-only` |
| `CC_LOCAL_PROVIDER` | `ollama` | Имя локального LLM-провайдера |
| `CC_REMOTE_PROVIDER` | `openrouter` | Имя облачного LLM-провайдера |
| `CC_OPENROUTER_API_KEY` | — | Ключ API для облачного режима |
| `CC_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter-совместимый эндпоинт |
| `CC_OPENROUTER_TIMEOUT` | `15` | Таймаут запросов к OpenRouter (сек) |
| `CC_OPENROUTER_MAX_TOKENS` | `256` | Максимум токенов в ответе LLM |
| `CC_OPENROUTER_TEMPERATURE` | `0.1` | Температура LLM |
| `CC_OPENROUTER_EMBED_MODEL` | `text-embedding-3-small` | Облачная модель для эмбеддингов |
| `CC_OPENROUTER_COMMIT_MODEL` | `openai/gpt-4o-mini` | Облачная модель для коммитов |

---

## Автор

**Никита (@nikondrat)**

10 месяцев ежедневно работаю с AI-агентами. Строил мультикомпонентные агентные системы, анализировал что работает (а что нет), мигрировал с проприетарных инструментов на open-source стек, ужал инфраструктурные расходы в 20 раз.

code-context — дистиллят этого опыта.

Занимаюсь консалтингом по архитектуре AI-агентов, разработке MCP-серверов и оптимизации LLM-воркфлоу. Если ваша команда строит AI-инструменты для разработчиков или встраивает агентов в свой стек — я могу помочь.

Открыт к предложениям.

---

## Разработка

```bash
uv sync
uv run pytest tests/ -v
```

### Логирование

Вызовы инструментов пишутся в `~/.code-context-cache/debug.jsonl` с аргументами, результатом, задержкой и статусом:

```bash
tail -f ~/.code-context-cache/debug.jsonl
```

Переменная `CC_DEBUG_LOG` меняет путь к лог-файлу.

PRs приветствуются. [Открытые issues](https://github.com/nikondrat/cctx-mcp/issues).

---

## Лицензия

MIT — можно всё.
