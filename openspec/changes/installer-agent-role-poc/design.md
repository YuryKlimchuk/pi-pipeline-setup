# Design

## Context

- Pi **1.1.0**, OpenSpec CLI **1.14.0**, Node **v22.22.3** — установлены и совпадают с заявленными (`docs/compatibility.md`).
- Установленное расширение subagent `~/.pi/agent/extensions/subagent/` — это **S3** (SHA-256: `index.ts` `d7f717bc…`, `agents.ts` `e1ab7add…`), два обычных файла без package.json/README/LICENSE/Git; происхождение, версия и способ установки **не установлены** (`blocked`).
- Кандидат **S4** (`examples/extensions/subagent/` в пакете Pi 1.1.0; SHA-256 `index.ts` `4facaa61…`, `agents.ts` `cc85ecd3…`) — поставляемый пример, **не установлен**.
- Отличия S3/S4 (verified): S4 наследует активную модель/thinking родителя при отсутствии `model` и учитывает `ctx.isProjectTrusted()`; S3 — нет. S4 принимает `tools` строкой или массивом; S3 — только строкой. Обе явно передают заданный `model`, ищут `.pi/agents` вверх от cwd, не добавляют child-флаги `--approve`/`--no-extensions`/`--no-mcp`.
- Формат роли (обе реализации): Markdown + YAML frontmatter `name`, `description` (обязательные), `tools` (необязательная строка через запятую), `model` (необязательный); тело → `--append-system-prompt`. Discovery: user `~/.pi/agent/agents/*.md` (всегда), project `.pi/agents/*.md` (только `agentScope: project|both`; `both` даёт приоритет проектным именам).
- Пользовательские агенты уже есть, но **ни одна из шести ролей blueprint не существует** ни в user-, ни в project-scope.
- `trust.json` не содержит ни `pi-pipeline-setup`, ни disposable-проекта.
- Контракт моделей P2 реализован: `schemas/model-configuration.schema.json` + fixtures `tests/fixtures/models/`.

## Goals

Доказать на disposable-проекте восемь свойств из `proposal.md` и вернуть воспроизводимый evidence-отчёт. Ничего не менять в `~/.pi/agent/`, глобальной конфигурации Pi, trust и смежных проектах.

## Non-Goals

Production-CLI установщика (P6b), production-роли/resolver (P4), workflow-движок, sandbox/QA-runner, автоматическая инициализация OpenSpec, live-запросы сверх отдельно разрешённого минимума, реализация скрапера криптовалют.

## Decisions

- **D-PoC-1 — Offline-first.** Все проверки, не требующие модельного запроса, выполняются без него: discovery, парсинг frontmatter, построение аргументов child, резолв моделей, примитивы установщика на fixtures. Live — только отдельно разрешённый минимум.
- **D-PoC-2 — Две дорожки.** Track A (subagent + шесть ролей) и Track B (примитивы установщика) независимы по файлам; общий disposable-root один, но fixture-каталоги не пересекаются.
- **D-PoC-3 — Disposable-проект.** Одноразовый каталог вне рабочих проектов, без секретов и credential-файлов; baseline (список файлов + хеши) фиксируется до любых записей.
- **D-PoC-4 — Переиспользование P2.** Выбор модели идёт через schema-валидный `.pi/blueprint-models.yaml` (синтетические ID в fixture), резолв даёт явные `model:` для шести ролей и `defaultProvider`/`defaultModel` для основной сессии. Не выдумываются реальные ID и не выполняется API-запрос для резолва.
- **D-PoC-5 — Явный выбор реализации subagent.** PoC не молча использует S3. Варианты: (а) подключить S4 в disposable-окружение (способ доставки и хеш фиксируются), либо (б) осознанно протестировать S3 с пометкой «происхождение/версия неизвестны». Выбор — отдельное разрешение пользователя; свойства S3 и S4 не переносятся друг на друга.
- **D-PoC-6 — Evidence вызова по событиям.** «Роль вызвана» доказывается JSON-событиями дочернего процесса (фактическая модель, фактически объявленные/использованные tools, assistant-сообщение с ответом, exit code, stopReason), а не фактом существования `.md`-файла и не полем `details.model`.

## PoC architecture

### Track A — subagent и шесть ролей

1. Fixture-проект с `.pi/agents/{analyst,architect,developer,code-reviewer,qa,devops}.md` (черновые определения, тела по контрактам `docs/roles.md`; Reviewer/QA — `tools: read, grep, find, ls` без shell).
2. Offline: discovery из корня и вложенного cwd при `agentScope: project`; парсинг frontmatter; dry-run построения аргументов child; негативы (невалидный frontmatter, пустой/некорректный `tools`, коллизия user/project имён).
3. Live (отдельно разрешено): один single-вызов минимальной тестовой роли с чтением синтетического `fixture.txt`; затем, при разрешении бюджета, по одному вызову на каждую из шести ролей для доказательства invokability каждой.
4. Сбор evidence: JSON-события child, exit code, фактическая модель и tools, побочные записи вне проекта (temp prompt удалён; session/cache/log-следы child перечислены).

### Track B — примитивы установщика (офлайн, fixtures)

1. Черновой формат `install-manifest` (ownership: `whole-file`, `marked-block`, `json-keys`, `frontmatter-fields`) — для PoC достаточно структуры и хешей, не полноценный D3-формат (он согласуется в P6a).
2. `plan` без записи: preview, отклонение symlink/hardlink для управляемых путей, обнаружение коллизий.
3. Применение на fixture: staging/backup/журнал внутри `.pi/blueprint/`, `current == last-applied → update`, `current == desired → no-op`, иначе — конфликт на решение.
4. Негативы: permission failure, запись вне root, dirty/no-Git, повреждённый manifest, повторная установка (no-op), частичный сбой и восстановление, crash между шагами (journal/backup).

## File layout (предлагаемый, для PoC — fixture)

```text
tests/fixtures/installer-agent-role-poc/
  README.md                       # классификация всех fixture как синтетических, без секретов
  disposable/                     # одноразовый целевой проект (временный, не коммитится)
    .pi/
      agents/{analyst,architect,developer,code-reviewer,qa,devops}.md
      blueprint-models.yaml       # синтетические ModelRef
      blueprint/install-manifest.json
      blueprint/backups/<transaction-id>/
    fixture.txt                   # синтетический файл для live-чтения
  roles/                          # исходные черновые определения ролей (fixture-качество)
  installer/                      # fixture-данные для Track B (source snapshot, expected images)
```

Target-layout (для будущего production-установщика, вне PoC) остаётся как в `docs/architecture.md` §D4.

## Sequence

1. Зафиксировать baseline disposable-проекта и версии/хеши (Pi/OpenSpec/Node, S3/S4).
2. Согласовать выбор реализации subagent, модель/стоимость/auth для live, trust для disposable и допустимость temp/cache-следов (все — отдельные разрешения).
3. Offline Track A и Track B (без модельных запросов).
4. Отдельно разрешённый live-read (Track A, шаг 3–4).
5. Санитизированный отчёт `verified` / `not-tested` / `blocked`, отражение в `docs/compatibility.md`.
6. Предъявление независимым Reviewer и QA (обязательно оба отчёта), цикл исправлений.
7. Gate B (приёмка пользователем) и архивирование — после Gate A и реализации.

## Risks / Trade-offs

- **S3 vs S4:** S3 — уже установлен, но происхождение неизвестно; S4 — проверяемый источник, но требует подключения. Риск выбора неверной базы контракта. Смягчение: явное решение пользователя + фиксация SHA-256; при несовместимости — возврат к D2, не форк.
- **Стоимость live:** доказательство шести ролей требует до шести вызовов. Смягчение: минимально один вызов для механизма, остальные — только по отдельному бюджетному разрешению; каждый вызов читает один синтетический файл.
- **Trust/headless:** child `pi --no-session` в JSON-режиме может не загрузить project settings; UI-confirmation отсутствует в headless. Смягчение: негативный тест untrusted child; отсутствие безопасного режима — блокер, не fallback.
- **Побочные эффекты:** temp prompt вне проекта (создаётся/удаляется расширением), возможные session/cache-следы child. Смягчение: полный diff до/после, согласие на temp/cache.
- **Ложное «роль исполнима»:** разбор файла ≠ вызов. Смягчение: D-PoC-6 (evidence по событиям).

## Migration Plan

Не применимо: PoC не меняет существующий формат и не мигрирует данные. Production-миграции — в P6a/P7.

## Open Questions

1. **Реализация subagent для PoC:** S4 (подключить, зафиксировать доставку/хеш) или S3 (тест с пометкой «происхождение неизвестно»)? Требует разрешения.
2. **Live-запрос:** какая модель (provider/id), лимит стоимости/данных, способ auth? Требует разрешения.
3. **Trust:** разрешён ли сохранённый trust для disposable-проекта, либо одноразовый режим подтверждения? Требует решения.
4. **Побочные следы:** допустимы ли temp/cache/session-записи child вне disposable-проекта? Требует согласия.
5. **P2 task 5.2:** независимая проверка изменения `model-configuration-contract` остаётся незакрытой — закрывать до или параллельно с PoC?
