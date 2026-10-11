# Workflow оркестратора

Этот каталог описывает, **как** основной агент (оркестратор) ведёт задачу через этапы workflow. Здесь нет проектных деталей и определений ролей — только процесс, решения и gates.

## Содержимое

- `orchestrator.md` — рабочая инструкция оркестратора (этапы, условия перехода, gates, режимы subagent-инструмента).

## Связь с остальными частями

- Этапы workflow — в [`docs/workflow.md`](../docs/workflow.md).
- Роли — в [`docs/roles.md`](../docs/roles.md); их определения — в [`agents/`](../agents/).
- Артефакты OpenSpec (этап 4) — по конвенциям [`openspec/`](../openspec/).
- Распределение моделей по ролям — [`docs/model-configuration.md`](../docs/model-configuration.md).
