# Контракт модельной конфигурации (P2)

> Статус: реализовано в рамках P2 (изменение `model-configuration-contract`).
> Источники: schema `schemas/model-configuration.schema.json`, fixtures
> `tests/fixtures/models/`, утверждённое решение D1 в [architecture.md](architecture.md),
> канонические профили в [model-configuration.md](model-configuration.md).

Это машино-проверяемый контракт формата, а не runtime-механизм Pi. Pi не читает
этот YAML; потребитель — будущий resolver/генератор (P4) и валидаторы. В P2
рабочие `config/models.yaml` и `.pi/blueprint-models.yaml` **не создаются**.

## Два источника

| Документ | Назначение | Ключевые обязательные поля |
|---|---|---|
| Пресеты blueprint (`config/models.yaml`) | Профили и назначения ролей в уровни, без provider ID | `schemaVersion`, `defaultProfile`, `levels`, `profiles` |
| Проектный источник (`.pi/blueprint-models.yaml`) | Профиль, `provider/model-id` по уровням, overrides | `schemaVersion`, `blueprint`, `profile`, `levels` |

Корневой `oneOf` различает документы по обязательным полям; `additionalProperties: false`
делает смешение полей двух источников ошибкой.

## Три уровня проверки

1. **Schema-валидация (структура).** Типы, `enum` профилей/ролей/уровней,
   `required`, `additionalProperties: false`, `const` версии, `oneOf` для
   `Assignment`, `pattern` для `presetsSha256`. Не доказывает семантическую
   корректность.
2. **Семантическая валидация (назначения).** Согласованность профиля/уровней/
   назначений и правил приоритетов. Документируется ниже; исполняется будущим
   resolver (P4), не JSON Schema.
3. **Runtime-разрешение.** Выбор эффективного provider/ID. Только P4.

Валидный JSON/YAML не означает «семантически корректен» или «исполним».

## Разрешение и приоритеты

`профиль → orchestrator/subagents override → сопоставление уровня → итоговый ModelRef`.

- Назначение из профиля всегда выражено уровнем; оно разрешается через карту
  `levels.<level> → ModelRef` проектного источника.
- Override с `level` заменяет уровень роли, затем уровень разрешается в ModelRef.
- Override с прямым `model` (ModelRef) **минует** сопоставление уровня — итоговым
  становится сам ModelRef.
- Отсутствие override означает «профиль», не пустую модель.
- `orchestrator` относится только к defaults основной сессии; в `subagents`
  ключ `orchestrator` запрещён.
- Постоянный ручной выбор = правка override + повторное применение (без watcher).

## ModelRef и идентификаторы

`ModelRef` = непустые строки `provider` и `id`. `id` хранится целиком, включая
`/` и `:`; запрещено делить ID по `/` и интерпретировать его как shell-строку.
`blueprint.revision` — непустая строка (не плавающая ветка/`latest`);
`blueprint.presetsSha256` — ровно 64 hex-символа.

## Duplicate keys (parse-слой)

JSON Schema **не обнаруживает** дубли ключей (JSON-парсер их теряет). Обязанность
по отклонению дублей лежит на YAML-загрузчике: он должен использовать
unique-keys-aware-разбор **до** schema-валидации. Аналогично запрещены custom
tags, aliases и merge keys. Это правило загрузчика, не schema.

## Ошибки

`schemaVersion` ≠ 1 → ошибка без миграции; неизвестные поля/роли/профили/уровни →
ошибка без игнорирования; `{level, model}` одновременно → ошибка; пустой
provider/id → ошибка. Ошибки детерминированы, молчаливого fallback нет.

## Ручная процедура валидации (без установки зависимостей)

Используются уже доступные `python3` + `jsonschema` + `PyYAML`. Ничего не
устанавливается.

### 1. Синтаксис schema

```bash
python3 -c "import json; json.load(open('schemas/model-configuration.schema.json')); print('schema JSON OK')"
python3 -c "from jsonschema import Draft202012Validator; Draft202012Validator.check_schema(__import__('json').load(open('schemas/model-configuration.schema.json'))); print('schema valid')"
```

### 2. Valid fixtures — ожидается отсутствие ошибок

```bash
python3 - <<'EOF'
import json, glob, sys
from jsonschema import Draft202012Validator
schema = json.load(open('schemas/model-configuration.schema.json'))
v = Draft202012Validator(schema)
rc = 0
for f in sorted(glob.glob('tests/fixtures/models/valid/*.json')):
    doc = json.load(open(f))
    errs = list(v.iter_errors(doc))
    print(f, 'OK' if not errs else 'ERRORS: ' + str([e.message for e in errs]))
    rc |= bool(errs)
sys.exit(rc)
EOF
```

### 3. Invalid JSON fixtures — ожидаются ошибки schema

```bash
python3 - <<'EOF'
import json, glob, sys
from jsonschema import Draft202012Validator
schema = json.load(open('schemas/model-configuration.schema.json'))
v = Draft202012Validator(schema)
rc = 0
for f in sorted(glob.glob('tests/fixtures/models/invalid/*.json')):
    doc = json.load(open(f))
    errs = list(v.iter_errors(doc))
    print(f, 'REJECTED (%d errors)' % len(errs) if errs else 'NOT REJECTED')
    rc |= (not errs)
sys.exit(rc)
EOF
```

### 4. Duplicate keys — строгий YAML-загрузчик должен отклонять

```bash
python3 - <<'EOF'
import yaml, sys
class UniqueKeyLoader(yaml.SafeLoader):
    pass
def reject_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "duplicate key", node.start_mark,
                "found duplicate key %r" % key, key_node.start_mark)
        seen.add(key)
    return {loader.construct_object(k, deep=deep): loader.construct_object(v, deep=deep)
            for k, v in node.value}
UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, reject_duplicates)
try:
    list(yaml.load_all(open('tests/fixtures/models/invalid/duplicate-keys.yaml'),
                       Loader=UniqueKeyLoader))
    print('NOT REJECTED'); sys.exit(1)
except yaml.constructor.ConstructorError as e:
    print('REJECTED:', e.problem); sys.exit(0)
EOF
```

### 5. Согласованность

```bash
git diff --check
```

Ручная сверка: профили в `presets.json` ↔ таблица `docs/model-configuration.md`;
роли в schema ↔ семь канонических ролей `docs/roles.md`.
