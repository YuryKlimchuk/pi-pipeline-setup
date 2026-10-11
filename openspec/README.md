# Интеграция с OpenSpec

Источник правил и настроек: **[Fission-AI/openspec](https://github.com/Fission-AI/openspec)** (npm: `@fission-ai/openspec`). Команды и зависимости ниже сверены с локальным CLI **1.14.0** и его схемой `spec-driven`; на целевой установке нужно повторно проверить версию/профиль.

OpenSpec — инструмент spec-driven development: общий, рецензируемый план до написания кода. Зависимости артефактов: `proposal → (specs, design) → tasks`.

## Содержимое

| Файл | Назначение |
|---|---|
| `conventions.md` | Конвенции ведения артефактов и выверенные команды CLI. |
| `config.example.yaml` | Пример проектного `openspec/config.yaml` (schema, context, rules). |
| `templates/` | Шаблоны артефактов схемы `spec-driven` (proposal / spec / design / tasks). |

## Ключевые факты (проверено)

### CLI

- Пакет `@fission-ai/openspec` версии 1.14.0 требует **Node.js 20.19+**. Установку выбранной версии и глобальные изменения пользователь согласует отдельно; blueprint не запускает `npm install` автоматически.
- Инициализация проекта: `openspec init --tools <ids>` (создаёт `openspec/` и команды для выбранных AI-инструментов).
- **OpenSpec нативно поддерживает Pi**: `openspec init --tools pi` генерирует slash-команды в `.pi/prompts/opsx-<id>.md` (имя файла → `/opsx-<id>`). Список id инструментов: `openspec init --help` (включает `pi`, `oh-my-pi`).

### Команды Pi `/opsx-…` (будут сгенерированы в `.pi/prompts/` целевого проекта)

Например, `/opsx-propose`, `/opsx-apply`, `/opsx-archive`. Точный набор зависит от версии и профиля OpenSpec; проверяется по фактически сгенерированным файлам. Это prompt templates, не отдельные агенты и не механизм принудительного workflow. В данном репозитории такие команды не установлены.

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
    │   ├── design.md             # в blueprint обязателен, допустим краткий
    │   ├── tasks.md
    │   └── specs/<capability-path>/spec.md   # дельта требований
    └── archive/                  # заархивированные изменения
```

### Схема `spec-driven` (по умолчанию)

Артефакты и зависимости: `proposal` → (`specs`, `design`) → `tasks`. `apply.requires: [tasks]`, `apply.tracks: tasks.md` (чек-боксы `- [ ] N.M` отслеживают прогресс).

## Связь с blueprint

- Этапы и оба обязательных Human Gate A/B определены только в [каноническом workflow](../docs/workflow.md). Наличие артефактов и чек-боксов не доказывает пользовательское согласие.
- Команды Pi `/opsx-…` генерируются OpenSpec при явно разрешённой инициализации; blueprint их не дублирует. Их вызов не отменяет gates, в том числе для apply/archive.
- `design.md` в blueprint обязателен даже для простой задачи. При отсутствии изменения поведения допускается обоснованный `skip_specs: true`, предъявленный на Gate A; фиктивные требования не создаются.

### Владение артефактами по ролям

Краткая справка; канонические контракты и совместная сверка артефактов — в [docs/roles.md](../docs/roles.md):

| Артефакт | Роль |
|---|---|
| `proposal.md` | `analyst` |
| `specs/<capability>/spec.md` (дельты) | `analyst` |
| `design.md` | `architect` |
| `tasks.md` | `architect` |

Orchestrator создаёт изменение (`openspec new change`) и валидирует его, но не подменяет авторов требований/дизайна. Он может добавлять техническую запись согласований по правилам workflow.
