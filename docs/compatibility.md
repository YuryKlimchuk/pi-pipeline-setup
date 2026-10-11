# Матрица совместимости (P1)

> **Редакция:** 1. Подготовлено в рамках P1 (статическое исследование). Дата: 2026-10-11.
> Ни один `verified`-факт ниже не является результатом live-запуска subagent, модельного запроса, установки зависимостей или изменения trust. Записи `verified` подтверждены чтением локальных файлов/CLI; записи `not-tested` требуют эксперимента и зафиксированы в [протоколе PoC](poc-protocol.md).

## Легенда статусов

| Статус | Значение |
|---|---|
| `verified` | Подтверждено чтением документации или исходного кода установленных версий (статически) |
| `not-tested` | Нельзя подтвердить статически; требует эксперимента, описанного в протоколе PoC |
| `blocked` | Недоступно/не установлено происхождение или запрещено текущим scope задания |

Разделение: факты, подтверждённые документацией/кодом (`verified`), отделены от поведения, устанавливаемого только экспериментом (`not-tested`).

## 1. Окружение и версии

| Механизм | Статус | Версия/источник | Наблюдаемый факт |
|---|---|---|---|
| Pi Coding Agent | `verified` | `pi --version` → `1.1.0`; пакет `@earendil-works/pi-coding-agent@1.1.0` | Бинарь: `/home/yury/.local/share/pi-node/node-v22.22.3-linux-x64/bin/pi` |
| OpenSpec CLI | `verified` | `openspec --version` → `1.14.0`; пакет `@fission-ai/openspec@1.14.0` | Бинарь в том же каталоге pi-node |
| Node.js | `verified` | `node --version` → `v22.22.3` | Соответствует `engines.node >=22.19.0` пакета Pi |
| Лицензия Pi | `verified` | `package.json` → `"license": "MIT"` | Файла `LICENSE` в установленном пакете нет; только `MIT` в `README.md` |
| Лицензия OpenSpec | `verified` | `package.json` → `"license": "MIT"`; файл `LICENSE` присутствует | Лицензия MIT, `repository` `https://github.com/Fission-AI/OpenSpec` |

**Целевые исходные версии исследования (Pi 1.1.0, OpenSpec CLI 1.14.0) фактически установлены и совпадают с заявленными.** Расхождений не выявлено.

## 2. Subagent-кандидат S4 (пример из Pi 1.1.0)

Источник: `examples/extensions/subagent/` в пакете `@earendil-works/pi-coding-agent@1.1.0`. Это пример в составе пакета, **не встроенный API** и **не отдельный версионированный пакет**.

SHA-256 (совпадают с ранее записанными в архитектуре):

| Файл | SHA-256 |
|---|---|
| `examples/extensions/subagent/index.ts` | `4facaa61c9c781748dd000eb5d2ec0a75289986d1a6e11ce13971ca5653dc252` |
| `examples/extensions/subagent/agents.ts` | `cc85ecd33b89aa575bea3d2a9a9da7654a6305da4de02e5041aa5342a1de29b4` |

| № | Механизм | Статус | Источник/ссылка | Наблюдаемый факт | Ограничения и последствия | Следующий шаг |
|---|---|---|---|---|---|---|
| S4-1 | Происхождение/версия | `verified` (состав) / `not-tested` (upstream commit) | `package.json`, `README.md` пакета; `examples/extensions/subagent/README.md` (путь внутри пакета) | Пример поставляется в составе Pi 1.1.0; отдельного `package.json`/версии у примера нет. Лицензия наследуется из метаданных Pi (`MIT`), но текста `LICENSE` в установленном пакете нет | MIT-метаданные Pi не доказывают происхождение и не дают текста лицензии для будущей поставки кода; точный upstream-commit релиза 1.1.0 в локальной установке не установлен | Для поставки кода: подтверждённый upstream ref, полный текст LICENSE и copyright notices выбранной версии |
| S4-2 | Discovery и scope | `verified` | `agents.ts` `discoverAgents()`; `README.md` | `scope` ∈ `user`/`project`/`both` (default `user`). user-каталог: `getAgentDir()/agents` (`~/.pi/agent/agents`). project-каталог: поиск `.pi/agents` вверх от cwd до корня FS. `both` — проектное имя перекрывает пользовательское | `.pi/agents` — не стандартный ресурс package manifest; доставка/обнаружение — задача D3 | PoC: найти ожидаемый путь при `agentScope: project` из корня и из вложенного каталога |
| S4-3 | Передача модели | `verified` | `index.ts` `runSingleAgent()` | `dispatchDefaults.model = ${ctx.model.provider}/${ctx.model.id}`; `model = agent.model ?? dispatchDefaults.model`; при наличии — `--model <model>`. `--thinking` передаётся только при наследовании (когда `agent.model` отсутствует) | S4 наследует активную модель родителя при отсутствии `model` в агенте; это отличие от локальной S3. Наследование опирается на `ctx.model` родительского ExtensionAPI | PoC: подтвердить фактическую модель child по JSON-событиям, а не только `details.model` |
| S4-4 | Передача инструментов | `verified` | `agents.ts` `parseToolList()`; `index.ts` | `tools` принимается как строка (split `,`) или массив; иной тип → `undefined` (без инструментов). При непустом списке — `--tools <join(",")>` | Наличие имени в `--tools` не гарантирует фактическую доступность/MCP; `--tools` не sandbox | PoC: сверить фактически действующий набор инструментов child |
| S4-5 | Передача инструкций/контекста | `verified` | `index.ts` `writePromptToTempFile()`, `runSingleAgent()`; `docs/cli.md` (`--append-system-prompt`) | Тело роли (после frontmatter) пишется во временный файл `os.tmpdir()/pi-subagent-*/prompt-*.md` (mode 0600) и передаётся через `--append-system-prompt <path>`; задача — позиционным аргументом `Task: <task>` | Контекст родителя/сессии не переносится; child запускается как `pi --no-session` и сам загружает свои context-файлы по правилам Pi. Markdown-ссылка не является include | PoC: проверить, что child реально прочитал переданную роль/задачу |
| S4-6 | Trust и permissions | `verified` | `index.ts` `execute()` | Подтверждение проектных агентов: `(scope project/both) && confirmProjectAgents && ctx.hasUI && !ctx.isProjectTrusted()` → UI-confirm. Child не получает `--approve`, `--no-extensions`, `--no-mcp` | Project trust родителя не гарантирует загрузку project settings child; headless-режим без UI не обеспечивает подтверждение | PoC: отрицательный тест untrusted child и коллизию user/project |
| S4-7 | Дочерний процесс | `verified` | `index.ts` `getPiInvocation()`, `runSingleAgent()` | `spawn(cmd, args, { cwd: cwd ?? defaultCwd, shell: false, stdio: ["ignore","pipe","pipe"] })`; окружение наследуется. `getPiInvocation` запускает тот же runtime/скрипт, fallback `pi`. stdout разбирается как JSONL (`message_end`, `tool_result_end`) | Окружение наследуется, не sandbox; произвольные расширения/MCP родителя могут влиять | PoC: зафиксировать фактический `cwd`, события, exit code |
| S4-8 | Single/parallel/chain | `verified` | `index.ts` `execute()`; `README.md` | Single `{agent,task}`; parallel `{tasks[]}` (max 8 задач, 4 одновременно, видимый вывод ≤ 50 KiB/задачу, полный — в details); chain `{chain[]}` с `{previous}`, остановка на первом сбое | Parallel/chain не обязательны v1; для workflow достаточно последовательных независимых single-вызовов | PoC v1: один single-вызов; parallel/chain — отдельно при необходимости |
| S4-9 | Ошибки/отмена/завершение | `verified` | `index.ts` `isFailedResult()`, обработка `signal` | `exitCode != 0` → ошибка; `stopReason: error` → ошибка LLM; `aborted` → SIGTERM, через 5s SIGKILL; chain останавливается на сбойном шаге; `proc.on("error")` → exit 1 | Фактическое поведение при отмене/краше нужно подтвердить экспериментом | PoC: ошибка модели, отмена (Ctrl+C), завершение процесса |
| S4-10 | Файловые побочные эффекты | `verified` (temp prompt) / `not-tested` (следы child) | `index.ts` `writePromptToTempFile()`, `finally` | Временный prompt-файл в `os.tmpdir()` (mode 0600) удаляется в `finally` (unlink + rmdir). Child `pi` может оставлять session/cache/log-следы вне проекта — расширение их не контролирует | Temp/cache/session-следы child должны быть отдельно согласованы в PoC | PoC: зафиксировать все записи вне проекта |

## 3. Локальная реализация S3 (для сравнения, не кандидат)

Источник: `~/.pi/agent/extensions/subagent/{index.ts, agents.ts}` — два обычных файла (не symlink); собственного `package.json`, `README`, `LICENSE` и Git-корня не обнаружено.

| Файл | SHA-256 |
|---|---|
| `index.ts` | `d7f717bcdc6d335363ea3719dcb3fcfc0b5ee791eae81e3f803af2ff0d0d22a4` |
| `agents.ts` | `e1ab7addbd4c0dcd11a2acd11ad21e1aef8b91d61c0a2216f8b6c29a0bfde904` |

| Механизм | Статус | Наблюдаемый факт | Ограничения |
|---|---|---|---|
| Происхождение/версия/способ установки | `blocked` | Не установлены | Не может быть переносимым контрактом |
| Передача модели | `verified` (отличие) | Передаёт `--model` только при `agent.model`; наследования активной модели родителя нет | Не соответствует рекомендации D2 |
| Thinking level | `verified` (отличие) | Не передаётся | — |
| Передача tools | `verified` (отличие) | Только строка (`frontmatter.tools?.split(",")`); массив не поддерживается; `model` не проверяется на строку | Некорректный тип может сорвать обнаружение |
| Подтверждение проектных агентов | `verified` (отличие) | Проверяет только `ctx.hasUI` (без `ctx.isProjectTrusted()`) | Отличается от S4 |

Свойства S3 **не переносятся** на S4 и наоборот.

## 4. Загрузка инструкций Pi

| Механизм | Статус | Источник/ссылка | Наблюдаемый факт | Ограничения и последствия | Следующий шаг |
|---|---|---|---|---|---|
| Выбор context-файла каталога | `verified` | `dist/core/resource-loader.js` `loadContextFileFromDir()` | Кандидаты в порядке: `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`; выбирается первый существующий обычный файл; файлы каталога **не объединяются** | Создание нового `AGENTS.md` может вытеснить действующий `CLAUDE.md` | Учтено в D4: проверка эффективного контекста до записи |
| Порядок обхода каталогов | `verified` | `dist/core/resource-loader.js` `loadProjectContextFiles()` | Сначала глобальный контекст agent-каталога, затем от cwd вверх по родителям (ближайший первым), дедупликация по realpath | Вложенный запуск меняет набор контекста | PoC: вложенный cwd |
| `.pi/AGENTS.md` не загружается автоматически | `verified` | `docs/configuration.md` (таблица `.pi`) | В `.pi` определены только `SYSTEM.md`, `APPEND_SYSTEM.md`, `settings.json`, `mcp.json`, `extensions/`, `skills/`, `prompts/`, `themes/` | Корневой `AGENTS.md` — корректная точка входа; `.pi/AGENTS.md` не считать include | Подтверждает выбор D4 (root `AGENTS.md`) |
| `SYSTEM.md`/`APPEND_SYSTEM.md` | `verified` | `docs/configuration.md` | `SYSTEM.md` заменяет системный промпт, `APPEND_SYSTEM.md` добавляет; доверенный проектный файл имеет приоритет над agent-каталогом; одноимённые файлы не объединяются | Установка не должна молча вытеснять пользовательские инструкции | D4: не создавать/менять по умолчанию |
| Context не требует trust | `verified` | `docs/configuration.md` | «Context-file discovery does not require project trust» | Инструкции читаются и в untrusted-проекте | Учтено в D2/D4 |

## 5. OpenSpec CLI

| Механизм | Статус | Источник/ссылка | Наблюдаемый факт | Ограничения и последствия | Следующий шаг |
|---|---|---|---|---|---|
| Набор команд | `verified` | `openspec --help` | `version, init, update, list, view, change, archive, spec, config, schema, store, doctor, context, workset, validate, show, feedback, completion, status, instructions, templates, schemas, new, help` | Команд `generate`/`update-version` нет — старые skills нельзя копировать без сверки | — |
| `init` | `verified` | `openspec init --help` | Поддерживает `--tools pi` (и многие другие), `--language`, `--force`, `--profile` | Инициализация — только явное решение пользователя; в P1 не выполняется | — |
| `new change` | `verified` | `openspec new --help` | `new change <name>` создаёт каталог изменения; при отсутствии корня может создать корень | Обход инициализации запрещён | — |
| `validate` | `verified` | `openspec validate --help` | `--all/--changes/--specs/--archived/--strict/--json/--type` | Структурная проверка, не доказательство согласия | — |
| `archive` | `verified` (код) / `not-tested` (end-to-end) | `openspec archive --help`; `dist/core/archive.js` | Опции `-y/--yes`, `--skip-specs`, `--no-validate`, `--json`, `--store`. Код переносит каталог изменения в `changes/archive/` (rename, fallback copy при EPERM/EXDEV), обновляет main specs | Сохранность служебного раздела `proposal.md` и evidence при archive не проверена на fixture | Проверить на безопасной копии в P8 (не в P1) |
| `instructions`/`context`/`doctor` | `verified` | `openspec instructions --help`, `--help` | `instructions [artifact]` (`--change`, `--schema`, `--json`); `context` печатает рабочий контекст root; `doctor` — здоровье root | Фактический planning root разрешается до записи; внешний store требует отдельного разрешения | Проверить фактический root перед любой записью |

## 6. Сводка

**`verified` (статически):** версии Pi/OpenSpec/Node; контракт S4 (discovery/scope, model, tools, инструкции, trust-проверка, дочерний процесс, single/parallel/chain, ошибки/отмена, temp-файл); отличия S3; порядок загрузки context-файлов Pi и правило «`.pi/AGENTS.md` не загружается»; `SYSTEM`/`APPEND_SYSTEM`; команды OpenSpec и отсутствие `generate`/`update-version`; лицензии (MIT, у Pi нет текста LICENSE).

**`not-tested` (только экспериментом):** фактическая модель child по JSON-событиям; фактический набор инструментов; поведение trust/headless child; ошибки/отмена/завершение; файловые следы child вне проекта; end-to-end `openspec archive` с сохранением proposal/evidence. Каждая позиция описана в [протоколе PoC](poc-protocol.md).

**`blocked`:** происхождение/версия/способ установки локальной S3.
