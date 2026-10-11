# Шаблоны OpenSpec-артефактов

Шаблоны схемы `spec-driven`, адаптированы из [Fission-AI/openspec](https://github.com/Fission-AI/openspec) (`schemas/spec-driven/templates/`).

| Файл | Артефакт | Зависимость артефакта (не номер этапа) |
|---|---|---|
| `proposal.md` | Зачем и что меняем | Исходный артефакт |
| `spec.md` | Дельта требований (поведение) | proposal; отсутствие дельт обосновывается через `skip_specs` |
| `design.md` | Как (технические решения) | proposal; в blueprint обязателен, допустим краткий |
| `tasks.md` | Чек-лист реализации | specs и design |

Примечания:
- Это справочные адаптации. `openspec instructions <artifact> --change <name>` отдаёт формат и контекст установленной версии CLI. Технический формат сверяют с CLI; более строгие правила blueprint (design и Human Gate A/B) сохраняются. Несовместимость требует решения пользователя, а не молчаливой отмены согласований.
- Язык артефактов задаётся `openspec init --language <lang>` (и/или `context` в `config.yaml`).
