# PoC примитивов установщика (Track B)

> **Синтетические fixtures.** Все provider/ID, содержимое и пути — вымышленные;
> секретов и реальных производственных настроек нет. Это **provisional**-прототип
> для проверки примитивов D3, а **не** финальный контракт D3/P6a и не production-установщик.

## Объём (утверждён Gate A: задачи 0.2, 3.1–3.10)

- `poc_installer.py` — provisional-примитивы: manifest, `plan` (без записи), `apply`
  (staging/backup/journal/state), `recover`, детект symlink/hardlink и drift.
- `test_poc_installer.py` — офлайн-тесты (`unittest`, только stdlib; пишет только в
  одноразовый temp-каталог).
- `installer/install-manifest.json` — пример provisional-manifest с четырьмя типами
  владения и хешами управляемых частей.

## Manifest (provisional)

```json
{
  "schemaVersion": 1,
  "provisional": true,
  "entries": [
    {"path": "…", "ownership": "whole-file | json-keys | marked-block | frontmatter-fields",
     "desired": "…", "sha256": "…"}
  ]
}
```

- `whole-file` — файл управляется целиком.
- `json-keys` — управляются только перечисленные ключи JSON (остальные сохраняются).
- `marked-block` — управляется блок между `<!-- BEGIN <blockId> -->` / `<!-- END <blockId> -->`.
- `frontmatter-fields` — управляются только перечисленные скалярные поля YAML-frontmatter
  (PoC-упрощение: только `key: value`-скаляры; формальная обработка — P4/P6a).

`sha256` — обязательный хеш канонической формы управляемой части; установщик
**сверяет** его с пересчитанным значением и отклоняет расхождение (M1).

Каноническая форма marked-block нормализуется (окружающие пробелы/переводы строк
игнорируются) — поэтому валидный блок сходится к `noop` (H1).

## Согласование (D3-примитивы)

`plan()`: `create` (отсутствует) / `noop` (current == desired) / `update`
(current == last-applied) / `conflict` (drift — пользователь изменил управляемую часть).
`apply()`: staging → backup → write-ahead journal (с `post_hash`) → запись → фиксация
`state.json` последней; перед записью повторно проверяется безопасность пути (L2).
`recover()`: откат по journal+backup **с обнаружением post-crash-правок** — если
пользователь изменил файл после сбоя, восстановление останавливается с конфликтом,
не затирая правку (H2).

## Запуск

```bash
cd tests/fixtures/installer-agent-role-poc
python3 test_poc_installer.py
```

Ожидание: все тесты зелёные. Ничего вне одноразового temp-каталога не пишется.

## Остаточные ограничения (явно зафиксированы)

- **TOCTOU (L2):** повторная проверка symlink/hardlink непосредственно перед
  записью снижает, но **не устраняет** гонку между проверкой и записью
  (portable-атомарного `openat`-подхода в stdlib нет). На локальном доверенном
  fixture риск минимален; полная защита — за пределами PoC.
- **Рост staging/backup/journal (L3):** автоматическая очистка **не выполняется**
  (backup и journal — это recovery-evidence; очистка — будущая работа P6a).
- **Frontmatter (M3):** парсинг только скалярных `key: value` полей; файл без
  однозначно идентифицируемого frontmatter трактуется консервативно (conflict,
  содержимое не изменяется и не отбрасывается).
- **Manifest остаётся provisional:** это PoC-прототип, не финальный контракт D3/P6a.
