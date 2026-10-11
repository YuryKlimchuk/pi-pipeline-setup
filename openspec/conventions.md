# Конвенции OpenSpec

> Сверено с `Fission-AI/openspec` (схема `spec-driven`, CLI 1.14.0). Источник: https://github.com/Fission-AI/openspec

## Жизненный цикл изменения

1. **Создать изменение** (kebab-case имя):
   ```bash
   openspec new change "<name>"
   ```
   Создаёт `openspec/changes/<name>/` с `.openspec.yaml`. При отсутствии корня создаёт `openspec/` (config.yaml со `schema:`, `specs/`, `changes/archive/`).

2. **Статус артефактов**:
   ```bash
   openspec status --change "<name>" --json
   ```
   Возвращает `schemaName`, `planningHome`, `changeRoot`, `artifactPaths`, `artifacts` со статусами, `nextSteps`.

3. **Инструкция по артефакту** (шаблон + контекст + правила):
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```
   `artifact-id`: `proposal` | `specs` | `design` | `tasks` | `apply` | `archive`.

4. **Написать артефакты** по шаблонам из `templates/` в порядке зависимостей: proposal → specs, design → tasks.

5. **Проверить**:
   ```bash
   openspec validate [item]
   ```

6. **Реализовать** (`/opsx-apply`): чек-боксы `- [ ] N.M` в `tasks.md` → `- [x] N.M`.

7. **Заархивировать** (`/opsx-archive` / `openspec archive <name>`): синхронизирует дельты в базовые specs и переносит изменение в `changes/archive/<YYYY-MM-DD-<name>>/`.

## Артефакты

| Артефакт | Вопрос | Содержимое |
|---|---|---|
| `proposal.md` | Зачем | Why, What Changes, Capabilities (New/Modified), Impact |
| `specs/<cap>/spec.md` | Что (поведение) | дельта требований (ADDED/MODIFIED/REMOVED/RENAMED) |
| `design.md` | Как | Context, Goals/Non-Goals, Decisions, Risks/Trade-offs, Migration Plan, Open Questions |
| `tasks.md` | Шаги | чек-боксы `- [ ] N.M <действие + как проверить>` |

`design.md` создаётся только если применимо (кросс-модульные изменения, новая зависимость, безопасность/миграции, неоднозначность). `tasks.md` требует `specs` и `design`.

## Формат дельта-требований (`specs/<cap>/spec.md`)

```markdown
# Spec Delta

## Purpose            # ТОЛЬКО для новых capability (50+ символов)
## ADDED Requirements
## MODIFIED Requirements    # полный блок требования (не частичный!)
## REMOVED Requirements     # с Reason и Migration
## RENAMED Requirements     # FROM:/TO:
```

Правила:
- Каждое требование: `### Requirement: <имя>` + описание с `SHALL`/`MUST`.
- Каждый сценарий: `#### Scenario: <имя>` (ровно **4** решётки) + `WHEN`/`THEN`.
- Описание требования (текст до первого сценария) ≤ **500 символов**.
- Одно поведение = одно требование; примеры/границы → в сценарии.
- MODIFIED: копировать блок целиком, заголовок совпадает (без учёта пробелов).
- Новая capability → `## Purpose` обязателен; существующая → `## Purpose` не добавлять.

## Метаданные изменения `.openspec.yaml`

Распознаваемые ключи: `schema`, `created`, `goal`, `affected_areas`, `initiative`, `skip_specs`, `retire_capabilities`.

- `skip_specs: true` — изменение без дельт спецификаций (рефакторинг/тулинг/доки). Иначе `openspec validate` отклоняет изменение с нулём дельт.
- `retire_capabilities: true` — изменение может удалить последнее требование capability (удаление main-spec — осознанное решение автора).

## Проектный `config.yaml`

```yaml
schema: spec-driven

context: |
  # стек, пакетный менеджер, продуктовый язык — инжектится в каждую инструкцию

rules:
  specs: [...]   # правила для требований
  tasks: [...]   # правила для задач
  design: [...]  # правила для дизайна
```

Пример — `config.example.yaml`. `context` и `rules` — место для **проектных** правил (в т.ч. стек-специфичных), которые идут в целевой проект, а не в ядро blueprint.

## Правила процесса

1. **Нет OpenSpec-корня** → не инициализировать без явной просьбы (`openspec init` / `openspec new change` создают корень как побочный эффект — не допускать).
2. Артефакты создаются **только** на этапе планирования; до ручного согласования код не меняется.
3. `skip_specs` не выдумывать ради прохождения валидации: нет изменения поведения → нет спеки.
4. Перед архивированием: `openspec validate` + подтверждение приёмки.

## Справочные команды

```bash
openspec list --json              # изменения (root: null → корня нет)
openspec list --specs             # инвентарь capability
openspec show <id> --type spec --json --no-scenarios   # обзор существующей спеки
openspec change show <name> --json --deltas-only       # дельты изменения
openspec schemas --json           # доступные схемы
openspec store list --json        # зарегистрированные stores
```
