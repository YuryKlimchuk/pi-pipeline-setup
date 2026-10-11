# Интеграция с OpenSpec

Источник правил и настроек: **[Fission-AI/openspec](https://github.com/Fission-AI/openspec)** (npm: `@fission-ai/openspec`). Все команды, схема и форматы ниже сверены с этим репозиторием (версия ~1.14.x) и локально установленным CLI **1.14.0**.

OpenSpec — инструмент spec-driven development: общий, рецензируемый план (proposal → specs → design → tasks) до написания кода.

## Содержимое

| Файл | Назначение |
|---|---|
| `conventions.md` | Конвенции ведения артефактов и выверенные команды CLI. |
| `config.example.yaml` | Пример проектного `openspec/config.yaml` (schema, context, rules). |
| `templates/` | Шаблоны артефактов схемы `spec-driven` (proposal / spec / design / tasks). |

## Ключевые факты (проверено)

### CLI

- Пакет `@fission-ai/openspec`, установка: `npm install -g @fission-ai/openspec@latest`. Требует **Node.js 20.19+**.
- Инициализация проекта: `openspec init --tools <ids>` (создаёт `openspec/` и команды для выбранных AI-инструментов).
- **OpenSpec нативно поддерживает Pi**: `openspec init --tools pi` генерирует slash-команды в `.pi/prompts/opsx-<id>.md` (имя файла → `/opsx-<id>`). Список id инструментов: `openspec init --help` (включает `pi`, `oh-my-pi`).

### Команды `/opsx:*` (генерируются в `.pi/prompts/`)

Профиль по умолчанию: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`, `/opsx:update`, `/opsx:sync-specs`. Расширенный профиль добавляет `/opsx:new`, `/opsx:continue`, `/opsx:ff`, `/opsx:verify`, `/opsx:bulk-archive`, `/opsx:onboard`.

В Pi команды пишутся через дефис: `/opsx-propose`, `/opsx-apply`, `/opsx-archive` и т.д.

### Структура `openspec/` в проекте

```
openspec/
├── config.yaml            # schema, context, rules (проектные настройки)
├── specs/                 # базовые спецификации
│   └── <capability-path>/spec.md
└── changes/
    ├── <change-name>/
    │   ├── .openspec.yaml        # метаданные изменения (schema, skip_specs, …)
    │   ├── proposal.md
    │   ├── design.md             # опционально
    │   ├── tasks.md
    │   └── specs/<capability-path>/spec.md   # дельта требований
    └── archive/                  # заархивированные изменения
```

### Схема `spec-driven` (по умолчанию)

Артефакты и зависимости: `proposal` → (`specs`, `design`) → `tasks`. `apply.requires: [tasks]`, `apply.tracks: tasks.md` (чек-боксы `- [ ] N.M` отслеживают прогресс).

## Связь с blueprint

- Этап планирования workflow использует OpenSpec-изменение (`proposal → specs → design → tasks`).
- Ручное согласование (gate) — между готовыми артефактами и реализацией.
- Реализация отслеживается по `tasks.md`; архивирование — `openspec archive`.
- Команды `/opsx:*` поставляются самим OpenSpec через `openspec init --tools pi`; blueprint не дублирует их, а ссылается на них.
