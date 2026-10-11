# Шаблоны OpenSpec-артефактов

Шаблоны схемы `spec-driven`, адаптированы из [Fission-AI/openspec](https://github.com/Fission-AI/openspec) (`schemas/spec-driven/templates/`).

| Файл | Артефакт | Порядок |
|---|---|---|
| `proposal.md` | Зачем и что меняем | 1 |
| `spec.md` | Дельта требований (поведение) | 2 |
| `design.md` | Как (технические решения) | 2 (опционально) |
| `tasks.md` | Чек-лист реализации | 3 |

Примечания:
- Это справочные копии. Реальный `openspec instructions <artifact> --change <name>` отдаёт шаблон и контекст из установленной версии CLI — при расхождении приоритет у CLI.
- Язык артефактов задаётся `openspec init --language <lang>` (и/или `context` в `config.yaml`).
