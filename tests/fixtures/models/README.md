# Синтетические fixtures модельной конфигурации

> Все файлы здесь **синтетические**: provider/ID вымышлены, секретов и реальных
> производственных настроек нет. Ни один ID не является утверждённым выбором
> модели. Источник формата — [schema](../../../schemas/model-configuration.schema.json)
> и [контракт](../../../docs/model-configuration-contract.md).

Каждый fixture валидируется против JSON Schema Draft 2020-12. JSON-файлы —
подмножество YAML (допустимы как YAML-документы). `duplicate-keys.yaml` — особый
случай parse-слоя, не выражается в JSON Schema.

## valid/

| Файл | Что демонстрирует | Ожидание |
|---|---|---|
| `presets.json` | Полные пресеты blueprint: три профиля × семь ролей по канонической таблице `docs/model-configuration.md`; `defaultProfile: Balanced` | валиден |
| `project-minimal.json` | Минимальный проектный источник: `blueprint` + `profile` + три `levels`→`ModelRef` | валиден |
| `project-overrides.json` | `orchestrator` (уровень) и `subagents` overrides: прямой `model` и `level` | валиден |
| `project-special-ids.json` | provider/ID с `/` и `:` (хранятся целиком) | валиден |

## invalid/

| Файл | Что демонстрирует | Ожидаемая причина отказа |
|---|---|---|
| `missing-required.json` | Проектный источник без `profile` | `required` |
| `unknown-schema-version.json` | `schemaVersion: 2` | `const` (неизвестная версия) |
| `unknown-role.json` | `subagents.tester` | неизвестная роль (`additionalProperties: false`) |
| `unknown-profile.json` | `profile: Premium` | неизвестный профиль (`enum`) |
| `conflicting-level-model.json` | `orchestrator` с `level` и `model` одновременно | `oneOf` (ровно одно) |
| `unknown-property.json` | верхнеуровневое поле `watcher` | `additionalProperties: false` |
| `invalid-type.json` | `provider: 123` (число) | неверный тип |
| `orchestrator-in-subagents.json` | `subagents.orchestrator` | `orchestrator` запрещён в subagent-map |
| `malformed-id.json` | пустой `id` | `minLength: 1` |
| `duplicate-keys.yaml` | дубликат ключа `provider` в YAML | отклоняется строгим YAML-загрузчиком (parse-слой), не JSON Schema |
