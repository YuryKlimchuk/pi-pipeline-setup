# Proposal

> **Статус:** черновик для Human Gate A. **Gate A не одобрен.** Реализация PoC запрещена до явного одобрения пользователем (этап 5 канонического `docs/workflow.md`).

## Why

P0 (решения D1–D6 утверждены) и P1 (матрица совместимости `docs/compatibility.md` + протокол PoC `docs/poc-protocol.md`) завершены. P2 — изменение `model-configuration-contract` — реализовано (schema, синтетические fixtures, документация; 12/13 задач), но его независимая проверка (задача 5.2: Reviewer + QA) **остаётся открытой**: P2 **не объявляется принятым**, Gate B не достигнут.

Следующая реализационная стадия требует воспроизводимого **проектного установщика** и **шести исполнимых ролей subagent**, чтобы инициализировать новые проекты утверждённым workflow. Первое целевое приложение — Java/Spring-скрапер криптовалют с Telegram-оповещениями (в рамках этого изменения **не реализуется**).

Ключевые факты остаются `not-tested` (`docs/compatibility.md`): фактическая модель дочернего процесса, фактический набор инструментов, поведение trust/headless child, файловые побочные эффекты. Поэтому до подтверждения контракта нельзя писать production-установщик (P6b) или production-роли (P4). Нужен минимальный PoC, который на disposable-проекте установит восемь свойств из задачи.

## What Changes

Добавляются **процедура и каркас PoC** (fixtures + чек-лист + правила сбора evidence), но **не** production-установщик и **не** production-определения ролей. PoC доказывает:

1. **Проектную установку без изменения глобальной конфигурации Pi** — все записи только в корне и `.pi/` disposable-проекта; `~/.pi/agent/` не изменяется.
2. **Ожидаемый layout и формат ролей** — `.pi/agents/<role>.md` с frontmatter `name`/`description`/`tools`/`model` и телом инструкций; discovery через `agentScope: project`.
3. **Шесть исполнимых ролей** — черновые тестовые определения `analyst`, `architect`, `developer`, `code-reviewer`, `qa`, `devops` (fixture-качество, не production).
4. **Orchestrator как основная сессия Pi** — не файл роли; подтверждается самим фактом выполнения PoC из основной сессии.
5. **Выбор модели по контракту P2** — schema-валидный `.pi/blueprint-models.yaml` → явные `model:` для каждой роли + `defaultProvider`/`defaultModel` основной сессии. Offline-резолв выполняется сейчас; live-подтверждение фактической модели — только по отдельному разрешению.
6. **Явную обработку ошибок** — отсутствующая модель, отсутствующее/несовместимое расширение, невалидная конфигурация, permission/trust failures.
7. **Владение/конфликты/backup/повтор/восстановление** — примитивы установщика (D3) на fixtures, офлайн, включая прерывание между каждым шагом установки.
8. **Доказательство фактического вызова роли** — evidence различает **настроенную** модель (`model:` во frontmatter / аргумент `--model`) и **фактически использованную** модель (JSON-события child). Если фактическую модель или набор инструментов нельзя достоверно подтвердить — соответствующий acceptance test считается **невыполненным**.

### Разрешённый объём этого этапа (offline)

Только чтение, анализ, подготовка fixture и offline-тесты: discovery, парсинг frontmatter, dry-run аргументов child, резолв моделей P2, примитивы установщика на fixtures. Никаких записей вне рабочего дерева, изменений trust, подключения расширений или модельных запросов.

### Вне этого этапа — требует отдельных разрешений

- Подключение S3/S4 (доставка кода в disposable-окружение) — отдельное действие пользователя.
- Live-вызовы моделей (модель, стоимость, данные, auth) — отдельное разрешение.
- Изменение trust / одноразовый режим подтверждения — отдельное решение.
- Записи вне disposable-root (temp/cache/session-следы child) — отдельное согласие.

### Кандидат subagent — S4 (предпочтительный, не подключается)

Предпочтительный кандидат для дальнейшей проверки — **S4**: пример `examples/extensions/subagent/` в пакете `@earendil-works/pi-coding-agent@1.1.0` (Pi 1.1.0). Источник, версия и SHA-256 фиксируются (см. `design.md`), **подключение не выполняется**; совместимость с установленным Pi 1.1.0 описывается как **проверяемое условие**, а не как `verified` факт до PoC.

**Не входит в PoC (остаётся отдельно гейтованным):** production-CLI установщика (P6b), production-определения ролей и resolver (P4), workflow-движок, sandbox/QA-runner, изменение `~/.pi/agent/`, trust или глобальной конфигурации Pi, любые изменения в проекте скрапера криптовалют.

## Capabilities

Изменение не меняет runtime-поведения продукта: это проверочная/tooling-стадия (fixtures, процедура, отчёт). Дельты спецификаций не создаются; opt-out зафиксирован в `.openspec.yaml` через `skip_specs: true` и явно предъявляется на Gate A (конвенции: «нет изменения поведения → нет спеки»).

### New Capabilities

<!-- нет: PoC не вводит runtime-поведения продукта -->

### Modified Capabilities

<!-- нет -->

## Impact

- **Код:** production-код не создаётся; только fixture-ресурсы и процедура под `tests/fixtures/` и документация.
- **Зависимости:** не устанавливаются.
- **API/модели:** live-запрос только по отдельному разрешению (модель, стоимость, данные, auth).
- **Глобальная конфигурация Pi / trust:** не изменяется; существующие пользовательские данные не затрагиваются.
- **Смежные проекты:** скрапер криптовалют и другие проекты не затрагиваются.
- **Совместимость:** PoC фиксирует фактический контракт кандидата S4 (и отличия установленной S3), версии Pi/OpenSpec/Node и SHA-256 кандидата.
- **Связь с P2:** задача 5.2 (`model-configuration-contract`) остаётся открытой до независимого review; её открытость не блокирует независимое offline-проектирование Track B.

<!-- Gate A ожидает явного одобрения пользователя. Раздел "Blueprint approvals" добавляется только после решения (append-only, D6). -->

<!-- BEGIN: Blueprint approvals -->
<!-- Служебный раздел журнала согласований. Исключается из digest proposal.md (D6). Append-only; исправление — новая запись со ссылкой `supersedes`. -->

## Blueprint approvals

### Record ga-20261011-002 — Human Gate A (accept, строго ограниченный scope)

| Поле | Значение |
|---|---|
| record-id | `ga-20261011-002` |
| time | 2026-10-11T17:18:07+03:00 |
| change | `installer-agent-role-poc` |
| root | `/home/yury/projects/java/pi-pipeline-setup` |
| gate | A |
| decision | `accept` (строго ограниченный scope) |
| git revision | `50348eea47c900d7ec4af913433eebbe987a3d52` |
| reviewer | саморевью первичного Orchestrator (НЕ независимое; независимый Reviewer/QA — на Gate B) |

**Цитата решения пользователя:** «I approve Gate A for change `installer-agent-role-poc`, with the following strict scope and conditions.» … «Authorize only: tasks 3.1–3.10: offline implementation and tests of installer primitives; task 0.2: baseline collection for the disposable project, limited to the project-local state needed for Track B. No other tasks are authorized by this approval.»

**Принятый scope:** только задачи `0.2` (baseline disposable-проекта) и `3.1–3.10` (офлайн-реализация и тесты примитивов установщика). Никакие другие задачи не авторизованы.

**Явные исключения (НЕ авторизовано):** Track A `1.x`/`2.x` (в т.ч. офлайн discovery и эксперименты с ролями/резолвом моделей); gated/live `4.x`; приёмка/отчётность `5.x`, Gate B, архивирование OpenSpec; `0.1`/`0.3` в части subagent-кандидата и внешних побочных эффектов за пределами project-local baseline; установка/подключение/выполнение S3 или S4; live-модельные/API-запросы; изменение trust/глобальной конфигурации Pi/permissions/существующих пользовательских данных; запись вне disposable-project root; Git commit/push/reset/изменение истории.

**skip_specs: true — рассмотрено и принято.** Причина: PoC меняет tooling (fixtures/процедура), а не runtime-поведение продукта; «нет изменения поведения → нет спеки» (`openspec/conventions.md`).

**Условия реализации (из решения пользователя):**
1. PoC-manifest остаётся явно provisional; не выдаётся за финальный контракт D3/P6a.
2. Сохранять пользовательские файлы; безопасный отказ при конфликтах, symlink-escape, permission-ошибках, неоднозначном ownership.
3. Реализовать staging, backup, journal, идемпотентные повторы и crash-recovery тесты в рамках scope.
4. Не расширять scope без отдельного одобрения.
5. P2 task 5.2 остаётся открытой; P2 не объявляется принятым.
6. Зафиксировать `skip_specs: true` и обоснование (tooling, не product-runtime).

**Snapshot (Gate A):** `c656c16cf8d64a4aefcd814b787c9bbe97ee4a4e7990bb78aca2fe7d82ae4034` — SHA-256 над упорядоченным manifest `sha256 size path` (provisional-формат; формальная сериализация — в P5):

- `1e37a77797feae14d9a5bfdde8adcb9e0bb8689d350c35e9897c84b76d3e4691  8989  openspec/changes/installer-agent-role-poc/proposal.md` (тело без этого раздела)
- `977a4b290bff4f462266204f92d8103744e5d4368d8028a65fd675a2867941c7  18089  openspec/changes/installer-agent-role-poc/design.md`
- `cbed60f01e461ad026c2a80e68c1f085cc5115c03a5f29c25850523b11873db5  10821  openspec/changes/installer-agent-role-poc/tasks.md`
- `a7fdc6c6efa3596a5399daac645701c99f1f6d02a0583674f2b07430b0892f75  470  openspec/changes/installer-agent-role-poc/.openspec.yaml`
- `f0082e9c22e8ce1d611c0f3b4d4915ce445e7ff2553cda6b713b6c25f390984c  998  openspec/config.yaml`
- отсутствуют (опциональные): `openspec/changes/installer-agent-role-poc/specs/**` (skip_specs).

**Evidence:** отсутствует на Gate A (до реализации; тесты — в рамках реализации, независимый review — на Gate B).

**Замечания:** нет открытых блокеров.

<!-- END: Blueprint approvals -->
