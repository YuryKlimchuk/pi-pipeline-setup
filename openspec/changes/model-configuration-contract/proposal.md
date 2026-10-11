# Proposal

## Why

Утверждённое решение D1 задаёт два декларативных источника модельной конфигурации — blueprint-пресеты (профили и назначения ролей без конкретных ID) и проектный источник `provider/model-id` с overrides — но машино-проверяемого контракта формата пока нет: каноническая таблица профилей живёт только в `docs/model-configuration.md`, а перечень полей — в `docs/architecture.md`. Без schema и синтетических fixtures будущий resolver/генератор (P4) получит неоднозначный вход и недетерминированные ошибки. Контракт нужно зафиксировать сейчас, до генератора, чтобы P4 опирался на проверяемый формат, а не на разрозненные описания.

## What Changes

- Добавить JSON Schema `schemas/model-configuration.schema.json` для двух видов документов: пресеты blueprint (`config/models.yaml`) и проектный источник назначений (`.pi/blueprint-models.yaml`).
- Добавить синтетические fixtures в `tests/fixtures/models/` (валидные и невалидные), без реальных provider ID и без секретов.
- Добавить документацию правил: разделение schema-валидации / семантической валидации / runtime-разрешения; приоритеты и overrides; представление provider/model ID (включая `/` и `:`); политика duplicate keys; конфликт `level`/`model`; неизвестные поля/версии/роли/профили; детерминированная обработка ошибок.
- Зафиксировать воспроизводимую ручную процедуру валидации (репозиторий не имеет собственного test runner; зависимости не устанавливаются).

**Не создаются** в рамках P2: рабочие `config/models.yaml` и `.pi/blueprint-models.yaml`, модельные пресеты с реальными ID, resolver, генератор, установщик и определения ролей — это P4 и последующие этапы.

## Capabilities

Изменение не меняет поведение системы: это tooling/формат-контракт (schema + fixtures + документация). Дельты спецификаций не создаются; opt-out зафиксирован в `.openspec.yaml` через `skip_specs: true`.

### New Capabilities

<!-- нет: изменение не вводит runtime-поведения -->

### Modified Capabilities

<!-- нет -->

## Impact

- **Код:** без изменений runtime; добавляются только schema, fixtures и документация.
- **Зависимости:** не устанавливаются.
- **API/системы:** не затрагиваются.
- **Совместимость:** формат версионируется (`schemaVersion: 1`); неизвестные версии отклоняются явно, без автоматической миграции.

<!-- BEGIN: Blueprint approvals -->
<!-- Служебный раздел журнала согласований. Исключается из digest файла proposal.md (D6). Append-only: исправление — новая запись со ссылкой `supersedes`, не стирание. -->

## Blueprint approvals

### Record ga-20261011-001 — Human Gate A (условное принятие)

| Поле | Значение |
|---|---|
| record-id | `ga-20261011-001` |
| time | 2026-10-11T15:21:56+03:00 |
| change | `model-configuration-contract` |
| root | `/home/yury/projects/java/pi-pipeline-setup` |
| gate | A |
| decision | `accept` (условно, при выполнении C1–C3) |
| git revision | `7b665e4f6e9fe48777b999fb5cc9a5950ef1fb12` |
| reviewer | саморевью первичного Orchestrator (НЕ независимое) |

**Цитата решения пользователя:** «The user conditionally approves Human Gate A for this specific change, subject to the three clarifications C1–C3 in the pre-Gate-A review.»

**Принятый scope (только P2):** schema `schemas/model-configuration.schema.json`; синтетические fixtures `tests/fixtures/models/`; документация валидации/разрешения и политики duplicate keys; воспроизводимая ручная процедура валидации. **Не входит:** P3, live/API-запросы, установка расширений, trust/глобальная конфигурация Pi, новые зависимости, commit/push.

**skip_specs: true — рассмотрено и принято.** Обоснование (из `proposal.md` §Capabilities и `openspec/conventions.md`): изменение — tooling/формат-контракт, не меняет runtime-поведения системы, поэтому дельты спецификаций не требуются («нет изменения поведения → нет спеки»).

**Условия C1–C3:**
- **C1** (применено к `design.md` D-5): прямой `model`-override минует сопоставление уровня; сопоставление применяется только к назначениям `level` и к профильным назначениям; приоритет «профиль → override → уровень → ModelRef» не меняется.
- **C2** (применено к `design.md` D-1): `defaultProfile` обязателен в пресетах; в проектном источнике его нет (там обязательный `profile`); `Balanced` — значение при создании файла генератором, **не** JSON Schema `default`.
- **C3** (настоящая запись): `skip_specs: true` явно зафиксировано как рассмотренное и принятое.

**Snapshot (Gate A):** `d676571d9e1cf30f41063f75a17f50919db91cef1bc790422fd842ca135470ae` — SHA-256 над упорядоченным manifest `sha256 size path` (provisional-формат; формальная сериализация — в P5):

- `440afb004b25d4160e573fa251628fa4268759e2f4b19b35cc4713f4d8231917  3569  openspec/changes/model-configuration-contract/proposal.md` (тело без этого раздела)
- `1eddea60ad701986d57971fece0738a674db64559de6044507bb2116959100fa  9028  openspec/changes/model-configuration-contract/design.md`
- `f24b6b55e268024554431ce89c152ced558695e1dfed18c874664715391d5260  4086  openspec/changes/model-configuration-contract/tasks.md`
- `de92c825331e1ee1d2f3d4948810ab8076416dcd685a0eaf1255fa8adaaf630e  314  openspec/changes/model-configuration-contract/.openspec.yaml`
- `f0082e9c22e8ce1d611c0f3b4d4915ce445e7ff2553cda6b713b6c25f390984c  998  openspec/config.yaml`
- отсутствуют (опциональные): `openspec/changes/model-configuration-contract/specs/**` (skip_specs).

**Evidence:** отсутствует (Gate A — до реализации; тесты и проверки — на Gate B).

**Замечания:** нет открытых блокеров.

<!-- END: Blueprint approvals -->
