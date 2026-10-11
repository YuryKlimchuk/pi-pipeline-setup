# Определения subagents (роли)

Здесь будут лежать определения ролей — Markdown-файлы, которые при установке копируются в `.pi/agents/` целевого проекта.

> **Статус:** на текущем этапе файлы subagents **не создаются**. Ниже — формат, конвенции и состав ролей. Полные карточки ролей — [`docs/roles.md`](../docs/roles.md); распределение моделей — [`docs/model-configuration.md`](../docs/model-configuration.md).

## Формат (проверено по исходникам расширения subagent)

```markdown
---
name: <lowercase-name>
description: <что делает и когда использовать>
tools: read, grep, find, ls, bash          # необязательно, через запятую
model: <модель>                            # необязательно, заполняется при установке
---

<тело = системный промпт агента>
```

- Агент загружается, если есть `name` и `description`.
- `tools` — список разрешённых инструментов (если пусто — без ограничений).
- `model` — если не задан, агент наследует модель по умолчанию.

## Разделение понятий

Роль и модель независимы:

| Понятие | Где | Примечание |
|---|---|---|
| Роль + инструкции | тело файла агента | без привязки к провайдеру/модели |
| Модель агента | `model:` frontmatter | заполняется установщиком из конфигурации уровней |
| Инструменты | `tools:` frontmatter | наименьшие привилегии |
| Параметры запуска | вызов `subagent` (single/parallel/chain, `agentScope`) | задаёт оркестратор |
| Этапы | `workflow/orchestrator.md` | когда запускать роль |

## Конвенции

1. **Не хардкодить `model` в теле агента.** Имена моделей специфичны для окружения. Модель назначается через конфигурацию уровней (`docs/model-configuration.md`), а не пишется в инструкции роли.
2. `tools` — минимально необходимые (ревьюеру не нужен `write`; QA и ревьюеру — только чтение + `bash` без мутирующих команд).
3. Тело агента завершается форматом вывода для передачи контекста следующему шагу (`{previous}`).
4. `orchestrator` **не создаётся как subagent** — это основная сессия Pi.

## Состав ролей

| Файл (будущий) | Роль | Этапы workflow | Запуск |
|---|---|---|---|
| `analyst.md` | Business/System Analyst | 2, 4 | single / chain |
| `architect.md` | Software Architect / Tech Lead | 3, 4 | single / chain |
| `developer.md` | Software Developer | 6, 8 | single |
| `code-reviewer.md` | Developer Reviewer | 7, 8 | parallel |
| `qa.md` | QA Engineer | 7, 8 | parallel |
| `devops.md` | DevOps Engineer | по необходимости | single / parallel |

Подготовка OpenSpec распределена: `analyst` → `proposal.md` + `specs/`; `architect` → `design.md` + `tasks.md`. Узкие роли (`spec-writer`, `planner`, `explore`) не вводятся.
