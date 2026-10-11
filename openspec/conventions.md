# Конвенции OpenSpec

> Сверено с `Fission-AI/openspec` (схема `spec-driven`, CLI 1.14.0). Источник: https://github.com/Fission-AI/openspec

## Операции CLI, не альтернативный workflow

Переходы, роли и согласования определены в [docs/workflow.md](../docs/workflow.md). Таблица — справочник операций, не самостоятельный сокращённый процесс.

| Операция | Команда и условие |
|---|---|
| Проверить корень | `openspec context --json`; проверить фактический root/store до записи. Внешний planning root требует отдельного разрешения |
| Создать изменение | Orchestrator: `openspec new change "<name>"` (kebab-case), только в уже согласованном корне. При отсутствии корня CLI может создать его — этот обход инициализации запрещён |
| Получить статус | `openspec status --change "<name>" --json`; статус артефактов не равен согласованию |
| Получить инструкции | `openspec instructions <artifact-id> --change "<name>" --json`, где ID: `proposal`, `specs`, `design`, `tasks`, `apply`, `archive` |
| Проверить изменение | `openspec validate "<name>" --type change --strict --no-interactive`; структурная проверка, не доказательство качества решения |
| Применить план | `/opsx-apply` (если сгенерирована) только после Human Gate A. Developer отмечает выполненное в `tasks.md` |
| Архивировать | Orchestrator: `openspec archive <name>` или `/opsx-archive` после Human Gate B; проверить синхронизацию дельт и перенос в `changes/archive/<YYYY-MM-DD-<name>>/` |

Перед архивированием прочитать актуальные инструкции и проверить валидацию. Не использовать `--no-validate`, `--skip-specs` или `--yes` ради обхода ошибок/согласования; opt-out спецификаций должен быть обоснован и согласован. Подтверждение CLI само по себе не является Human Gate B.

## Артефакты

| Артефакт | Вопрос | Содержимое |
|---|---|---|
| `proposal.md` | Зачем | Why, What Changes, Capabilities (New/Modified), Impact |
| `specs/<cap>/spec.md` | Что (поведение) | дельта требований (ADDED/MODIFIED/REMOVED/RENAMED) |
| `design.md` | Как | Context, Goals/Non-Goals, Decisions, Risks/Trade-offs, Migration Plan, Open Questions |
| `tasks.md` | Шаги | чек-боксы `- [ ] N.M <действие + как проверить>` |

Зависимости схемы: `proposal → (specs, design) → tasks`. Шаблон OpenSpec рекомендует design при существенных технических решениях; **blueprint требует `design.md` всегда**, допускает краткое обоснование простого подхода. Отсутствие дельт `specs/` допустимо только через обоснованный `skip_specs`, явно предъявленный на Gate A. Это исключение состава артефактов, не сокращение workflow.

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
- Для новых требований рекомендуется описание (до первого сценария) ≤ **500 символов**. В схеме OpenSpec это информационная рекомендация, не безусловная ошибка validation; существующий MODIFIED-блок нельзя урезать ради длины.
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
2. Артефакты готовятся на этапе 4; при возвратах могут обновляться. Изменение согласованных scope/требований/архитектуры/плана требует повторного Human Gate A до дальнейшей реализации. Код до Gate A не меняется.
3. `skip_specs` не выдумывать ради прохождения валидации: нет изменения поведения → нет спеки.
4. Перед архивированием: валидация конкретного изменения, закрытие замечаний/отчёты проверок и явный Human Gate B. Чек-боксы в `tasks.md` не заменяют приёмку.

## Справочные команды

```bash
openspec list --json              # изменения (root: null → корня нет)
openspec list --specs             # инвентарь capability
openspec show <id> --type spec --json --no-scenarios   # обзор существующей спеки
openspec change show <name> --json --deltas-only       # дельты изменения
openspec schemas --json           # доступные схемы
openspec store list --json        # зарегистрированные stores
```
