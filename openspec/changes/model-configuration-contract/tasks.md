# Tasks

> Прогресс по чек-боксам: `- [ ] N.M` → `- [x] N.M`. Каждая задача указывает, как проверить завершение. Нумерация — идентификаторы задач, не этапы workflow blueprint.

## 1. JSON Schema

- [ ] 1.1 Создать `schemas/model-configuration.schema.json` (draft 2020-12): `$defs` для `profile`/`level`/`role`/`subagentRole`/`ModelRef`/`Assignment`/`roleLevelMap`; корневой `oneOf` для пресетов blueprint и проектного источника. **Проверка:** файл синтаксически валиден (`JSON.parse` и доступный валидатор, если есть).
- [ ] 1.2 Задать `additionalProperties: false` и `required` так, чтобы неизвестные поля/версии/роли/профили/уровни отклонялись. **Проверка:** fixtures `invalid/unknown-*` дают ошибку schema.
- [ ] 1.3 Задать `Assignment` как ровно одно из `level`/`model`. **Проверка:** `invalid/conflicting-level-model.json` отклонён; `valid/assignment-level.json` и `valid/assignment-model.json` приняты.

## 2. Синтетические fixtures

- [ ] 2.1 Создать `tests/fixtures/models/{valid,invalid}/` и `README.md`, классифицирующий каждый fixture как синтетический. **Проверка:** README перечисляет каждый файл и ожидаемый результат; секретов и реальных ID нет.
- [ ] 2.2 Valid: минимальный полный документ (оба вида), назначения с overrides, provider/ID с `/` и `:`. **Проверка:** соответствуют schema.
- [ ] 2.3 Invalid: missing required, unknown schemaVersion, unknown role, unknown profile, conflicting `level`/`model`, malformed id/тип, `orchestrator` внутри `subagents`. **Проверка:** каждый отклонён по ожидаемой причине.
- [ ] 2.4 Duplicate-keys fixture (YAML) и фиксация, что это parse-level правило. **Проверка:** правило задокументировано; JSON Schema его не выражает.

## 3. Документация

- [ ] 3.1 Документировать три уровня (schema / семантическая / runtime) и правила приоритетов/overrides. **Проверка:** документ согласован со schema и `docs/model-configuration.md`.
- [ ] 3.2 Документировать представление provider/model ID (`/`, `:`), duplicate-key policy, обработку ошибок. **Проверка:** тексты согласованы с fixtures.

## 4. Ручная валидация и согласованность

- [ ] 4.1 Зафиксировать воспроизводимую ручную процедуру валидации (без установки зависимостей) с командами и ожидаемыми результатами. **Проверка:** процедура выполнима в чистом окружении.
- [ ] 4.2 `git diff --check`; проверка Markdown-ссылок; сверка fixtures ↔ `docs/model-configuration.md` ↔ schema. **Проверка:** нет расхождений и посторонних изменений.

## 5. Приёмка

- [ ] 5.1 Прогнать valid fixtures против schema и подтвердить отклонение всех invalid fixtures (или явно зафиксировать ограничение доступного инструмента). **Проверка:** результаты зафиксированы в evidence.
- [ ] 5.2 Предъявить результаты независимому Reviewer и QA; устранить замечания. **Проверка:** оба отчёта привязаны к редакции артефактов.
